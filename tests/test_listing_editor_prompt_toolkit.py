"""Tests for the layout of the listing viewer in
papple2.workbench.listing_editor_prompt_toolkit. The view itself needs a
terminal; its lines are plain text."""

from papple2.workbench.listing_editor_prompt_toolkit import (
    INSTRUCTION_CAP,
    ColumnWidths,
    column_widths,
    format_row,
)
from papple2.workbench.shell import ListingRow


def row(
    address: int | None,
    instruction: str,
    label: str = "",
    comment: str = "",
    hex_bytes: str = "20 3e 7a",
) -> ListingRow:
    return ListingRow(address, "", hex_bytes, label, instruction, comment)


def test_the_widths_follow_the_longest_label_and_instruction() -> None:
    rows = [
        row(0x8350, "LDY row_num", label=".loop1"),
        row(0x8352, "JSR lookup_hgr"),
    ]
    assert column_widths(rows) == ColumnWidths(label=6, instruction=14)


def test_a_very_long_instruction_is_capped() -> None:
    rows = [row(0x8352, "JSR " + "x" * 40)]
    assert column_widths(rows).instruction == INSTRUCTION_CAP


def test_a_row_lines_up_in_its_columns() -> None:
    # Label column 6 wide, instruction column 16, two spaces between.
    line = format_row(
        row(0x8352, "JSR lookup_hgr", comment="with Y"),
        ColumnWidths(label=6, instruction=16),
        columns=80,
    )
    assert line == "8352  20 3e 7a" + " " * 10 + "JSR lookup_hgr" + " " * 4 + "; with Y"


def test_a_comment_that_does_not_fit_is_cut() -> None:
    line = format_row(
        row(0x8352, "JSR lookup_hgr", comment="a long comment that does not fit"),
        ColumnWidths(label=6, instruction=16),
        columns=50,
    )
    assert line == "8352  20 3e 7a" + " " * 10 + "JSR lookup_hgr" + " " * 4 + "; a l..."
    assert len(line) == 50


def test_a_cut_instruction_ends_in_dots() -> None:
    line = format_row(
        row(0x8352, "JSR lookup_hgr"), ColumnWidths(label=0, instruction=8), 80
    )
    assert line == "8352  20 3e 7a  JSR l..."


def test_without_labels_there_is_no_label_column() -> None:
    lda = row(0x6000, "LDA #$00", hex_bytes="a9 00")
    assert format_row(lda, column_widths([lda]), 80) == "6000  a9 00     LDA #$00"


def test_the_empty_line_before_a_byte_block_is_its_gutter_alone() -> None:
    empty = ListingRow(None, "| |   ", "", "", "", "")
    assert format_row(empty, ColumnWidths(label=0, instruction=8), 80) == "| |"
