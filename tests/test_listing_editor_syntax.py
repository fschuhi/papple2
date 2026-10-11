"""Tests for the syntax colors of the listing editor: the mnemonic in its
class's color, the hex bytes dark gray, the name in an operand in the color
of the address it names, everything else plain."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.debug.disassembler import Disassembler
from papple2.workbench import shell
from papple2.workbench.basic_blocks_analysis import (
    BasicBlock,
    BlockGraph,
    Routines,
)
from papple2.workbench.colors import Colors
from papple2.workbench.listing_editor import (
    MNEMONIC_CLASS,
    MNEMONIC_COLORS,
    MNEMONIC_GROUPS,
    STYLE,
    ColumnWidths,
    ListingRow,
    column_widths,
    format_row,
    on_bar,
    operand_name_span,
    row_fragments,
)

JSR = ListingRow(
    0x8352, "| ", "20 3e 7a", ".loop1", "JSR lookup_hgr", "with Y", target=0x7A3E
)
INX = ListingRow(0x8355, "| ", "e8", "", "INX", "")
BYTES = ListingRow(0x1A85, "", "", "", ".byte 00 28 50", "")
GAP = ListingRow(None, "|   ", "", "", "... 6004-6006: 2 bytes never ran ...", "")
EMPTY = ListingRow(None, "| ", "", "", "", "")
ROWS = [JSR, INX, BYTES, GAP, EMPTY]


def test_every_mnemonic_of_the_disassembler_has_a_class() -> None:
    disassembler = Disassembler(CPU(Memory(), 0x6000))
    known = {op[1] for op in disassembler.ops} - {"???"}

    assert known == set(MNEMONIC_CLASS)


def test_each_mnemonic_is_in_one_class_only() -> None:
    names = [name for names in MNEMONIC_GROUPS.values() for name in names.split()]

    assert len(names) == len(set(names)) == 56


def test_every_class_has_a_color_in_the_style() -> None:
    assert set(MNEMONIC_COLORS) == set(MNEMONIC_GROUPS)
    for group in MNEMONIC_GROUPS:
        assert STYLE.get_attrs_for_style_str(f"class:mn-{group}").color


@pytest.mark.parametrize("columns", [80, 40, 20])
@pytest.mark.parametrize("row", ROWS)
def test_the_pieces_add_up_to_the_plain_line(row: ListingRow, columns: int) -> None:
    widths = column_widths(ROWS)

    pieces = row_fragments(row, widths, columns)

    assert "".join(text for _style, text in pieces) == format_row(row, widths, columns)


def test_a_cut_instruction_still_adds_up() -> None:
    widths = ColumnWidths(label=0, instruction=8)

    pieces = row_fragments(JSR, widths, 80)

    assert "".join(text for _style, text in pieces) == format_row(JSR, widths, 80)
    assert ("class:mn-ctrl", "JSR") in pieces


def test_the_mnemonic_and_the_bytes_are_colored() -> None:
    pieces = row_fragments(JSR, column_widths(ROWS), 80)

    assert ("class:mn-ctrl", "JSR") in pieces
    assert ("class:bytes", "20 3e 7a") in pieces


def test_label_operand_and_comment_stay_plain() -> None:
    pieces = row_fragments(JSR, column_widths(ROWS), 80)
    plain = "".join(text for style, text in pieces if style == "")

    assert ".loop1" in plain
    assert "lookup_hgr" in plain
    assert "; with Y" in plain
    assert "| 8352" in plain


def test_a_mnemonic_without_operand_is_colored() -> None:
    pieces = row_fragments(INX, column_widths(ROWS), 80)

    assert pieces[-1] == ("class:mn-inc", "INX")


def test_a_byte_row_has_no_class_color() -> None:
    pieces = row_fragments(BYTES, column_widths(ROWS), 80)

    assert all(not style.startswith("class:mn-") for style, _text in pieces)


@pytest.mark.parametrize("row", [GAP, EMPTY])
def test_a_row_without_an_address_is_one_faint_piece(row: ListingRow) -> None:
    widths = column_widths(ROWS)

    assert row_fragments(row, widths, 80) == [
        ("class:gap", format_row(row, widths, 80))
    ]


def test_the_bar_keeps_its_background_under_every_piece() -> None:
    pieces = row_fragments(JSR, column_widths(ROWS), 80)

    on = on_bar(pieces, 80)

    assert all(style.split()[0] == "class:bar" for style, _text in on)
    assert ("class:bar class:mn-ctrl", "JSR") in on
    assert sum(len(text) for _style, text in on) == 80


# Operand colors. Each row names its target; COLORS stands in for the
# dossier's color ranges.

INDEXED = ListingRow(
    0x8872, "", "bd 9a 1c", "", "LDA tbl_halfscr_col_byte,X", "", target=0x1C9A
)
INDIRECT = ListingRow(
    0x835B, "", "31 0c", "", "AND (zp_hgr1_row_ptr),Y", "", target=0x000C
)
IMMEDIATE = ListingRow(0x8359, "", "49 7f", "", "EOR #$7f", "")
OFFSET = ListingRow(0x8450, "", "8d 5b 84", "", "STA .selfmod1+2", "", target=0x845C)
COLORS = {0x1C9A: "green", 0x000C: "cyan", 0x845C: "blue", 0x7A3E: "red"}
OPERAND_ROWS = [JSR, INX, INDEXED, INDIRECT, IMMEDIATE, OFFSET]


def colored(row: ListingRow, columns: int = 80) -> list[tuple[str, str]]:
    return row_fragments(row, column_widths(OPERAND_ROWS), columns, COLORS.get)


def test_the_operand_name_span_leaves_out_brackets_and_index() -> None:
    assert INDEXED.instruction[slice(*operand_name_span(INDEXED))] == (
        "tbl_halfscr_col_byte"
    )
    assert INDIRECT.instruction[slice(*operand_name_span(INDIRECT))] == (
        "zp_hgr1_row_ptr"
    )
    assert OFFSET.instruction[slice(*operand_name_span(OFFSET))] == ".selfmod1+2"


@pytest.mark.parametrize("row", [INX, IMMEDIATE, BYTES])
def test_an_operand_without_a_target_has_no_span(row: ListingRow) -> None:
    assert operand_name_span(row) is None


def test_an_indexed_operand_shows_its_tables_color() -> None:
    pieces = colored(INDEXED)

    assert ("ansigreen", "tbl_halfscr_col_byte") in pieces
    assert pieces[-1] == ("", ",X")


def test_an_indirect_operand_shows_its_pointers_color() -> None:
    pieces = colored(INDIRECT)

    assert ("ansicyan", "zp_hgr1_row_ptr") in pieces
    assert pieces[-1] == ("", "),Y")
    assert any(text.endswith("(") and style == "" for style, text in pieces)


def test_a_label_with_an_offset_is_colored_whole() -> None:
    assert ("ansiblue", ".selfmod1+2") in colored(OFFSET)


def test_a_jsr_target_is_colored_and_the_comment_stays_plain() -> None:
    pieces = colored(JSR)

    assert ("ansired", "lookup_hgr") in pieces
    assert pieces[-1][0] == ""
    assert pieces[-1][1].endswith("; with Y")


def test_an_immediate_stays_plain() -> None:
    pieces = colored(IMMEDIATE)

    assert not any(style.startswith("ansi") for style, _text in pieces)


def test_a_target_without_a_color_stays_plain() -> None:
    pieces = row_fragments(INDEXED, column_widths(OPERAND_ROWS), 80, {}.get)

    assert not any(style.startswith("ansi") for style, _text in pieces)


@pytest.mark.parametrize("columns", [80, 30])
@pytest.mark.parametrize("instruction_width", [32, 12, 6])
@pytest.mark.parametrize("row", OPERAND_ROWS)
def test_colored_pieces_still_add_up_to_the_plain_line(
    row: ListingRow, instruction_width: int, columns: int
) -> None:
    widths = ColumnWidths(label=6, instruction=instruction_width)

    pieces = row_fragments(row, widths, columns, COLORS.get)

    assert "".join(text for _style, text in pieces) == format_row(row, widths, columns)


def test_a_cut_operand_colors_only_what_lies_before_the_dots() -> None:
    widths = ColumnWidths(label=0, instruction=12)

    pieces = row_fragments(INDEXED, widths, 80, COLORS.get)

    assert ("ansigreen", "tbl_h") in pieces
    assert pieces[-1] == ("", "...")


def test_the_bar_keeps_its_background_under_a_colored_operand() -> None:
    on = on_bar(colored(INDEXED), 80)

    assert ("class:bar ansigreen", "tbl_halfscr_col_byte") in on


def test_the_shell_gives_the_editor_the_dossiers_colors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_session: None,
) -> None:
    graph = BlockGraph(
        entry=0x8872,
        blocks={0x8872: BasicBlock(0x8872, 0x887C, 1)},
        edges={},
        successors={0x8872: []},
        predecessors={0x8872: []},
    )
    monkeypatch.setattr(
        shell.session,
        "routines",
        Routines(
            graphs={0x8872: graph},
            loops_of={0x8872: {}},
            calls_into={0x8872: 1},
        ),
    )
    monkeypatch.setattr(shell.session, "annotations", SimpleNamespace(labels={}))
    store = Colors(tmp_path)
    monkeypatch.setattr(shell.session, "color_store", store)
    # Saved in another session before the editor opens: edit() reloads.
    Colors(tmp_path).color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")
    captured = {}

    def capture(*args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(shell, "edit_rows", capture)

    shell.edit(0x8872)

    lookup = captured["target_color_of"]
    assert lookup(0x1C9A) == "green"
    assert lookup(0x1D25) == "green"
    assert lookup(0x1D26) is None
