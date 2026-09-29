"""Count which addresses run as code in Lode Runner, and draw a memory map.

Boots Lode Runner headless (the same boot as scripts/boot_lode_runner.py,
including the RWTS trap), runs 4,000,000 instructions from the start, and
counts for every address how often it was fetched as an opcode and how
often as an operand. Saves a 256 x 256 map as a PNG, one pixel per address,
scaled up 3 times:

    row     = high byte of the address (the page)
    column  = low byte of the address

    black   never fetched as opcode or operand
    blue    an instruction started here (opcode fetch)
    orange  read as an operand
    red     both -- worth a closer look

The map shows "ran or not", not how often: see DIRECTION.md, the lessons
from the Robotron heat map. The full counts stay in ExecutionCounts for
later maps.

Run from the repo root, like the other scripts (papple2.toml's data_dir is
read relative to the current working directory):

    python scripts/count_lode_runner.py data/bin/LODE_RUNNER.BIN
    python scripts/count_lode_runner.py data/bin/LODE_RUNNER.BIN --instructions 1000000
"""

import argparse
import logging
import time
from pathlib import Path

# boot_lode_runner.py sits in this folder. Python puts the folder of the
# script it starts on its search path, so this import works when the script
# is started as shown above.
from boot_lode_runner import boot
from papple2.core.emulator import APPLE_II_CYCLES_PER_SECOND
from papple2.debug.stop_conditions import after_instructions

MEMORY_SIZE = 0x10000
SCALE = 3
OUTPUT = "tmp/lode_runner_execution_map.png"

BLACK = (0, 0, 0)
OPCODE_COLOUR = (60, 200, 255)
OPERAND_COLOUR = (255, 160, 40)
BOTH_COLOUR = (255, 60, 60)


class ExecutionCounts:
    """Per address: how often it was fetched as an opcode, and as an operand.

    The two methods are named after Memory's hook lists, so that
    Emulator.attach() puts each one into its list. A read hook gets
    (address, value); the value is not needed for counting.
    """

    def __init__(self) -> None:
        self.opcode: list[int] = [0] * MEMORY_SIZE
        self.operand: list[int] = [0] * MEMORY_SIZE

    def after_read_opcode(self, address: int, value: int) -> None:
        self.opcode[address] += 1

    def after_read_operand(self, address: int, value: int) -> None:
        self.operand[address] += 1

    def colour(self, address: int) -> tuple[int, int, int]:
        ran_as_opcode = self.opcode[address] > 0
        ran_as_operand = self.operand[address] > 0
        if ran_as_opcode and ran_as_operand:
            return BOTH_COLOUR
        if ran_as_opcode:
            return OPCODE_COLOUR
        if ran_as_operand:
            return OPERAND_COLOUR
        return BLACK


def save_map(counts: ExecutionCounts, filename: str) -> None:
    import pygame

    surface = pygame.Surface((256 * SCALE, 256 * SCALE))
    surface.fill(BLACK)
    for address in range(MEMORY_SIZE):
        colour = counts.colour(address)
        if colour != BLACK:
            row = address >> 8
            column = address & 0xFF
            surface.fill(colour, (column * SCALE, row * SCALE, SCALE, SCALE))
    # the folder may not exist yet, e.g. on a fresh clone or after `make clean`
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, filename)
    print("saved", filename)


def print_summary(counts: ExecutionCounts) -> None:
    opcode_addresses = sum(1 for count in counts.opcode if count)
    operand_addresses = sum(1 for count in counts.operand if count)
    both_addresses = sum(1 for a in range(MEMORY_SIZE) if counts.opcode[a] and counts.operand[a])
    print(f"addresses fetched as opcode:  {opcode_addresses}")
    print(f"addresses fetched as operand: {operand_addresses}")
    print(f"addresses fetched as both:    {both_addresses}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to LODE_RUNNER.BIN")
    parser.add_argument("--instructions", type=int, default=4_000_000,
                        help="stop after N instructions (default: 4000000)")
    args = parser.parse_args()

    # shows the line attach() logs
    logging.basicConfig(level=logging.INFO)

    emulator, rwts = boot(args.binary, headless=True)

    counts = ExecutionCounts()
    emulator.attach(counts)

    start = time.time()
    emulator.run(until=after_instructions(args.instructions))
    seconds = time.time() - start

    print(f"{emulator.instructions} instructions in {seconds:.2f} s")
    # the same comparison the throttle makes: emulated cycles against the
    # Apple II's fixed clock, instead of instructions, which vary in length
    apple_seconds = emulator.cpu.cycles / APPLE_II_CYCLES_PER_SECOND
    print(f"{emulator.cpu.cycles} cycles, {apple_seconds:.2f} s on a real Apple II, "
          f"{apple_seconds / seconds:.2f} times a real Apple II")
    print(f"RWTS reads served: {len(rwts.log)}")
    print_summary(counts)
    save_map(counts, OUTPUT)


if __name__ == "__main__":
    main()
