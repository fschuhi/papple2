"""Collect Lode Runner's tiles and counted transitions online.

A tile starts at the initial PC or at the destination of a control
transfer. Every conditional branch ends a tile, taken or not. JMP, JSR,
RTS, BRK, and RTI also end tiles.

Ordinary instruction advancement stays in the current tile. Gliding
does not check whether another tile starts at an address, so overlapping
tiles remain separate.

After the run, writes:
    tmp/lr_tiles.csv
    tmp/lr_transitions.csv

These reports retain structure and counts, not the ordered execution
history. Trap effects are not interpreted as instruction transitions;
the worked-example attract run has no RWTS reads.

Run from the repo root:

    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN
    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN --instructions 1000000
"""

import argparse
import csv
import time
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

TILES_OUTPUT = Path("tmp/lr_tiles.csv")
TRANSITIONS_OUTPUT = Path("tmp/lr_transitions.csv")

# Source tile, transfer instruction PC, opcode, branch outcome, target tile.
type TransitionKey = tuple[int, int, int, str, int]


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

    def tile_at(self, start_pc: int) -> Tile:
        tile = self.tiles.get(start_pc)
        if tile is None:
            tile = Tile(start_pc)
            self.tiles[start_pc] = tile
        return tile

    def after_instruction(self) -> None:
        pc = self.cpu.last_PC
        opcode = self.cpu.last_opcode

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
                "" if tile.furthest_pc is None else f"${tile.furthest_pc:04X}"
            )
            writer.writerow(
                (
                    f"${tile.start_pc:04X}",
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
                    f"${source:04X}",
                    f"${pc:04X}",
                    f"${opcode:02X}",
                    outcome,
                    f"${target:04X}",
                    count,
                )
            )

    print(
        f"wrote {len(experiment.transitions):,} transition records to {filename}"
    )


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

    emulator, rwts = boot(args.binary, headless=True)
    experiment = Tiles(emulator.cpu)
    emulator.attach(experiment)

    start = time.perf_counter()
    emulator.run(until=after_instructions(args.instructions))
    seconds = time.perf_counter() - start
    emulator.detach(experiment)

    print(f"{emulator.instructions:,} instructions in {seconds:.2f} s")
    print(f"RWTS reads served: {len(rwts.log)}")
    print(
        f"transitions traversed: {sum(experiment.transitions.values()):,}"
    )
    save_tiles(experiment, TILES_OUTPUT)
    save_transitions(experiment, TRANSITIONS_OUTPUT)
    print("each CSV includes one additional header line")


if __name__ == "__main__":
    main()
