"""Count which addresses run as code in Lode Runner, and draw a memory map.

Boots Lode Runner headless (the same boot as scripts/boot_lode_runner.py,
including the RWTS trap), runs 4,000,000 instructions from the start, and
counts for every address how often it was fetched as an opcode, as an
operand, and as an immediate operand. Saves a 256 x 256 map as a PNG, one pixel per address,
scaled up 3 times, and the same map as an HTML page, where hovering over a
coloured cell shows its address and counts:

    row     = high byte of the address (the page)
    column  = low byte of the address

    black   never fetched as opcode or operand
    blue    an instruction started here (opcode fetch)
    orange  read as an operand
    green   read as an immediate operand (the $0B in LDA #$0B)
    red     more than one of these -- worth a closer look

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
HTML_OUTPUT = "tmp/lode_runner_execution_map.html"
HTML_CELL_SIZE = 6

BLACK = (0, 0, 0)
OPCODE_COLOUR = (60, 200, 255)
OPERAND_COLOUR = (255, 160, 40)
IMMEDIATE_COLOUR = (90, 200, 90)
BOTH_COLOUR = (255, 60, 60)

# The CPU reads an immediate operand (the $0B in LDA #$0B) with read_data,
# like real data, so it never reaches after_read_operand. These are the 11
# opcodes with immediate mode (ORA AND EOR ADC LDY LDX LDA CPY CMP CPX SBC).
IMMEDIATE_OPCODES = frozenset({0x09, 0x29, 0x49, 0x69, 0xA0, 0xA2, 0xA9, 0xC0, 0xC9, 0xE0, 0xE9})


class ExecutionCounts:
    """Per address: how often it was fetched as an opcode, as an operand,
    and as an immediate operand.

    The methods are named after Memory's hook lists, so that
    Emulator.attach() puts each one into its list. A read hook gets
    (address, value).

    Immediate operands arrive as data reads. after_read_opcode remembers the
    last opcode and its address; after_read_data counts a data read as an
    immediate operand when that opcode has immediate mode and the read is the
    byte right after it. All other data reads are ignored here.
    """

    def __init__(self) -> None:
        self.opcode: list[int] = [0] * MEMORY_SIZE
        self.operand: list[int] = [0] * MEMORY_SIZE
        self.immediate: list[int] = [0] * MEMORY_SIZE
        self.last_opcode_address = -1
        self.last_opcode = 0

    def after_read_opcode(self, address: int, value: int) -> None:
        self.opcode[address] += 1
        self.last_opcode_address = address
        self.last_opcode = value

    def after_read_operand(self, address: int, value: int) -> None:
        self.operand[address] += 1

    def after_read_data(self, address: int, value: int) -> None:
        if self.last_opcode in IMMEDIATE_OPCODES and address == (self.last_opcode_address + 1) & 0xFFFF:
            self.immediate[address] += 1

    def colour(self, address: int) -> tuple[int, int, int]:
        kinds = [
            colour for colour, counts in (
                (OPCODE_COLOUR, self.opcode),
                (OPERAND_COLOUR, self.operand),
                (IMMEDIATE_COLOUR, self.immediate),
            )
            if counts[address] > 0
        ]
        if len(kinds) > 1:
            return BOTH_COLOUR
        if kinds:
            return kinds[0]
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


def css_colour(colour: tuple[int, int, int]) -> str:
    red, green, blue = colour
    return f"rgb({red}, {green}, {blue})"


def save_html(counts: ExecutionCounts, filename: str, instructions: int) -> None:
    """The same map as the PNG, as a plain HTML table: one row per page, one
    cell per address. Only coloured cells get a tooltip (the title
    attribute); black cells stay empty, which keeps the file small."""
    classes = {OPCODE_COLOUR: "o", OPERAND_COLOUR: "p", IMMEDIATE_COLOUR: "i", BOTH_COLOUR: "b"}
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Lode Runner: execution map</title>",
        "<style>",
        f"body {{ background: {css_colour(BLACK)}; color: #ddd; font-family: sans-serif; margin: 1em; }}",
        "table { border-collapse: collapse; }",
        f"td {{ width: {HTML_CELL_SIZE}px; height: {HTML_CELL_SIZE}px; padding: 0; }}",
        "th { font-family: monospace; font-size: 10px; font-weight: normal; color: #888; padding: 0 4px; text-align: left; }",
        "tbody th { line-height: 0; }",
        f".o {{ background: {css_colour(OPCODE_COLOUR)}; }}",
        f".p {{ background: {css_colour(OPERAND_COLOUR)}; }}",
        f".i {{ background: {css_colour(IMMEDIATE_COLOUR)}; }}",
        f".b {{ background: {css_colour(BOTH_COLOUR)}; }}",
        ".key { display: inline-block; width: 10px; height: 10px; margin: 0 4px 0 12px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Lode Runner: execution map</h1>",
        f"<p>{instructions} instructions from the start. Hover over a coloured cell for its address and counts.</p>",
        "<p>",
        '<span class="key o"></span>opcode (an instruction started here)',
        '<span class="key p"></span>operand',
        '<span class="key i"></span>immediate operand',
        '<span class="key b"></span>more than one of these',
        "</p>",
        "<table>",
        # column labels every 16 addresses: $00, $10, ... $F0
        "<thead><tr><th></th>"
        + "".join(f'<th colspan="16">${column:02X}</th>' for column in range(0, 256, 16))
        + "</tr></thead>",
        "<tbody>",
    ]
    for page in range(256):
        cells = []
        for column in range(256):
            address = page << 8 | column
            colour = counts.colour(address)
            if colour == BLACK:
                cells.append("<td></td>")
            else:
                tooltip = (f"${address:04X}: opcode {counts.opcode[address]}, "
                           f"operand {counts.operand[address]}, "
                           f"immediate {counts.immediate[address]}")
                cells.append(f'<td class="{classes[colour]}" title="{tooltip}"></td>')
        # a label on every 4th row only: 10px text on 6px rows would overlap
        label = f"${page:02X}" if page % 4 == 0 else ""
        lines.append(f"<tr><th>{label}</th>" + "".join(cells) + "</tr>")
    lines += ["</tbody>", "</table>", "</body>", "</html>"]

    # the folder may not exist yet, e.g. on a fresh clone or after `make clean`
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    Path(filename).write_text("\n".join(lines) + "\n")
    print("saved", filename)


def print_summary(counts: ExecutionCounts) -> None:
    opcode_addresses = sum(1 for count in counts.opcode if count)
    operand_addresses = sum(1 for count in counts.operand if count)
    immediate_addresses = sum(1 for count in counts.immediate if count)
    several_addresses = sum(1 for a in range(MEMORY_SIZE) if counts.colour(a) == BOTH_COLOUR)
    print(f"addresses fetched as opcode:    {opcode_addresses}")
    print(f"addresses fetched as operand:   {operand_addresses}")
    print(f"addresses read as immediate:    {immediate_addresses}")
    print(f"addresses with more than one:   {several_addresses}")


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
    save_html(counts, HTML_OUTPUT, emulator.instructions)


if __name__ == "__main__":
    main()
