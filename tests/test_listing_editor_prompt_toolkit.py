"""Tests for the listing editor in
papple2.workbench.listing_editor_prompt_toolkit: its layout, as plain text,
and its keys, typed in through a pipe instead of a terminal."""

import threading
import time

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from papple2.workbench.listing_editor_prompt_toolkit import (
    INSTRUCTION_CAP,
    ColumnWidths,
    ListingRow,
    column_widths,
    edit_rows,
    field_start,
    format_row,
)


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


# The editor at work: keys go in through a pipe, the screen goes nowhere.
# Tab is "\t", Enter "\r", Ctrl+C "\x03", Down "\x1b[B", Esc "\x1b".

# Two rows: LDY names the address $1b, INX names none.
EDITOR_ROWS = [
    ListingRow(0x8350, "", "a4 1b", ".loop1", "LDY row_num", "with Y", target=0x1B),
    ListingRow(0x8352, "", "e8", "", "INX", ""),
]


def type_into_editor(
    keys: str | list[str],
    refusal: str | None = None,
    labels: dict[int, str] | None = None,
) -> list[tuple[int, str, str]]:
    """Run the editor on EDITOR_ROWS with keys typed in; return what it
    saved, as (address, field, text), in order. Every save is refused with
    refusal, if one is given. labels stands in for the dossier's labels.

    keys as a list is typed in pieces, with a pause after each: a lone Esc
    needs one, or the key after it would make it Esc plus that key."""
    saved = []

    def save(address: int, field: str, text: str) -> str | None:
        saved.append((address, field, text))
        return refusal

    def type_in_pieces(pipe) -> None:
        for piece in keys:
            time.sleep(0.2)
            pipe.send_text(piece)

    with create_pipe_input() as pipe:
        if isinstance(keys, str):
            pipe.send_text(keys)
        else:
            threading.Thread(target=type_in_pieces, args=(pipe,), daemon=True).start()
        with create_app_session(input=pipe, output=DummyOutput()):
            edit_rows(
                lambda: EDITOR_ROWS,
                save,
                lambda address: (labels or {}).get(address, ""),
            )
    return saved


def test_tab_opens_the_label_and_enter_saves_it() -> None:
    # The field starts with the label, the cursor behind it.
    assert type_into_editor("\tx\rq") == [(0x8350, "label", ".loop1x")]


def test_a_q_typed_into_a_field_is_text() -> None:
    # Not the key that leaves the editor.
    assert type_into_editor("\tq\rq") == [(0x8350, "label", ".loop1q")]


def test_the_operand_field_labels_the_operands_target() -> None:
    # It starts with the target's label, and saves under the target.
    assert type_into_editor("\t\tx\rq", labels={0x1B: "row_num"}) == [
        (0x8350, "label", ".loop1"),
        (0x1B, "label", "row_numx"),
    ]


def test_tab_goes_round_from_the_operand_to_the_label() -> None:
    assert type_into_editor("\t\t\t\rq") == [
        (0x8350, "label", ".loop1"),
        (0x1B, "label", ""),
        (0x8350, "label", ".loop1"),
    ]


def test_without_an_operand_address_tab_stays_on_the_label() -> None:
    # INX names no address: no operand field.
    assert type_into_editor("\x1b[B\t\t\rq") == [
        (0x8352, "label", ""),
        (0x8352, "label", ""),
    ]


def test_a_refused_save_keeps_the_field_open() -> None:
    # The second Enter saves again: the field is still open.
    assert type_into_editor("\t\r\r\x03", refusal="no") == [
        (0x8350, "label", ".loop1"),
        (0x8350, "label", ".loop1"),
    ]


def test_a_field_starts_where_format_row_puts_its_column() -> None:
    row = EDITOR_ROWS[0]
    widths = ColumnWidths(label=6, instruction=16)
    line = format_row(row, widths, 80)
    assert line[field_start(row, widths, "label") :].startswith(".loop1")
    assert line[field_start(row, widths, "operand") :].startswith("row_num")


def test_e_opens_the_comment_and_enter_saves_it() -> None:
    # The box starts with the comment, the cursor behind it.
    assert type_into_editor("e, X\rq") == [(0x8350, "comment", "with Y, X")]


def test_a_comment_can_be_given_where_there_is_none() -> None:
    assert type_into_editor("\x1b[Bedone\rq") == [(0x8352, "comment", "done")]


def test_esc_leaves_the_comment_box_without_saving() -> None:
    # Then Tab and Enter save the label: the box is closed, the listing back.
    assert type_into_editor(["eX", "\x1b", "\t\rq"]) == [
        (0x8350, "label", ".loop1")
    ]
