"""Memory map: the dossier's color ranges over a stretch of memory.

The map has MAP_COLUMNS cells per row. Each cell stands for cell_bytes
bytes, a power of 2, so a row covers MAP_COLUMNS * cell_bytes bytes and
starts at a round address: with the default 0x100 per cell, sixteen rows
show the whole 64 KB; with 0x10, one row is one page; with 1, one cell is
one byte, as in a hexdump.

map_rows() works out the color of each cell, through a lookup it is
given (Colors.color_of_bytes in the shell); print_memory_map() prints the
rows, and print_map_legend() the color ranges below them. Nothing here
keeps state or reads the dossier.
"""

from collections.abc import Callable
from dataclasses import dataclass

from papple2.workbench.colors import MIX_COLOR, ColorRange

# Cells per row of the map.
MAP_COLUMNS = 16

# The largest cell: sixteen of them cover the whole 64 KB.
MAX_CELL_BYTES = 0x1000

# A cell outside the range asked for: the bounds are rounded out to whole
# rows, so the first and last row can hold such cells. Shown empty, not
# as a cell without color.
OUTSIDE = ""

# Terminal background colors for the shades and the mix color.
MAP_BACKGROUNDS = {
    "red": "\x1b[41m",
    "green": "\x1b[42m",
    "yellow": "\x1b[43m",
    "blue": "\x1b[44m",
    "magenta": "\x1b[45m",
    "cyan": "\x1b[46m",
    "white": "\x1b[47m",
    MIX_COLOR: "\x1b[103m",
}

# What a colored cell shows in plain text, for the clipboard: the shade's
# first letter, Y for the mix. A cell without color shows dots.
MAP_LETTERS = {
    "red": "r",
    "green": "g",
    "yellow": "y",
    "blue": "b",
    "magenta": "m",
    "cyan": "c",
    "white": "w",
    MIX_COLOR: "Y",
}

RESET = "\x1b[0m"


@dataclass
class MapRow:
    """One row of the map: the address it starts at, and per cell its
    color, None for a cell without color, or OUTSIDE."""

    address: int
    cells: list[str | None]


def map_rows(
    color_of_bytes: Callable[[int, int], str | None],
    start: int,
    end: int,
    cell_bytes: int,
) -> list[MapRow]:
    """The rows of the map from start up to, not including, end.

    start is rounded down and end up to whole rows. A cell is colored by
    color_of_bytes(cell_start, cell_end), asked only about the bytes of the cell
    that lie in the range; a cell with none of them is OUTSIDE.
    """
    if not 0 <= start < end <= 0x10000:
        raise ValueError("a memory map needs 0000 <= start < end <= 10000")
    if cell_bytes <= 0 or cell_bytes & (cell_bytes - 1):
        raise ValueError(f"cell_bytes must be a power of 2, not {cell_bytes:#x}")
    if cell_bytes > MAX_CELL_BYTES:
        raise ValueError(
            f"cell_bytes can be at most {MAX_CELL_BYTES:#x}, not {cell_bytes:#x}"
        )

    row_bytes = MAP_COLUMNS * cell_bytes
    first_row = start - start % row_bytes
    rows_end = min(-(-end // row_bytes) * row_bytes, 0x10000)
    rows = []
    for address in range(first_row, rows_end, row_bytes):
        cells: list[str | None] = []
        for column in range(MAP_COLUMNS):
            cell = address + column * cell_bytes
            cell_start = max(cell, start)
            cell_end = min(cell + cell_bytes, end)
            cells.append(
                color_of_bytes(cell_start, cell_end)
                if cell_start < cell_end
                else OUTSIDE
            )
        rows.append(MapRow(address, cells))
    return rows


def offset_width(cell_bytes: int) -> int:
    """How many hex digits the column offsets need, at least two."""
    return max(2, len(f"{(MAP_COLUMNS - 1) * cell_bytes:x}"))


def print_memory_map(
    rows: list[MapRow], cell_bytes: int, colored: bool = False
) -> None:
    """Print the rows: a header with the columns' offsets, then each row
    with its address. No gridlines: a cell is as wide as its offset plus
    the space behind it, so cells of one color run into one band.

    colored shows each cell's color as its background. Plain, a colored
    cell shows its letter (MAP_LETTERS), a cell without color dots, and a
    cell OUTSIDE spaces, so the text says the same on the clipboard.
    """
    width = offset_width(cell_bytes)
    offsets = " ".join(
        f"{column * cell_bytes:0{width}x}" for column in range(MAP_COLUMNS)
    )
    print(f"      {offsets}")
    for row in rows:
        cells = []
        for shade in row.cells:
            if shade == OUTSIDE:
                cells.append(" " * (width + 1))
            elif colored and shade is not None:
                cells.append(MAP_BACKGROUNDS[shade] + " " * (width + 1) + RESET)
            elif colored:
                cells.append(" " * (width + 1))
            else:
                letter = "." if shade is None else MAP_LETTERS[shade]
                cells.append(letter * width + " ")
        print(f"{row.address:04x}  {''.join(cells)}".rstrip())


def has_mix(rows: list[MapRow]) -> bool:
    """Whether a cell of the rows has the mix color."""
    return any(shade == MIX_COLOR for row in rows for shade in row.cells)


def print_map_legend(
    entries: list[tuple[str, ColorRange]], mix: bool, colored: bool = False
) -> None:
    """Print one line per color range: a swatch, its bounds, its shade and
    its name, in the order given; then, if mix, a line for the mix color.
    The swatch is a cell of the map, colored or plain as there."""

    def swatch(shade: str) -> str:
        if colored:
            return MAP_BACKGROUNDS[shade] + "   " + RESET
        return MAP_LETTERS[shade] * 3

    for name, definition in entries:
        print(
            f"{swatch(definition.shade)}  "
            f"{definition.start:04x}-{definition.end:04x}  "
            f"{definition.shade:<7}  {name}"
        )
    if mix:
        print(f"{swatch(MIX_COLOR)}  different colors in one cell")
