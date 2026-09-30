"""Collect Lode Runner's tiles and measure their observed structure.

A tile starts at the initial PC or at the destination of a control
transfer. Every conditional branch ends a tile, taken or not. JMP, JSR,
RTS, BRK, and RTI also end tiles.

Ordinary instruction advancement stays in the current tile. Gliding
does not check whether another tile starts at an address, so overlapping
tiles remain separate.

After the run, check accounting and write:
    tmp/lr_tiles.csv
    tmp/lr_transitions.csv
    tmp/lr_measurements.txt
    tmp/lr_boundary_sites.csv
    tmp/lr_overlap_groups.csv
    tmp/lr_stitch_candidates.csv
    tmp/lr_loop_candidates.csv

The original tile and transition CSV schemas are unchanged.

Measurements do not transform the collected graph. They identify
boundary sites, address-span overlap, conservative stitch candidates,
and loop candidates. No annotated listing is used as input.

Two graph views are measured:
    full
    without_call_return

The second view excludes JSR, RTS, and RTI edges. It is a diagnostic
projection, not a claim that those transfers did not execute.

These reports retain structure and counts, not ordered execution
history. Trap effects are not interpreted as instruction transitions.

Run from the repo root:

    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN
    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN --instructions 1000000
"""

import argparse
import csv
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

# Python puts the folder of the started script on its search path,
# so the sibling boot script can be imported directly.
from boot_lode_runner import boot
from papple2.core.cpu import (
    BCC,
    BCS,
    BEQ,
    BMI,
    BNE,
    BPL,
    BVC,
    BVS,
    JMP_absolute,
    JMP_indirect,
    JSR,
    RTS,
    CPU,
)
from papple2.debug.stop_conditions import after_instructions

BRK = 0x00
RTI = 0x40

BRANCH_OPCODES = frozenset({BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS})
OTHER_LEAP_OPCODES = frozenset({JMP_absolute, JMP_indirect, JSR, RTS, BRK, RTI})
CALL_RETURN_OPCODES = frozenset({JSR, RTS, RTI})

# Conservatively avoid stitching across calls, returns, or interrupts.
STITCH_EXCLUDED_OPCODES = frozenset({JSR, RTS, RTI, BRK})

TILES_OUTPUT = Path("tmp/lr_tiles.csv")
TRANSITIONS_OUTPUT = Path("tmp/lr_transitions.csv")
MEASUREMENTS_OUTPUT = Path("tmp/lr_measurements.txt")
BOUNDARY_SITES_OUTPUT = Path("tmp/lr_boundary_sites.csv")
OVERLAP_GROUPS_OUTPUT = Path("tmp/lr_overlap_groups.csv")
STITCH_CANDIDATES_OUTPUT = Path("tmp/lr_stitch_candidates.csv")
LOOP_CANDIDATES_OUTPUT = Path("tmp/lr_loop_candidates.csv")

# Source tile, transfer instruction PC, opcode, branch outcome, target tile.
type TransitionKey = tuple[int, int, int, str, int]
type TransitionRecord = tuple[TransitionKey, int]

OPCODE_NAMES = {
    BCC: "BCC",
    BCS: "BCS",
    BEQ: "BEQ",
    BMI: "BMI",
    BNE: "BNE",
    BPL: "BPL",
    BVC: "BVC",
    BVS: "BVS",
    JMP_absolute: "JMP_absolute",
    JMP_indirect: "JMP_indirect",
    JSR: "JSR",
    RTS: "RTS",
    BRK: "BRK",
    RTI: "RTI",
}

BOUNDARY_CLASSES = ("branch", "call", "return", "jump", "interrupt", "other")


def address(pc: int) -> str:
    return f"${pc:04X}"


def addresses(pcs) -> str:
    """Format a collection in the supplied order."""
    return " ".join(address(pc) for pc in pcs)


def boundary_class(opcode: int) -> str:
    if opcode in BRANCH_OPCODES:
        return "branch"
    if opcode == JSR:
        return "call"
    if opcode in {RTS, RTI}:
        return "return"
    if opcode in {JMP_absolute, JMP_indirect}:
        return "jump"
    if opcode == BRK:
        return "interrupt"
    return "other"


@dataclass
class Tile:
    start_pc: int
    initial_entries: int = 0
    leaped_to: int = 0
    leaped_from: int = 0
    instructions: int = 0
    furthest_pc: int | None = None
    furthest_instruction_size: int = 0

    def observe_instruction(self, pc: int, size: int) -> None:
        self.instructions += 1

        # Retain the observed extent for reporting, not a fixed tile boundary.
        # Overlap with any other tile is deliberately ignored.
        if self.furthest_pc is None or pc > self.furthest_pc:
            self.furthest_pc = pc
            self.furthest_instruction_size = size
        elif pc == self.furthest_pc:
            self.furthest_instruction_size = max(
                self.furthest_instruction_size, size
            )

    def length_bytes(self) -> int:
        if self.furthest_pc is None:
            return 0
        return (
            self.furthest_pc
            + self.furthest_instruction_size
            - self.start_pc
        )


class Tiles:
    """Collect tiles and transitions through one after_instruction hook."""

    def __init__(self, cpu: CPU) -> None:
        self.cpu = cpu
        self.tiles: dict[int, Tile] = {}
        self.transitions: dict[TransitionKey, int] = {}
        self.current_tile: Tile | None = None
        self.observed_instructions = 0

    def tile_at(self, start_pc: int) -> Tile:
        tile = self.tiles.get(start_pc)
        if tile is None:
            tile = Tile(start_pc)
            self.tiles[start_pc] = tile
        return tile

    def after_instruction(self) -> None:
        pc = self.cpu.last_PC
        opcode = self.cpu.last_opcode
        self.observed_instructions += 1

        if self.current_tile is None:
            self.current_tile = self.tile_at(pc)
            self.current_tile.initial_entries += 1

        source = self.current_tile
        source.observe_instruction(pc, 1 + self.cpu.operand_length)

        if opcode in BRANCH_OPCODES:
            outcome = "taken" if self.cpu.branched else "fall_through"
        elif opcode in OTHER_LEAP_OPCODES:
            outcome = ""
        else:
            return

        target = self.tile_at(self.cpu.PC)
        key = (source.start_pc, pc, opcode, outcome, target.start_pc)
        self.transitions[key] = self.transitions.get(key, 0) + 1

        # A self-transition is an exit and a new entry, even though source
        # and target refer to the same tile.
        source.leaped_from += 1
        target.leaped_to += 1
        self.current_tile = target


def check_consistency(experiment: Tiles, expected_instructions: int) -> None:
    """Check collected accounting before writing any reports.

    These checks validate accounting, not the completeness of the
    control-transfer classification or the interpretation of trap effects.
    """
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(f"tile consistency check failed: {message}")

    require(expected_instructions >= 0, "negative emulator instruction delta")
    require(
        experiment.observed_instructions == expected_instructions,
        "hook instruction count != emulator instruction delta "
        f"({experiment.observed_instructions} != {expected_instructions})",
    )

    incoming: Counter[int] = Counter()
    outgoing: Counter[int] = Counter()

    for key, count in experiment.transitions.items():
        source, pc, opcode, outcome, target = key
        require(
            isinstance(count, int) and count > 0,
            f"invalid transition count: {key!r}",
        )
        require(source in experiment.tiles, f"unknown source {address(source)}")
        require(target in experiment.tiles, f"unknown target {address(target)}")
        require(0 <= pc <= 0xFFFF, f"invalid transfer PC: {key!r}")
        require(
            opcode in BRANCH_OPCODES or opcode in OTHER_LEAP_OPCODES,
            f"unclassified transfer opcode: {key!r}",
        )

        if opcode in BRANCH_OPCODES:
            require(
                outcome in {"taken", "fall_through"},
                f"invalid branch outcome: {key!r}",
            )
        else:
            require(outcome == "", f"outcome on non-branch: {key!r}")

        incoming[target] += count
        outgoing[source] += count

    for start_pc, tile in experiment.tiles.items():
        label = address(start_pc)
        require(0 <= start_pc <= 0xFFFF, f"{label}: invalid start PC")
        require(tile.start_pc == start_pc, f"{label}: tile identity mismatch")

        for field in (
            "initial_entries",
            "leaped_to",
            "leaped_from",
            "instructions",
        ):
            value = getattr(tile, field)
            require(
                isinstance(value, int) and value >= 0,
                f"{label}: invalid {field}",
            )

        require(
            incoming[start_pc] == tile.leaped_to,
            f"{label}: incoming transition counts != leaped_to",
        )
        require(
            outgoing[start_pc] == tile.leaped_from,
            f"{label}: outgoing transition counts != leaped_from",
        )
        require(
            tile.initial_entries + tile.leaped_to - tile.leaped_from
            == int(tile is experiment.current_tile),
            f"{label}: entry/exit balance != open_visit",
        )
        require(
            tile.leaped_from <= tile.instructions,
            f"{label}: more exits than observed instructions",
        )

        if tile.instructions == 0:
            require(
                tile.furthest_pc is None
                and tile.furthest_instruction_size == 0,
                f"{label}: extent recorded without an instruction",
            )
        else:
            require(
                tile.furthest_pc is not None,
                f"{label}: instructions recorded without an extent",
            )
            require(
                1 <= tile.furthest_instruction_size <= 3,
                f"{label}: invalid instruction size",
            )
            require(
                0 <= tile.furthest_pc <= 0xFFFF,
                f"{label}: invalid furthest PC",
            )

    active = int(experiment.observed_instructions > 0)
    require(
        sum(tile.instructions for tile in experiment.tiles.values())
        == experiment.observed_instructions,
        "tile instruction total != hook instruction count",
    )
    require(
        sum(tile.initial_entries for tile in experiment.tiles.values()) == active,
        "unexpected number of initial entries",
    )
    require(
        sum(tile is experiment.current_tile for tile in experiment.tiles.values())
        == active,
        "unexpected number of open visits",
    )
    require(
        bool(experiment.tiles) == bool(active),
        "tile collection does not match run activity",
    )
    require(
        sum(tile.leaped_to for tile in experiment.tiles.values())
        == sum(experiment.transitions.values()),
        "global incoming total != transition traversal total",
    )
    require(
        sum(tile.leaped_from for tile in experiment.tiles.values())
        == sum(experiment.transitions.values()),
        "global outgoing total != transition traversal total",
    )
    print("tile/transition consistency checks passed")


def save_tiles(experiment: Tiles, filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "start_PC",
                "furthest_PC",
                "length_bytes",
                "initial_entries",
                "leaped_to",
                "leaped_from",
                "instructions",
                "open_visit",
            )
        )
        for start_pc in sorted(experiment.tiles):
            tile = experiment.tiles[start_pc]
            furthest_pc = (
                "" if tile.furthest_pc is None else address(tile.furthest_pc)
            )
            writer.writerow(
                (
                    address(tile.start_pc),
                    furthest_pc,
                    tile.length_bytes(),
                    tile.initial_entries,
                    tile.leaped_to,
                    tile.leaped_from,
                    tile.instructions,
                    int(tile is experiment.current_tile),
                )
            )
    print(f"wrote {len(experiment.tiles):,} tile records to {filename}")


def save_transitions(experiment: Tiles, filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "source_tile",
                "leap_from_PC",
                "opcode",
                "outcome",
                "target_tile",
                "count",
            )
        )
        for key, count in sorted(experiment.transitions.items()):
            source, pc, opcode, outcome, target = key
            writer.writerow(
                (
                    address(source),
                    address(pc),
                    f"${opcode:02X}",
                    outcome,
                    address(target),
                    count,
                )
            )
    print(
        f"wrote {len(experiment.transitions):,} transition records to {filename}"
    )


def write_table(filename: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} measurement records to {filename}")


def boundary_measurements(
    records: list[TransitionRecord],
) -> tuple[list[dict], list[str]]:
    # A site is identified by PC and opcode. The same PC may appear with
    # different opcodes if the program modifies instruction bytes.
    sites = defaultdict(list)
    for key, count in records:
        sites[(key[1], key[2])].append((key, count))

    rows = []
    for (pc, opcode), site_records in sorted(sites.items()):
        sources = {key[0] for key, _ in site_records}
        targets = {key[4] for key, _ in site_records}
        outcomes = {key[3] for key, _ in site_records if key[3]}
        rows.append(
            {
                "leap_from_PC": address(pc),
                "opcode": f"${opcode:02X}",
                "mnemonic": OPCODE_NAMES.get(opcode, "unknown"),
                "class": boundary_class(opcode),
                "source_tiles": len(sources),
                "target_tiles": len(targets),
                "transition_records": len(site_records),
                "traversals": sum(count for _, count in site_records),
                "outcomes": " ".join(sorted(outcomes)),
                "taken": sum(
                    count for key, count in site_records if key[3] == "taken"
                ),
                "fall_through": sum(
                    count
                    for key, count in site_records
                    if key[3] == "fall_through"
                ),
                "source_members": addresses(sorted(sources)),
                "target_members": addresses(sorted(targets)),
            }
        )

    lines = [
        "BOUNDARY CAUSES",
        "Sites are (PC, opcode) pairs; transfer PCs are also counted separately.",
        "Destination counts across classes are not additive.",
    ]
    for kind in BOUNDARY_CLASSES:
        selected = [
            (key, count)
            for key, count in records
            if boundary_class(key[2]) == kind
        ]
        lines.append(
            f"  {kind}: "
            f"{len({key[1] for key, _ in selected}):,} transfer PCs; "
            f"{len({(key[1], key[2]) for key, _ in selected}):,} sites; "
            f"{len(selected):,} transition records; "
            f"{sum(count for _, count in selected):,} traversals; "
            f"{len({key[4] for key, _ in selected}):,} destination tiles"
        )

    branch_sites = [
        {key[3] for key, _ in site_records}
        for (_, opcode), site_records in sites.items()
        if opcode in BRANCH_OPCODES
    ]
    lines.extend(
        (
            f"  Branch sites with one observed outcome: "
            f"{sum(len(outcomes) == 1 for outcomes in branch_sites):,}",
            f"  Branch sites with both observed outcomes: "
            f"{sum(len(outcomes) == 2 for outcomes in branch_sites):,}",
        )
    )
    return rows, lines


def overlap_measurements(experiment: Tiles) -> tuple[list[dict], list[str]]:
    """Measure half-open address intervals, not instruction-byte identity."""
    spans = []
    omitted = []
    for pc, tile in sorted(experiment.tiles.items()):
        if tile.instructions == 0:
            continue
        end = tile.furthest_pc + tile.furthest_instruction_size
        if end <= pc or end > 0x10000:
            # The collector's original extent representation is linear;
            # it cannot faithfully describe address-space wrapping.
            omitted.append(pc)
            continue
        spans.append((pc, end))

    # Sorted interval sweep. A strict overlap joins a connected group;
    # merely touching intervals remain separate groups.
    groups = []
    members = []
    group_end = -1
    for start, end in spans:
        if members and start >= group_end:
            groups.append(members)
            members = []
            group_end = -1
        members.append((start, end))
        group_end = max(group_end, end)
    if members:
        groups.append(members)

    rows = []
    overlapping_tiles = set()
    pair_count = 0
    for group in groups:
        if len(group) < 2:
            continue
        starts = [start for start, _ in group]
        overlapping_tiles.update(starts)
        summed = sum(end - start for start, end in group)
        union = max(end for _, end in group) - group[0][0]
        pairs = sum(
            other_start < end
            for index, (_, end) in enumerate(group)
            for other_start, _ in group[index + 1:]
        )
        pair_count += pairs
        rows.append(
            {
                "kind": "span_overlap",
                "group_id": f"overlap_{group[0][0]:04X}",
                "member_count": len(group),
                "members": addresses(starts),
                "range_start": address(group[0][0]),
                "range_end_exclusive": address(max(end for _, end in group)),
                "summed_span_bytes": summed,
                "union_span_bytes": union,
                "duplicate_span_bytes": summed - union,
                "overlapping_pairs": pairs,
                "terminal_PC": "",
                "terminal_size": "",
            }
        )

    # "Shared ending" here means shared furthest instruction PC and size.
    # It does not establish that bytes, paths, or actual exits are identical.
    endings = defaultdict(list)
    for start, end in spans:
        tile = experiment.tiles[start]
        endings[(tile.furthest_pc, tile.furthest_instruction_size)].append(
            (start, end)
        )

    shared_ending_count = 0
    for (pc, size), group in sorted(endings.items()):
        if len(group) < 2:
            continue
        shared_ending_count += 1
        summed = sum(end - start for start, end in group)
        union = max(end for _, end in group) - min(start for start, _ in group)
        rows.append(
            {
                "kind": "shared_ending",
                "group_id": f"ending_{pc:04X}_{size}",
                "member_count": len(group),
                "members": addresses(start for start, _ in group),
                "range_start": address(min(start for start, _ in group)),
                "range_end_exclusive": address(max(end for _, end in group)),
                "summed_span_bytes": summed,
                "union_span_bytes": union,
                "duplicate_span_bytes": summed - union,
                "overlapping_pairs": len(group) * (len(group) - 1) // 2,
                "terminal_PC": address(pc),
                "terminal_size": size,
            }
        )

    summed_span = sum(end - start for start, end in spans)
    union_span = sum(
        max(end for _, end in group) - group[0][0] for group in groups
    )
    lines = [
        "ADDRESS-SPAN OVERLAP",
        "These are span measurements, not proof of identical executed code.",
        f"  Valid nonempty spans: {len(spans):,}",
        f"  Unexecuted destination tiles: "
        f"{sum(tile.instructions == 0 for tile in experiment.tiles.values()):,}",
        f"  Omitted non-linear/wrapping extents: {len(omitted):,}",
        f"  Tiles participating in overlap: {len(overlapping_tiles):,}",
        f"  Connected overlap groups: "
        f"{sum(len(group) > 1 for group in groups):,}",
        f"  Overlapping tile pairs: {pair_count:,}",
        f"  Shared-ending groups: {shared_ending_count:,}",
        f"  Summed tile spans: {summed_span:,} bytes",
        f"  Address union: {union_span:,} bytes",
        f"  Excess span coverage: {summed_span - union_span:,} bytes",
    ]
    if omitted:
        lines.append(f"  Omitted tiles: {addresses(omitted)}")
    return rows, lines


def graph_adjacency(
    nodes: list[int], records: list[TransitionRecord]
) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    outgoing = {node: set() for node in nodes}
    incoming = {node: set() for node in nodes}
    for key, _ in records:
        source, _, _, _, target = key
        outgoing[source].add(target)
        incoming[target].add(source)
    return outgoing, incoming


def strongly_connected_components(
    nodes: list[int],
    outgoing: dict[int, set[int]],
    incoming: dict[int, set[int]],
) -> list[list[int]]:
    """Iterative Kosaraju traversal; no Python recursion-depth dependency."""
    visited = set()
    finish = []

    for root in nodes:
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(sorted(outgoing[root])))]
        while stack:
            node, successors = stack[-1]
            try:
                successor = next(successors)
            except StopIteration:
                finish.append(node)
                stack.pop()
                continue
            if successor not in visited:
                visited.add(successor)
                stack.append((successor, iter(sorted(outgoing[successor]))))

    assigned = set()
    components = []
    for root in reversed(finish):
        if root in assigned:
            continue
        assigned.add(root)
        pending = [root]
        component = []
        while pending:
            node = pending.pop()
            component.append(node)
            for predecessor in sorted(incoming[node], reverse=True):
                if predecessor not in assigned:
                    assigned.add(predecessor)
                    pending.append(predecessor)
        components.append(sorted(component))
    return sorted(components, key=lambda component: component[0])


def stitch_candidates(
    nodes: list[int], records: list[TransitionRecord]
) -> tuple[list[list[int]], int]:
    """Find disjoint maximal chains using transition-record degree.

    Require exactly one outgoing record from A and one incoming record
    into B. Do not cross calls, returns, BRK, or self-edges. Eligible
    cycles are left unstitched.
    """
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for key, count in records:
        outgoing[key[0]].append((key, count))
        incoming[key[4]].append((key, count))

    successor = {}
    predecessor = {}
    for source in nodes:
        if len(outgoing[source]) != 1:
            continue
        key, _ = outgoing[source][0]
        target = key[4]
        if (
            source == target
            or key[2] in STITCH_EXCLUDED_OPCODES
            or len(incoming[target]) != 1
        ):
            continue
        successor[source] = target
        predecessor[target] = source

    chains = []
    covered = set()
    for root in nodes:
        if root not in successor or root in predecessor:
            continue
        chain = [root]
        while chain[-1] in successor:
            chain.append(successor[chain[-1]])
        covered.update(chain)
        chains.append(chain)

    # Any eligible links not reached from a root form closed cycles.
    cycle_nodes = set(successor) | set(predecessor)
    cycle_nodes.difference_update(covered)
    return chains, len(cycle_nodes)


def region_metrics(
    experiment: Tiles,
    members: list[int],
    records: list[TransitionRecord],
) -> dict:
    """Recompute boundary accounting; do not sum member entry counters."""
    member_set = set(members)
    internal = []
    incoming = []
    outgoing = []
    for key, count in records:
        source_inside = key[0] in member_set
        target_inside = key[4] in member_set
        if source_inside and target_inside:
            internal.append((key, count))
        elif target_inside:
            incoming.append((key, count))
        elif source_inside:
            outgoing.append((key, count))

    return {
        "instructions": sum(
            experiment.tiles[node].instructions for node in members
        ),
        "initial_entries": sum(
            experiment.tiles[node].initial_entries for node in members
        ),
        "open_visits": int(
            experiment.current_tile is not None
            and experiment.current_tile.start_pc in member_set
        ),
        "internal_records": len(internal),
        "internal_traversals": sum(count for _, count in internal),
        "external_in_records": len(incoming),
        "external_in_traversals": sum(count for _, count in incoming),
        "external_out_records": len(outgoing),
        "external_out_traversals": sum(count for _, count in outgoing),
        "entry_tiles": addresses(sorted({key[4] for key, _ in incoming})),
        "exit_tiles": addresses(sorted({key[0] for key, _ in outgoing})),
        "outside_sources": addresses(sorted({key[0] for key, _ in incoming})),
        "outside_targets": addresses(sorted({key[4] for key, _ in outgoing})),
        "internal_call_return_records": sum(
            key[2] in CALL_RETURN_OPCODES for key, _ in internal
        ),
    }


def graph_measurements(
    experiment: Tiles,
    view: str,
    records: list[TransitionRecord],
    original_records: list[TransitionRecord],
) -> tuple[list[dict], list[dict], list[str]]:
    nodes = sorted(experiment.tiles)
    outgoing, incoming = graph_adjacency(nodes, records)
    chains, eligible_cycle_nodes = stitch_candidates(nodes, records)

    stitch_rows = []
    for index, members in enumerate(chains, 1):
        # Traffic is measured against the original graph even if candidate
        # detection used the call/return-excluded projection.
        metrics = region_metrics(experiment, members, original_records)
        stitch_rows.append(
            {
                "view": view,
                "candidate_id": f"{view}_stretch_{index:04d}",
                "entry_PC": address(members[0]),
                "last_tile": address(members[-1]),
                "member_count": len(members),
                "members": addresses(members),
                "projected_rows_removed": len(members) - 1,
                **metrics,
            }
        )

    self_loops = [[node] for node in nodes if node in outgoing[node]]
    reciprocal_pairs = [
        [source, target]
        for source in nodes
        for target in sorted(outgoing[source])
        if source < target and source in outgoing[target]
    ]
    components = strongly_connected_components(nodes, outgoing, incoming)
    cyclic_components = [
        members
        for members in components
        if len(members) > 1 or members[0] in outgoing[members[0]]
    ]

    loop_rows = []
    for kind, candidates in (
        ("self_loop", self_loops),
        ("reciprocal_pair", reciprocal_pairs),
        ("cyclic_scc", cyclic_components),
    ):
        for index, members in enumerate(candidates, 1):
            observed = region_metrics(experiment, members, original_records)
            projected = region_metrics(experiment, members, records)
            loop_rows.append(
                {
                    "view": view,
                    "kind": kind,
                    "candidate_id": f"{view}_{kind}_{index:04d}",
                    "member_count": len(members),
                    "members": addresses(members),
                    **observed,
                    "view_internal_records": projected["internal_records"],
                    "view_internal_traversals": projected["internal_traversals"],
                    "view_external_in_records": projected["external_in_records"],
                    "view_external_in_traversals":
                        projected["external_in_traversals"],
                    "view_external_out_records":
                        projected["external_out_records"],
                    "view_external_out_traversals":
                        projected["external_out_traversals"],
                }
            )

    reduction = sum(len(members) - 1 for members in chains)
    covered = sum(len(members) for members in chains)
    lines = [
        f"GRAPH VIEW: {view}",
        f"  Nodes retained: {len(nodes):,}",
        f"  Transition records retained: {len(records):,}",
        f"  Traversals retained: {sum(count for _, count in records):,}",
        f"  Isolated nodes in this view: "
        f"{sum(not outgoing[node] and not incoming[node] for node in nodes):,}",
        f"  Multi-tile stitch candidates: {len(chains):,}",
        f"  Tiles in stitch candidates: {covered:,}",
        f"  Singleton stretches after hypothetical stitching: "
        f"{len(nodes) - covered:,}",
        f"  Projected stretches: {len(nodes) - reduction:,}",
        f"  Projected rows removed: {reduction:,}",
        f"  Eligible cycle nodes left unstitched: {eligible_cycle_nodes:,}",
        f"  Self-loop nodes: {len(self_loops):,}",
        f"  Reciprocal pairs: {len(reciprocal_pairs):,}",
        f"  Strongly connected components: {len(components):,}",
        f"  Cyclic strongly connected components: {len(cyclic_components):,}",
        f"  Largest cyclic component: "
        f"{max((len(members) for members in cyclic_components), default=0):,} tiles",
    ]

    largest = sorted(
        (row for row in loop_rows if row["kind"] == "cyclic_scc"),
        key=lambda row: (-row["member_count"], row["members"]),
    )[:5]
    if largest:
        lines.append("  Largest cyclic components, with original-graph traffic:")
        for row in largest:
            lines.append(
                f"    {row['candidate_id']}: "
                f"{row['member_count']:,} tiles; "
                f"{row['instructions']:,} instructions; "
                f"{row['internal_traversals']:,} internal traversals; "
                f"{row['external_in_traversals']:,} external entries; "
                f"{row['external_out_traversals']:,} external exits"
            )

    return stitch_rows, loop_rows, lines


REGION_FIELDS = (
    "instructions",
    "initial_entries",
    "open_visits",
    "internal_records",
    "internal_traversals",
    "external_in_records",
    "external_in_traversals",
    "external_out_records",
    "external_out_traversals",
    "entry_tiles",
    "exit_tiles",
    "outside_sources",
    "outside_targets",
    "internal_call_return_records",
)


def save_measurements(experiment: Tiles, rwts_reads: int) -> None:
    records = sorted(experiment.transitions.items())
    boundary_rows, boundary_lines = boundary_measurements(records)
    overlap_rows, overlap_lines = overlap_measurements(experiment)

    stitch_rows = []
    loop_rows = []
    graph_lines = []
    for view, selected in (
        ("full", records),
        (
            "without_call_return",
            [
                (key, count)
                for key, count in records
                if key[2] not in CALL_RETURN_OPCODES
            ],
        ),
    ):
        stitches, loops, lines = graph_measurements(
            experiment, view, selected, records
        )
        stitch_rows.extend(stitches)
        loop_rows.extend(loops)
        graph_lines.extend(lines)
        graph_lines.append("")

    write_table(
        BOUNDARY_SITES_OUTPUT,
        (
            "leap_from_PC",
            "opcode",
            "mnemonic",
            "class",
            "source_tiles",
            "target_tiles",
            "transition_records",
            "traversals",
            "outcomes",
            "taken",
            "fall_through",
            "source_members",
            "target_members",
        ),
        boundary_rows,
    )
    write_table(
        OVERLAP_GROUPS_OUTPUT,
        (
            "kind",
            "group_id",
            "member_count",
            "members",
            "range_start",
            "range_end_exclusive",
            "summed_span_bytes",
            "union_span_bytes",
            "duplicate_span_bytes",
            "overlapping_pairs",
            "terminal_PC",
            "terminal_size",
        ),
        overlap_rows,
    )
    write_table(
        STITCH_CANDIDATES_OUTPUT,
        (
            "view",
            "candidate_id",
            "entry_PC",
            "last_tile",
            "member_count",
            "members",
            "projected_rows_removed",
            *REGION_FIELDS,
        ),
        stitch_rows,
    )
    write_table(
        LOOP_CANDIDATES_OUTPUT,
        (
            "view",
            "kind",
            "candidate_id",
            "member_count",
            "members",
            *REGION_FIELDS,
            "view_internal_records",
            "view_internal_traversals",
            "view_external_in_records",
            "view_external_in_traversals",
            "view_external_out_records",
            "view_external_out_traversals",
        ),
        loop_rows,
    )

    lines = [
        "LODE RUNNER TILE MEASUREMENTS",
        "",
        "ACCOUNTING",
        "  Consistency checks: passed",
        f"  Observed instructions: {experiment.observed_instructions:,}",
        f"  Tiles: {len(experiment.tiles):,}",
        f"  Transition records: {len(records):,}",
        f"  Transition traversals: {sum(count for _, count in records):,}",
        f"  RWTS reads served: {rwts_reads:,}",
        "",
        *boundary_lines,
        "",
        *overlap_lines,
        "",
        *graph_lines,
        "INTERPRETATION",
        "  All structure is observed structure from this run.",
        "  One observed branch outcome does not prove the other impossible.",
        "  No tiles or transitions have been stitched, removed, or changed.",
        "  Stitch candidates use transition-record degree, not just target degree.",
        "  Stitch candidates exclude calls, returns, BRK, self-edges, and cycles.",
        "  Multi-tile stitch candidates are disjoint within each view.",
        "  All other tiles would remain singleton stretches.",
        "  Projected stitch counts are separate alternatives, not additive.",
        "  A projected chain may contain an unobserved conditional alternative.",
        "  Loop candidates can overlap; their instruction counts are not additive.",
        "  A reciprocal pair is not necessarily an isolated two-node loop.",
        "  SCCs involving calls and returns need not be meaningful local regions.",
        "  Shared endings use furthest instruction PC and size, not code bytes.",
        "  Span measurements use the collector's linear extent representation.",
        "  Main candidate traffic columns always use the original full graph.",
        "  Loop view_* columns use only edges retained in the indicated view.",
        "  In the filtered view, original initial/open counts need not balance",
        "  against filtered external traffic because some edges were removed.",
        "  Region instructions include all observed executions of member tiles;",
        "  they are not counts of executions specifically following a cycle.",
        "  Entry/exit traffic is recomputed from boundary edges, not summed",
        "  from member tile counters.",
        "  Boundary edges describe connectivity, not matched call/return pairs.",
        "  Trap effects are not separately represented as transitions.",
        "  Accounting checks do not validate opcode semantics or trap handling.",
        "",
    ]

    MEASUREMENTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MEASUREMENTS_OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote measurement summary to {MEASUREMENTS_OUTPUT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to LODE_RUNNER.BIN")
    parser.add_argument(
        "--instructions",
        type=int,
        default=4_000_000,
        help="stop after N instructions (default: 4000000)",
    )
    args = parser.parse_args()
    if args.instructions <= 0:
        parser.error("--instructions must be positive")

    #emulator, rwts = boot(args.binary, headless=True)
    emulator, rwts = boot(args.binary, headless=False)
    experiment = Tiles(emulator.cpu)
    emulator.attach(experiment)

    # Compare hook accounting with the emulator's instruction delta,
    # rather than assuming boot left its cumulative counter at zero.
    instructions_before = emulator.instructions
    start = time.perf_counter()
    try:
        emulator.run(until=after_instructions(args.instructions))
    finally:
        seconds = time.perf_counter() - start
        emulator.detach(experiment)

    instructions_executed = emulator.instructions - instructions_before
    check_consistency(experiment, instructions_executed)

    print(f"{instructions_executed:,} instructions in {seconds:.2f} s")
    print(f"RWTS reads served: {len(rwts.log)}")
    print(
        f"transitions traversed: {sum(experiment.transitions.values()):,}"
    )

    save_tiles(experiment, TILES_OUTPUT)
    save_transitions(experiment, TRANSITIONS_OUTPUT)
    save_measurements(experiment, len(rwts.log))
    print("each CSV includes one additional header line")


if __name__ == "__main__":
    main()
