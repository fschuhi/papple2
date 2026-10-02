"""Tiling: an instrumentation that collects tiles and transitions.

A tile starts at the initial PC or at the destination of a control
transfer. Every conditional branch ends a tile, taken or not. JMP, JSR,
RTS, BRK, and RTI also end tiles.

Ordinary instruction advancement stays in the current tile. Gliding
does not check whether another tile starts at an address, so overlapping
tiles remain separate.

The three jobs of an instrumentation, for `Tiling`:
    set up:   emulator.attach(tiling), which hooks after_instruction
    collect:  after_instruction, once per instruction while the run lasts
    report:   tiling.write_reports(folder, ...), after the run

write_reports() checks accounting first, then writes into the folder:
    lr_unbroken_tiles.csv
    lr_unbroken_transitions.csv
    lr_measurements.txt
    lr_split_tiles.csv
    lr_split_transitions.csv

The transformer pass breaks overlapping tiles into strictly disjoint
split tiles (Basic Blocks) by splitting tiles at any observed
entry point. Executions are perfectly reconstructed by conserving traffic
across split points. Where a tile is cut, the piece before the cut runs
straight on into the piece after it, without a leap; each cut is written
as a transition with the outcome "glide".
"""

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

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

# The reports' file names. The folder they go into is the caller's choice.
TILES_FILE = "lr_unbroken_tiles.csv"
TRANSITIONS_FILE = "lr_unbroken_transitions.csv"
MEASUREMENTS_FILE = "lr_measurements.txt"
SPLIT_TILES_FILE = "lr_split_tiles.csv"
SPLIT_TRANSITIONS_FILE = "lr_split_transitions.csv"


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


class Tiling:
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

    def write_reports(
            self, folder: Path, expected_instructions: int, rwts_reads: int
    ) -> None:
        """Check the accounting, then write the five reports into `folder`.

        `expected_instructions` is the number of instructions the emulator
        ran while this instrumentation was attached; the hook's own count
        must match it. `rwts_reads` only goes into the measurements.
        """
        # The checks come first, so a failed check leaves no reports behind.
        check_consistency(self, expected_instructions)
        save_tiles(self, folder / TILES_FILE)
        save_transitions(self, folder / TRANSITIONS_FILE)
        save_measurements(self, rwts_reads, folder)
        print("each CSV includes one additional header line")


def check_consistency(instrumentation: Tiling, expected_instructions: int) -> None:
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
        instrumentation.observed_instructions == expected_instructions,
        "hook instruction count != emulator instruction delta "
        f"({instrumentation.observed_instructions} != {expected_instructions})",
    )

    incoming: Counter[int] = Counter()
    outgoing: Counter[int] = Counter()
    exit_pcs: dict[int, set[int]] = defaultdict(set)

    for key, count in instrumentation.transitions.items():
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

    for start_pc, tile in instrumentation.tiles.items():
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
            == int(tile is instrumentation.current_tile),
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
        if tile is not instrumentation.current_tile:
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

    active = int(instrumentation.observed_instructions > 0)

    # Every instruction belongs to exactly one tile, the one the PC is in.
    require(
        sum(tile.instructions for tile in instrumentation.tiles.values())
        == instrumentation.observed_instructions,
        "tile instruction total != hook instruction count",
    )

    # The run's two boundaries: it starts in exactly one tile without a leap
    # into it (the initial entry), and stops in exactly one tile before
    # leaving it (the open visit).
    require(
        sum(tile.initial_entries for tile in instrumentation.tiles.values()) == active,
        "unexpected number of initial entries",
    )
    require(
        sum(tile is instrumentation.current_tile for tile in instrumentation.tiles.values())
        == active,
        "unexpected number of open visits",
    )
    require(
        bool(instrumentation.tiles) == bool(active),
        "tile collection does not match run activity",
    )

    # Every leap appears once in the tile totals, as an entry and as an exit.
    require(
        sum(tile.leaped_to for tile in instrumentation.tiles.values())
        == sum(instrumentation.transitions.values()),
        "global incoming total != transition traversal total",
    )
    require(
        sum(tile.leaped_from for tile in instrumentation.tiles.values())
        == sum(instrumentation.transitions.values()),
        "global outgoing total != transition traversal total",
    )
    print("tile/transition consistency checks passed")


def check_split_consistency(
        original_records: list[TransitionRecord],
        split_tile_executions: dict[tuple[int, int], int],
        split_transitions: dict[TransitionKey, int],
        glide_transitions: dict[tuple[int, int], int],
        split_tile_initial_entries: dict[int, int],
) -> None:
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(f"split tile consistency failed: {message}")

    sorted_split_tiles = sorted(split_tile_executions.keys())
    for i in range(len(sorted_split_tiles) - 1):
        _, end = sorted_split_tiles[i]
        next_start, _ = sorted_split_tiles[i + 1]
        require(
            end <= next_start,
            f"overlap detected between split tile ending at ${end:04X} and next starting at ${next_start:04X}"
        )

    original_traversals = sum(count for _, count in original_records)
    split_traversals = sum(split_transitions.values())
    require(
        original_traversals == split_traversals,
        f"transition traffic altered ({original_traversals} != {split_traversals})"
    )

    known_split_tile_starts = {s for s, _ in split_tile_executions.keys()}
    for key in split_transitions:
        require(
            key.source in known_split_tile_starts,
            f"transition source ${key.source:04X} is not a valid split tile start"
        )
        require(
            key.target in known_split_tile_starts,
            f"transition target ${key.target:04X} is not a valid split tile start"
        )

    # Every execution of a split tile is entered once: by a leap, by a glide
    # across a cut, or as the run's very first entry. So the entries of each
    # split tile must add up to its executions.
    incoming: Counter[int] = Counter()
    for key, count in split_transitions.items():
        incoming[key.target] += count
    for (_, target), count in glide_transitions.items():
        incoming[target] += count
    for (start, _), executions in split_tile_executions.items():
        entries = split_tile_initial_entries.get(start, 0) + incoming[start]
        require(
            entries == executions,
            f"split tile ${start:04X}: entries ({entries}) != executions ({executions})"
        )
    print("split tile consistency checks passed")


def report_findings(instrumentation: Tiling) -> None:
    """Report what is unusual but not wrong.

    An RTS normally returns right behind a JSR (its PC + 3). An RTS target
    that is not behind any observed JSR points at an address pushed by the
    code itself, e.g. the PHA-PHA-RTS jump through a table.
    """
    keys = [TransitionKey._make(k) for k in instrumentation.transitions]
    jsr_pcs = {key.pc for key in keys if key.opcode == JSR}
    unusual = sorted(
        (key.pc, key.target, instrumentation.transitions[key])
        for key in keys
        if key.opcode == RTS and (key.target - 3) & 0xFFFF not in jsr_pcs
    )
    print(f"RTS targets not behind an observed JSR: {len(unusual)}")
    for pc, target, count in unusual:
        print(f"    {address(pc)} -> {address(target)} ({count:,}x)")


def save_tiles(instrumentation: Tiling, filename: Path) -> None:
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
        for start_pc in sorted(instrumentation.tiles):
            tile = instrumentation.tiles[start_pc]
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
    print(f"wrote {len(instrumentation.tiles):,} tile records to {filename}")


def save_transitions(instrumentation: Tiling, filename: Path) -> None:
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
        for raw_key, count in sorted(instrumentation.transitions.items()):
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
        f"wrote {len(instrumentation.transitions):,} transition records to {filename}"
    )


def write_table(filename: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} measurement records to {filename}")


def split_tiles(
        instrumentation: Tiling, records: list[TransitionRecord]
) -> tuple[list[dict], list[dict]]:
    """Split overlapping tiles into disjoint basic blocks (split tiles)."""
    split_points = sorted(instrumentation.tiles.keys())

    split_tile_executions = defaultdict(int)
    glide_transitions: dict[tuple[int, int], int] = defaultdict(int)
    split_tile_initial_entries: dict[int, int] = defaultdict(int)

    for tile in instrumentation.tiles.values():
        if tile.instructions == 0:
            continue

        start = tile.start_pc
        end = tile.furthest_pc + tile.furthest_instruction_size

        # Omit non-linear wrapping extents from split tile math
        if end <= start or end > 0x10000:
            continue

        # Find all known entry points that land inside this tile
        points = [p for p in split_points if start < p < end]

        boundaries = [start] + points + [end]
        traffic = tile.initial_entries + tile.leaped_to

        for s, e in zip(boundaries[:-1], boundaries[1:]):
            split_tile_executions[(s, e)] += traffic
            # A piece that ends at a cut, not at the tile's end, runs straight
            # on into the next piece. No leap records this, so record it here.
            if e != end:
                glide_transitions[(s, e)] += traffic

        # The run's first entry lands on the first piece of its tile.
        split_tile_initial_entries[start] += tile.initial_entries

    split_transitions = defaultdict(int)
    for key, count in records:
        # The split tile containing the leap instruction begins at the
        # highest split point at or before the leap PC (but within the source tile).
        valid_points = [p for p in split_points if key.source <= p <= key.pc]
        if not valid_points:
            continue

        split_tile_start = max(valid_points)
        new_key = TransitionKey(split_tile_start, key.pc, key.opcode, key.outcome, key.target)
        split_transitions[new_key] += count

    # Run the consistency checks
    check_split_consistency(
        records,
        split_tile_executions,
        split_transitions,
        glide_transitions,
        split_tile_initial_entries,
    )

    split_tile_rows = []
    for (s, e) in sorted(split_tile_executions.keys()):
        split_tile_rows.append(
            {
                "tile_start_PC": address(s),
                "tile_end_PC": address(e),
                "length_bytes": e - s,
                "executions": split_tile_executions[(s, e)],
            }
        )

    transition_rows = []
    for key, count in sorted(split_transitions.items()):
        transition_rows.append(
            {
                "source_tile": address(key.source),
                "leap_from_PC": address(key.pc),
                "opcode": f"${key.opcode:02X}",
                "outcome": key.outcome,
                "target_tile": address(key.target),
                "count": count,
            }
        )

    for (source, target), count in glide_transitions.items():
        transition_rows.append(
            {
                "source_tile": address(source),
                "leap_from_PC": "",
                "opcode": "",
                "outcome": "glide",
                "target_tile": address(target),
                "count": count,
            }
        )

    # A split tile that ends at a cut has no leap, so its glide row never shares
    # a source with leap rows. Sorting by source keeps the file in address
    # order; the sort is stable, so the leap rows keep their order.
    transition_rows.sort(key=lambda row: row["source_tile"])

    return split_tile_rows, transition_rows


def save_measurements(
        instrumentation: Tiling, rwts_reads: int, folder: Path
) -> None:
    # Convert the unique keys to NamedTuples once:
    records: list[TransitionRecord] = sorted(
        (TransitionKey._make(key), count)
        for key, count in instrumentation.transitions.items()
    )

    split_tile_rows, transition_rows = split_tiles(instrumentation, records)

    write_table(
        folder / SPLIT_TILES_FILE,
        (
            "tile_start_PC",
            "tile_end_PC",
            "length_bytes",
            "executions",
        ),
        split_tile_rows,
    )

    write_table(
        folder / SPLIT_TRANSITIONS_FILE,
        (
            "source_tile",
            "leap_from_PC",
            "opcode",
            "outcome",
            "target_tile",
            "count",
        ),
        transition_rows,
    )

    lines = [
        "LODE RUNNER TILE MEASUREMENTS",
        "",
        "ACCOUNTING",
        "  Consistency checks: passed",
        f"  Observed instructions: {instrumentation.observed_instructions:,}",
        f"  Tiles: {len(instrumentation.tiles):,}",
        f"  Transition records: {len(records):,}",
        f"  Transition traversals: {sum(count for _, count in records):,}",
        f"  RWTS reads served: {rwts_reads:,}",
        "",
        "SPLIT TILES",
        f"  Original tiles: {len(instrumentation.tiles):,}",
        f"  Split tiles (Basic Blocks): {len(split_tile_rows):,}",
        f"  Original transition records: {len(records):,}",
        f"  Split transition records: {len(transition_rows):,}",
        f"  Glide transition records: "
        f"{sum(row['outcome'] == 'glide' for row in transition_rows):,}",
        "",
        "INTERPRETATION",
        "  All structure is observed structure from this run.",
        "  One observed branch outcome does not prove the other impossible.",
        "  Split tiles represent dynamic basic blocks: contiguous executed bytes split by observed entry points.",
        "  Split tile executions are reconstructed perfectly by conserving traffic across split points.",
        "  Accounting checks validate the raw tile hooks, not opcode semantics or trap handling.",
        "",
    ]

    measurements_output = folder / MEASUREMENTS_FILE
    measurements_output.parent.mkdir(parents=True, exist_ok=True)
    measurements_output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote measurement summary to {measurements_output}")
