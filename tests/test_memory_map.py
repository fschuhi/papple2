"""Tests for the memory map: its rows, and how they are printed."""

from pathlib import Path

import pytest
from IPython.lib.pretty import pretty

from papple2.workbench import shell
from papple2.workbench.colors import MIX_COLOR, SHADES, ColorRange, Colors
from papple2.workbench.memory_map import (
    MAP_BACKGROUNDS,
    MAP_COLUMNS,
    MAP_LETTERS,
    OUTSIDE,
    has_mix,
    map_rows,
    offset_width,
    print_map_legend,
    print_memory_map,
)
from papple2.workbench.shell import Text, memory_map, use_dossier

# Lode Runner's two tables, as in its dossier.
RANGES = [(0x1C9A, 0x1D26, "green"), (0x1D26, 0x1DB2, "cyan")]


def tables(start: int, end: int) -> str | None:
    """A stand-in for Colors.color_of_bytes over RANGES."""
    shades = {
        shade for first, behind, shade in RANGES if first < end and start < behind
    }
    if not shades:
        return None
    return shades.pop() if len(shades) == 1 else MIX_COLOR


def test_the_default_shows_the_whole_memory_in_sixteen_rows() -> None:
    rows = map_rows(tables, 0x0000, 0x10000, 0x100)

    assert [row.address for row in rows] == list(range(0x0000, 0x10000, 0x1000))
    assert all(len(row.cells) == MAP_COLUMNS for row in rows)
    # Row 1000: page 1c green, page 1d both tables.
    assert rows[1].cells[0xC] == "green"
    assert rows[1].cells[0xD] == MIX_COLOR
    assert rows[1].cells[0xE] is None


def test_a_cell_of_sixteen_bytes_makes_a_row_one_page() -> None:
    rows = map_rows(tables, 0x1C00, 0x1E00, 0x10)

    assert [row.address for row in rows] == [0x1C00, 0x1D00]
    assert rows[0].cells == [None] * 9 + ["green"] * 7
    assert rows[1].cells == (["green"] * 2 + [MIX_COLOR] + ["cyan"] * 9 + [None] * 4)


def test_the_bounds_are_rounded_out_to_whole_rows() -> None:
    rows = map_rows(tables, 0x1C9A, 0x1CA0, 0x10)

    assert [row.address for row in rows] == [0x1C00]
    assert rows[0].cells == [OUTSIDE] * 9 + ["green"] + [OUTSIDE] * 6


def test_the_lookup_is_asked_only_about_bytes_in_the_range() -> None:
    asked: list[tuple[int, int]] = []

    def lookup(start: int, end: int) -> str | None:
        asked.append((start, end))
        return None

    map_rows(lookup, 0x1C9A, 0x1CB4, 0x10)

    assert asked == [(0x1C9A, 0x1CA0), (0x1CA0, 0x1CB0), (0x1CB0, 0x1CB4)]


def test_a_map_can_reach_the_last_byte_of_memory() -> None:
    rows = map_rows(lambda start, end: None, 0xFF00, 0x10000, 0x10)

    assert [row.address for row in rows] == [0xFF00]


@pytest.mark.parametrize("cell_bytes", [0, 3, 0x18, -0x10])
def test_cell_bytes_must_be_a_power_of_2(cell_bytes: int) -> None:
    with pytest.raises(ValueError, match="power of 2"):
        map_rows(tables, 0x0000, 0x10000, cell_bytes)


def test_cell_bytes_cannot_make_a_row_longer_than_memory() -> None:
    with pytest.raises(ValueError, match="at most"):
        map_rows(tables, 0x0000, 0x10000, 0x2000)


@pytest.mark.parametrize(
    "start, end", [(-1, 0x0010), (0x0010, 0x0010), (0x0014, 0x0010), (0x0000, 0x10001)]
)
def test_invalid_bounds_are_refused(start: int, end: int) -> None:
    with pytest.raises(ValueError, match="start < end"):
        map_rows(tables, start, end, 0x10)


@pytest.mark.parametrize(
    "cell_bytes, width", [(1, 2), (0x10, 2), (0x100, 3), (0x1000, 4)]
)
def test_the_offsets_are_as_wide_as_the_largest_one(
    cell_bytes: int, width: int
) -> None:
    assert offset_width(cell_bytes) == width


def test_the_plain_map_shows_letters_and_dots(capsys) -> None:
    print_memory_map(map_rows(tables, 0x1C00, 0x1E00, 0x10), 0x10)

    assert capsys.readouterr().out.splitlines() == [
        "      00 10 20 30 40 50 60 70 80 90 a0 b0 c0 d0 e0 f0",
        "1c00  .. .. .. .. .. .. .. .. .. gg gg gg gg gg gg gg",
        "1d00  gg gg YY cc cc cc cc cc cc cc cc cc .. .. .. ..",
    ]


def test_cells_outside_the_range_are_empty(capsys) -> None:
    print_memory_map(map_rows(tables, 0x1C9A, 0x1CA0, 0x10), 0x10)

    assert capsys.readouterr().out.splitlines()[1] == ("1c00" + " " * 29 + "gg")


def test_the_colored_map_shows_backgrounds_without_letters(capsys) -> None:
    print_memory_map(map_rows(tables, 0x1D00, 0x1D30, 0x10), 0x10, colored=True)

    row = capsys.readouterr().out.splitlines()[1]
    green = MAP_BACKGROUNDS["green"] + "   " + "\x1b[0m"
    mix = MAP_BACKGROUNDS[MIX_COLOR] + "   " + "\x1b[0m"
    assert row == "1d00  " + green + green + mix
    assert "g" not in row.replace("\x1b", "")


def test_every_shade_and_the_mix_color_has_a_background_and_a_letter() -> None:
    assert set(MAP_BACKGROUNDS) == set(MAP_LETTERS) == SHADES | {MIX_COLOR}
    assert len(set(MAP_LETTERS.values())) == len(MAP_LETTERS)


# The legend below the map.


def test_the_legend_lists_each_range_with_a_swatch(capsys) -> None:
    print_map_legend(
        [
            ("halfscr_col_byte", ColorRange(0x1C9A, 0x1D26, "green")),
            ("halfscr_col_shift", ColorRange(0x1D26, 0x1DB2, "cyan")),
        ],
        mix=True,
    )

    assert capsys.readouterr().out.splitlines() == [
        "ggg  1c9a-1d26  green    halfscr_col_byte",
        "ccc  1d26-1db2  cyan     halfscr_col_shift",
        "YYY  different colors in one cell",
    ]


def test_the_colored_legend_shows_the_swatch_as_a_background(capsys) -> None:
    print_map_legend(
        [("sprites", ColorRange(0x8336, 0x83A7, "blue"))], mix=False, colored=True
    )

    assert capsys.readouterr().out == (
        MAP_BACKGROUNDS["blue"] + "   \x1b[0m  8336-83a7  blue     sprites\n"
    )


def test_has_mix_finds_a_mixed_cell() -> None:
    assert has_mix(map_rows(tables, 0x1D00, 0x1E00, 0x10))
    assert not has_mix(map_rows(tables, 0x1C00, 0x1D00, 0x10))


# The command, on a dossier in a temporary folder.


@pytest.fixture
def dossier(tmp_path: Path, fresh_session: None) -> Path:
    use_dossier(tmp_path)
    colors = Colors(tmp_path)
    colors.color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")
    colors.color("halfscr_col_shift", 0x1D26, 0x1DB2, "cyan")
    colors.color("sprites", 0x8336, 0x83A7, "blue")
    return tmp_path


def test_memory_map_shows_the_map_and_the_legend_of_the_range(
    dossier: Path,
) -> None:
    shown = memory_map(0x1C00, 0x1E00, 0x10)

    assert isinstance(shown, Text)
    assert shown.splitlines() == [
        "      00 10 20 30 40 50 60 70 80 90 a0 b0 c0 d0 e0 f0",
        "1c00  .. .. .. .. .. .. .. .. .. gg gg gg gg gg gg gg",
        "1d00  gg gg YY cc cc cc cc cc cc cc cc cc .. .. .. ..",
        "",
        "ggg  1c9a-1d26  green    halfscr_col_byte",
        "ccc  1d26-1db2  cyan     halfscr_col_shift",
        "YYY  different colors in one cell",
    ]


def test_memory_map_shows_the_whole_memory_by_default(dossier: Path) -> None:
    lines = memory_map().splitlines()

    assert len(lines) == 1 + 16 + 1 + 4
    assert lines[2] == "1000  " + "... " * 12 + "ggg YYY ... ..."
    assert lines[9] == "8000  ... ... ... bbb" + " ..." * 12


def test_memory_map_shows_colors_in_ipython(dossier: Path) -> None:
    shown = memory_map(0x1C00, 0x1E00, 0x10)

    assert "\x1b" not in str(shown)
    assert MAP_BACKGROUNDS["green"] in pretty(shown)
    assert MAP_BACKGROUNDS[MIX_COLOR] in pretty(shown)


def test_memory_map_without_ranges_in_it_has_no_legend(dossier: Path) -> None:
    assert memory_map(0x0000, 0x0100, 0x10).splitlines() == [
        "      00 10 20 30 40 50 60 70 80 90 a0 b0 c0 d0 e0 f0",
        "0000  " + " ".join([".."] * 16),
    ]


def test_memory_map_takes_labels_as_bounds(dossier: Path) -> None:
    shell.label(0x1C00, "tables_page")

    assert memory_map("tables_page", 0x1E00, 0x10) == memory_map(0x1C00, 0x1E00, 0x10)


def test_memory_map_reads_ranges_saved_in_another_session(dossier: Path) -> None:
    Colors(dossier).color("scores", 0x0010, 0x0014, "red")

    assert "rrr  0010-0014  red      scores" in memory_map(0x0000, 0x0100, 0x10)


def test_memory_map_stops_without_a_dossier(fresh_session: None) -> None:
    with pytest.raises(RuntimeError, match="use_dossier"):
        memory_map()


def test_the_clipboard_gets_the_plain_map(
    dossier: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copied: list[str] = []

    def pbcopy(command: list[str], input: str, text: bool, check: bool) -> None:
        copied.append(input)

    monkeypatch.setattr(shell.subprocess, "run", pbcopy)
    shown = memory_map(0x1C00, 0x1E00, 0x10)

    shell.clip(shown)

    assert copied == [str(shown)]
