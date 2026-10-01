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
    tmp/lr_split_tiles.csv
    tmp/lr_split_transitions.csv

The transformer pass breaks overlapping tiles into strictly disjoint
execution stretches (Basic Blocks) by splitting tiles at any observed
entry point. Executions are perfectly reconstructed by conserving traffic
across split points.

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
from typing import NamedTuple

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
from papple2.debug.stop_conditions import instruction_count_reaches

BRK = 0x00
RTI = 0x40

BRANCH_OPCODES = frozenset({BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS})
OTHER_LEAP_OPCODES = frozenset({JMP_absolute, JMP_indirect, JSR, RTS, BRK, RTI})
CALL_RETURN_OPCODES = frozenset({JSR, RTS, RTI})

# Precomputed fast opcode lookup for the hot loop:
# 0 = straight-line, 1 = conditional branch, 2 = other leap (jump, call, return, trap)
OPCODE_KIND = bytearray(256)
for _op in BRANCH_OPCODES:
    OPCODE_KIND[_op] = 1
for _op in OTHER_LEAP_OPCODES:
    OPCODE_KIND[_op] = 2

TILES_OUTPUT = Path("tmp/lr_tiles.csv")
TRANSITIONS_OUTPUT = Path("tmp/lr_transitions.csv")
MEASUREMENTS_OUTPUT = Path("tmp/lr_measurements.txt")
SPLIT_TILES_OUTPUT = Path("tmp/lr_split_tiles.csv")
SPLIT_TRANSITIONS_OUTPUT = Path("tmp/lr_split_transitions.csv")


class TransitionKey(NamedTuple):
    source: int
    pc: int
    opcode: int
    outcome: str
    target: int


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


def address(pc: int) -> str:
    return f"{pc:04x}"


def addresses(pcs) -> str:
    """Format a collection in the supplied order."""
    return " ".join(address(pc) for pc in pcs)


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
        self.transitions: dict[tuple, int] = {}
        self.current_tile: Tile | None = None
        self.observed_instructions = 0
        # Internal runner points to the first-instruction handler initially:
        self._step = self._first_instruction

    def tile_at(self, start_pc: int) -> Tile:
        tile = self.tiles.get(start_pc)
        if tile is None:
            tile = Tile(start_pc)
            self.tiles[start_pc] = tile
        return tile

    def after_instruction(self) -> None:
        self._step()

    def _first_instruction(self) -> None:
        pc = self.cpu.last_PC
        tile = self.tile_at(pc)
        tile.initial_entries += 1
        self.current_tile = tile

        # Swap internal step handler to hot loop
        self._step = self._after_instruction_hot
        self._after_instruction_hot()

    def _after_instruction_hot(self) -> None:
        cpu = self.cpu
        pc = cpu.last_PC
        opcode = cpu.last_opcode
        self.observed_instructions += 1

        source = self.current_tile

        # Inlined source.observe_instruction(pc, 1 + cpu.operand_length)
        source.instructions += 1
        furthest = source.furthest_pc
        if furthest is None or pc > furthest:
            source.furthest_pc = pc
            source.furthest_instruction_size = 1 + cpu.operand_length
        elif pc == furthest:
            size = 1 + cpu.operand_length
            if size > source.furthest_instruction_size:
                source.furthest_instruction_size = size

        # Fast opcode dispatch via precomputed table
        kind = OPCODE_KIND[opcode]
        if not kind:
            return

        if kind == 1:
            outcome = "taken" if cpu.branched else "fall_through"
        else:
            outcome = ""

        # Inlined tile lookup/creation
        target_pc = cpu.PC
        tiles = self.tiles
        target = tiles.get(target_pc)
        if target is None:
            target = Tile(target_pc)
            tiles[target_pc] = target

        key = (source.start_pc, pc, opcode, outcome, target.start_pc)
        transitions = self.transitions
        transitions[key] = transitions.get(key, 0) + 1

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

    # The hook runs after every instruction, so its count must equal the
    # emulator's.
    require(
        experiment.observed_instructions == expected_instructions,
        "hook instruction count != emulator instruction delta "
        f"({experiment.observed_instructions} != {expected_instructions})",
    )

    incoming: Counter[int] = Counter()
    outgoing: Counter[int] = Counter()
    exit_pcs: dict[int, set[int]] = defaultdict(set)

    for key, count in experiment.transitions.items():
        source, pc, opcode, outcome, target = key
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

        # A branch that is not taken continues right behind its operand.
        if outcome == "fall_through":
            require(
                target == (pc + 2) & 0xFFFF,
                f"fall-through target is not branch PC + 2: {key!r}",
            )

        incoming[target] += count
        outgoing[source] += count
        exit_pcs[source].add(pc)

    for start_pc, tile in experiment.tiles.items():
        label = address(start_pc)

        # Every leap is recorded twice: in the transition table, and on its
        # two tiles, as an exit from the source and an entry into the target.
        require(
            incoming[start_pc] == tile.leaped_to,
            f"{label}: incoming transition counts != leaped_to",
        )
        require(
            outgoing[start_pc] == tile.leaped_from,
            f"{label}: outgoing transition counts != leaped_from",
        )

        # Every visit is entered once and left once. The only entry without a
        # leap is the run's very first; the only visit without an exit is the
        # one the run stops in. So entries minus exits is 1 for the open tile
        # and 0 for every other tile.
        require(
            tile.initial_entries + tile.leaped_to - tile.leaped_from
            == int(tile is experiment.current_tile),
            f"{label}: entry/exit balance != open_visit",
        )

        # Every exit is an instruction of the tile: the leap itself.
        require(
            tile.leaped_from <= tile.instructions,
            f"{label}: more exits than observed instructions",
        )

        # The PC glides from the tile's start to the first leap, so every
        # visit leaves through the same instruction, the furthest one. A tile
        # without exits can only be the open tile, stopped in its first visit.
        if exit_pcs[start_pc]:
            require(
                exit_pcs[start_pc] == {tile.furthest_pc},
                f"{label}: exits {addresses(sorted(exit_pcs[start_pc]))} "
                "!= furthest PC",
            )

        # For the same reason every completed visit runs the same number of
        # instructions. The open tile's last visit is unfinished.
        if tile is not experiment.current_tile:
            require(
                tile.leaped_from > 0
                and tile.instructions % tile.leaped_from == 0,
                f"{label}: instructions not a whole number per visit",
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

    # Every instruction belongs to exactly one tile, the one the PC is in.
    require(
        sum(tile.instructions for tile in experiment.tiles.values())
        == experiment.observed_instructions,
        "tile instruction total != hook instruction count",
    )

    # The run's two boundaries: it starts in exactly one tile without a leap
    # into it (the initial entry), and stops in exactly one tile before
    # leaving it (the open visit).
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

    # Every leap appears once in the tile totals, as an entry and as an exit.
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


def check_stretch_consistency(
        original_records: list[TransitionRecord],
        stretches_traffic: dict[tuple[int, int], int],
        split_transitions: dict[TransitionKey, int],
) -> None:
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(f"stretch consistency failed: {message}")

    sorted_stretches = sorted(stretches_traffic.keys())
    for i in range(len(sorted_stretches) - 1):
        _, end = sorted_stretches[i]
        next_start, _ = sorted_stretches[i + 1]
        require(
            end <= next_start,
            f"overlap detected between stretch ending at ${end:04X} and next starting at ${next_start:04X}"
        )

    original_traversals = sum(count for _, count in original_records)
    split_traversals = sum(split_transitions.values())
    require(
        original_traversals == split_traversals,
        f"transition traffic altered ({original_traversals} != {split_traversals})"
    )

    known_stretch_starts = {s for s, _ in stretches_traffic.keys()}
    for key in split_transitions:
        require(
            key.source in known_stretch_starts,
            f"transition source ${key.source:04X} is not a valid stretch start"
        )
        require(
            key.target in known_stretch_starts,
            f"transition target ${key.target:04X} is not a valid stretch start"
        )
    print("stretch consistency checks passed")


def report_findings(experiment: Tiles) -> None:
    """Report what is unusual but not wrong.

    An RTS normally returns right behind a JSR (its PC + 3). An RTS target
    that is not behind any observed JSR points at an address pushed by the
    code itself, e.g. the PHA-PHA-RTS jump through a table.
    """
    keys = [TransitionKey._make(k) for k in experiment.transitions]
    jsr_pcs = {key.pc for key in keys if key.opcode == JSR}
    unusual = sorted(
        (key.pc, key.target, experiment.transitions[key])
        for key in keys
        if key.opcode == RTS and (key.target - 3) & 0xFFFF not in jsr_pcs
    )
    print(f"RTS targets not behind an observed JSR: {len(unusual)}")
    for pc, target, count in unusual:
        print(f"    {address(pc)} -> {address(target)} ({count:,}x)")


def save_tiles(experiment: Tiles, filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "start_PC",
                "furthest_PC",
                "length_bytes",
                "leaped_to",
                "leaped_from",
                "instructions",
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
                    tile.leaped_to,
                    tile.leaped_from,
                    tile.instructions,
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
        for raw_key, count in sorted(experiment.transitions.items()):
            key = TransitionKey._make(raw_key)
            writer.writerow(
                (
                    address(key.source),
                    address(key.pc),
                    f"${key.opcode:02X}",
                    key.outcome,
                    address(key.target),
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


def transform_to_stretches(
        experiment: Tiles, records: list[TransitionRecord]
) -> tuple[list[dict], list[dict]]:
    """Split overlapping tiles into disjoint basic blocks (stretches)."""
    split_points = sorted(experiment.tiles.keys())

    stretches_traffic = defaultdict(int)

    for tile in experiment.tiles.values():
        if tile.instructions == 0:
            continue

        start = tile.start_pc
        end = tile.furthest_pc + tile.furthest_instruction_size

        # Omit non-linear wrapping extents from stretch math
        if end <= start or end > 0x10000:
            continue

        # Find all known entry points that land inside this tile
        points = [p for p in split_points if start < p < end]

        boundaries = [start] + points + [end]
        traffic = tile.initial_entries + tile.leaped_to

        for s, e in zip(boundaries[:-1], boundaries[1:]):
            stretches_traffic[(s, e)] += traffic

    split_transitions = defaultdict(int)
    for key, count in records:
        # The stretch containing the leap instruction begins at the
        # highest split point at or before the leap PC (but within the source tile).
        valid_points = [p for p in split_points if key.source <= p <= key.pc]
        if not valid_points:
            continue

        stretch_start = max(valid_points)
        new_key = TransitionKey(stretch_start, key.pc, key.opcode, key.outcome, key.target)
        split_transitions[new_key] += count

    # Run the consistency checks
    check_stretch_consistency(records, stretches_traffic, split_transitions)

    stretch_rows = []
    for (s, e) in sorted(stretches_traffic.keys()):
        stretch_rows.append(
            {
                "stretch_start_PC": address(s),
                "stretch_end_PC": address(e),
                "length_bytes": e - s,
                "executions": stretches_traffic[(s, e)],
            }
        )

    transition_rows = []
    for key, count in sorted(split_transitions.items()):
        transition_rows.append(
            {
                "source_stretch_start": address(key.source),
                "leap_from_PC": address(key.pc),
                "opcode": f"${key.opcode:02X}",
                "outcome": key.outcome,
                "target_stretch_start": address(key.target),
                "count": count,
            }
        )

    return stretch_rows, transition_rows


def save_measurements(experiment: Tiles, rwts_reads: int) -> None:
    # Convert the unique keys to NamedTuples once:
    records: list[TransitionRecord] = sorted(
        (TransitionKey._make(key), count)
        for key, count in experiment.transitions.items()
    )

    stretch_rows, transition_rows = transform_to_stretches(experiment, records)

    write_table(
        SPLIT_TILES_OUTPUT,
        (
            "stretch_start_PC",
            "stretch_end_PC",
            "length_bytes",
            "executions",
        ),
        stretch_rows,
    )

    write_table(
        SPLIT_TRANSITIONS_OUTPUT,
        (
            "source_stretch_start",
            "leap_from_PC",
            "opcode",
            "outcome",
            "target_stretch_start",
            "count",
        ),
        transition_rows,
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
        "STRETCH TRANSFORM",
        f"  Original tiles: {len(experiment.tiles):,}",
        f"  Split stretches (Basic Blocks): {len(stretch_rows):,}",
        f"  Original transition records: {len(records):,}",
        f"  Split transition records: {len(transition_rows):,}",
        "",
        "INTERPRETATION",
        "  All structure is observed structure from this run.",
        "  One observed branch outcome does not prove the other impossible.",
        "  Stretches represent dynamic basic blocks: contiguous executed bytes split by observed entry points.",
        "  Stretch executions are reconstructed perfectly by conserving traffic across split points.",
        "  Accounting checks validate the raw tile hooks, not opcode semantics or trap handling.",
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

    emulator, rwts = boot(args.binary, headless=True)
    experiment = Tiles(emulator.cpu)
    emulator.attach(experiment)

    # Compare hook accounting with the emulator's instruction delta,
    # rather than assuming boot left its cumulative counter at zero.
    instructions_before = emulator.instructions
    start = time.perf_counter()
    try:
        emulator.run(until=instruction_count_reaches(args.instructions))
    finally:
        seconds = time.perf_counter() - start
        emulator.detach(experiment)

    instructions_executed = emulator.instructions - instructions_before
    check_consistency(experiment, instructions_executed)
    first_tile = next(
        tile for tile in experiment.tiles.values() if tile.initial_entries
    )
    print(
        f"run started in tile {address(first_tile.start_pc)}, "
        f"stopped in tile {address(experiment.current_tile.start_pc)}"
    )
    report_findings(experiment)

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
