"""Tests for the syntax colors of the listing editor: the mnemonic in its
class's color, the hex bytes dark gray, everything else plain."""

import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.debug.disassembler import Disassembler
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
