#!/usr/bin/env python3
"""Inline viewer and editor for a 6502 disassembly listing.

Supports vertical navigation, viewport scrolling and inline editing of
the label, operand and comment fields. Prevents line wrapping by turning off the
terminal's auto-wrap (\033[?7l) and by scrolling fields horizontally.

Keys:
  In navigation mode (NAV):
    Arrow UP / DOWN     : move the line cursor (scrolls at the window edge)
    Enter               : switch the line into edit mode
    q or Ctrl+C         : quit

  In edit mode (EDIT):
    Tab                 : save the field, go on to the next: Label, Operand,
                          Comment
    Arrow LEFT / RIGHT  : move the cursor in the text field
    Backspace           : delete the character before the cursor
    Typing              : insert text at the cursor
    Enter               : save the field, back to NAV
    Esc                 : back to NAV without saving: the old text returns

Saving goes through the save_edit function run_editor() is given, and after
every save the rows are loaded again, so a new label also shows in the
operands that point at its address. A refused change (e.g. a label already
used elsewhere) shows its reason in a line under the window, until the next
key; the field keeps the typed text, to fix it or to leave with Esc.

The Operand field labels the address the operand names (row.target), not
the line's own: $1a85 in LDA $1a85,Y, the pointer $1b in STA ($1b),Y. While
it is edited, it stands in for everything after the mnemonic and holds the
target's label; the line under the window says whose. Lines whose operand
names no address (implied, immediate) have no Operand field: Tab skips it.

The empty line before a .byte block is drawn empty; the cursor skips it.
"""

import copy
import os
import select
import shutil
import sys
import termios
import tty
from collections.abc import Callable

from papple2.workbench.shell import ListingRow

# A piece of Lode Runner typed in by hand, for trying the editor without a
# run: python -m papple2.workbench.listing_editor [height]. At the prompt,
# edit() in papple2.workbench.shell opens it on the current run instead.
DATA: list[ListingRow] = [
    ListingRow(0x6238, "          ", "86 a2", "ROUTINE 001", "STX $a2", ""),
    ListingRow(0x623A, "          ", "a2 ff", "", "LDX #$ff", ""),
    ListingRow(0x623C, "          ", "86 00", "", "STX $00", ""),
    ListingRow(0x623E, "          ", "e8", "", "INX", ""),
    ListingRow(0x623F, "          ", "86 a3", "", "STX $a3", ""),
    ListingRow(0x6241, "          ", "86 93", "", "STX $93", ""),
    ListingRow(0x6243, "          ", "86 8d", "", "STX $8d", ""),
    ListingRow(0x6245, "          ", "86 19", "", "STX $19", ""),
    ListingRow(0x6247, "          ", "86 a0", "", "STX $a0", ""),
    ListingRow(0x6249, "          ", "86 92", "", "STX $92", ""),
    ListingRow(0x624B, "          ", "86 1a", "", "STX $1a", ""),
    ListingRow(0x624D, "          ", "86 86", "", "STX $86", ""),
    ListingRow(0x624F, "          ", "8a", "", "TXA", ""),
    ListingRow(0x6250, "          ", "a2 1e", "", "LDX #$1e", ""),
    ListingRow(0x6252, "      +-> ", "9d e0 0c", "", "STA $0ce0,X", ""),
    ListingRow(0x6255, "      |   ", "ca", "", "DEX", ""),
    ListingRow(0x6256, "      +-- ", "10 fa", "", "BPL $6252", ""),
    ListingRow(0x6258, "          ", "a2 05", "", "LDX #$05", ""),
    ListingRow(0x625A, "      +-> ", "9d 98 0c", "", "STA $0c98,X", ""),
    ListingRow(0x625D, "      |   ", "ca", "", "DEX", ""),
    ListingRow(0x625E, "      +-- ", "10 fa", "", "BPL $625a", ""),
    ListingRow(0x6260, "          ", "a9 01", "", "LDA #$01", ""),
    ListingRow(0x6262, "          ", "85 9a", "", "STA $9a", ""),
    ListingRow(0x6264, "          ", "20 0e 63", "", "JSR $630e", ""),
    ListingRow(0x6267, "          ", "a4 86", "", "LDY $86", ""),
    ListingRow(0x6269, "+-------> ", "b9 05 1c", "", "LDA $1c05,Y", ""),
    ListingRow(0x626C, "|         ", "85 06", "", "STA $06", ""),
    ListingRow(0x626E, "|         ", "85 08", "", "STA $08", ""),
    ListingRow(0x6270, "|         ", "b9 15 1c", "", "LDA $1c15,Y", ""),
    ListingRow(0x6273, "|         ", "85 07", "", "STA $07", ""),
    ListingRow(0x6275, "|         ", "b9 25 1c", "", "LDA $1c25,Y", ""),
    ListingRow(0x6278, "|         ", "85 09", "", "STA $09", ""),
    ListingRow(0x627A, "|         ", "a9 00", "", "LDA #$00", ""),
    ListingRow(0x627C, "|         ", "85 85", "", "STA $85", ""),
    ListingRow(0x627E, "| +-----> ", "a5 1a", "", "LDA $1a", "parity of $1a: even -> low nibble, odd -> high nibble"),
    ListingRow(0x6280, "| |       ", "4a", "", "LSR", ""),
    ListingRow(0x6281, "| |       ", "a4 92", "", "LDY $92", ""),
    ListingRow(0x6283, "| |       ", "b9 00 0d", "", "LDA $0d00,Y", "byte from the buffer at $0d00, two values per byte"),
    ListingRow(0x6286, "| |   +-- ", "b0 04", "", "BCS $628c", ""),
    ListingRow(0x6288, "| |   |   ", "29 0f", "", "AND #$0f", "even: low nibble; BPL always jumps"),
    ListingRow(0x628A, "| | +---- ", "10 06", "", "BPL $6292", ""),
    ListingRow(0x628C, "| | | +-> ", "4a", "", "LSR", "odd: high nibble, then on to the next byte"),
    ListingRow(0x628D, "| | |     ", "4a", "", "LSR", ""),
    ListingRow(0x628E, "| | |     ", "4a", "", "LSR", ""),
    ListingRow(0x628F, "| | |     ", "4a", "", "LSR", ""),
    ListingRow(0x6290, "| | |     ", "e6 92", "", "INC $92", ""),
    ListingRow(0x6292, "| | +---> ", "e6 1a", "", "INC $1a", ""),
    ListingRow(0x6294, "| |       ", "a4 85", "", "LDY $85", ""),
    ListingRow(0x6296, "| |       ", "c9 0a", "", "CMP #$0a", "values 10-15 are invalid: read as 0"),
    ListingRow(0x6298, "| |   +-- ", "90 02", "", "BCC $629c", ""),
    ListingRow(0x629A, "| |   |   ", "a9 00", "", "LDA #$00", ""),
    ListingRow(0x629C, "| |   +-> ", "91 06", "", "STA ($06),Y", ""),
    ListingRow(0x629E, "| |       ", "91 08", "", "STA ($08),Y", ""),
    ListingRow(0x62A0, "| |       ", "e6 85", "", "INC $85", ""),
    ListingRow(0x62A2, "| |       ", "a5 85", "", "LDA $85", ""),
    ListingRow(0x62A4, "| |       ", "c9 1c", "", "CMP #$1c", ""),
    ListingRow(0x62A6, "| +------ ", "90 d6", "", "BCC $627e", ""),
    ListingRow(0x62A8, "|         ", "e6 86", "", "INC $86", ""),
    ListingRow(0x62AA, "|         ", "a4 86", "", "LDY $86", ""),
    ListingRow(0x62AC, "|         ", "c0 10", "", "CPY #$10", ""),
    ListingRow(0x62AE, "+-------- ", "90 b9", "", "BCC $6269", ""),
    ListingRow(0x62B0, "          ", "20 b3 63", "", "JSR $63b3", ""),
    ListingRow(0x62B3, "      +-- ", "90 0e", "", "BCC $62c3", ""),
    ListingRow(0x62B5, "      |   ", "a5 96", "", "LDA $96", ""),
    ListingRow(0x62B7, "      |   ", "f0 0b", "", "BEQ $62c4", ""),
    ListingRow(0x62B9, "      |   ", "a2 00", "", "LDX #$00", ""),
    ListingRow(0x62BB, "      |   ", "86 96", "", "STX $96", ""),
    ListingRow(0x62BD, "      |   ", "e6 97", "", "INC $97", ""),
    ListingRow(0x62BF, "      |   ", "ca", "", "DEX", ""),
    ListingRow(0x62C0, "      |   ", "4c 38 62", "", "JMP ROUTINE 001", ""),
    ListingRow(0x62C3, "      +-> ", "60", "", "RTS", ""),
]


def read_key(fd: int) -> str:
    """Read one key press from stdin, unbuffered."""
    ch = os.read(fd, 1).decode("latin1", errors="ignore")
    if ch == "\x1b":
        seq = ""
        while True:
            rlist, _, _ = select.select([fd], [], [], 0.03)
            if not rlist:
                break
            nxt = os.read(fd, 1).decode("latin1", errors="ignore")
            seq += nxt
            if nxt.isalpha() or nxt == "~":
                break

        if not seq:
            return "ESC"

        if seq in ("[A", "OA"): return "UP"
        if seq in ("[B", "OB"): return "DOWN"
        if seq in ("[C", "OC"): return "RIGHT"
        if seq in ("[D", "OD"): return "LEFT"
        if seq == "[3~": return "DELETE"
        return "ESC"

    if ch in ("\r", "\n"):
        return "ENTER"
    if ch == "\t":
        return "TAB"
    if ch in ("\x7f", "\x08"):
        return "BACKSPACE"
    if ch == "\x03":
        return "CTRL_C"
    return ch


def render_field(text: str, max_width: int, cursor_pos: int, active: bool) -> str:
    """Render a text field as exactly max_width characters.

    Cuts the text if needed, scrolls horizontally with the cursor and
    highlights the cursor position, without pushing later columns to the right.
    """
    if max_width <= 0:
        return ""

    if not active:
        # Inactive: left-aligned, padded to exactly max_width
        return text[:max_width].ljust(max_width)

    # Active: keep the cursor inside the visible part
    if cursor_pos < max_width:
        window_start = 0
    else:
        window_start = cursor_pos - max_width + 1

    # One space at the end, so the cursor can also stand behind the last character
    extended_text = text + " "
    slice_end = window_start + max_width
    visible_chars = list(extended_text[window_start:slice_end])

    # Pad to exactly max_width if the text is shorter than the column
    while len(visible_chars) < max_width:
        visible_chars.append(" ")

    visible_cursor = cursor_pos - window_start

    result = []
    for idx, char in enumerate(visible_chars):
        if idx == visible_cursor:
            result.append(f"\033[7m{char}\033[0m")
        else:
            result.append(char)
    return "".join(result)


# The fields of a line, in the order Tab goes through them.
FIELDS = ("label", "operand", "comment")


def next_field(row: ListingRow, field: str) -> str:
    """The field Tab moves on to from field, round again after the last.
    A row whose operand names no address has no Operand field."""
    order = [each for each in FIELDS if each != "operand" or row.target is not None]
    return order[(order.index(field) + 1) % len(order)]


def next_row(rows: list[ListingRow], index: int, step: int) -> int:
    """The index of the next row from index in direction step (+1 or -1)
    that has an address; index itself if there is none."""
    candidate = index + step
    while 0 <= candidate < len(rows):
        if rows[candidate].address is not None:
            return candidate
        candidate += step
    return index


def run_editor(
    load_rows: Callable[[], list[ListingRow]],
    save_edit: Callable[[int, str, str], str | None],
    window_size: int = 14,
    label_of: Callable[[int], str] = lambda address: "",
) -> None:
    """Show the rows load_rows() gives and let labels and comments be
    edited. save_edit(address, field, text) saves one field ("label" or
    "comment") and returns why it refused, or None. label_of(address) gives
    the label an address has now: the Operand field starts with the label
    of the operand's target, and saves through save_edit(target, "label",
    text)."""
    rows = load_rows()
    if not any(row.address is not None for row in rows):
        print("Nothing to edit: no lines in this range.")
        return

    window_size = min(window_size, len(rows))
    # Start on the first line with an address, not on an empty line.
    cursor_idx = next_row(rows, -1, 1)
    top_offset = 0

    mode = "NAV"  # "NAV" or "EDIT"
    edit_field = "label"  # one of FIELDS
    edit_pos = 0
    # The Operand field's text while it is edited: the label of the
    # operand's target. Unlike label and comment, it has no place in a row.
    operand_text = ""

    def field_text(row: ListingRow) -> str:
        """The text of the field being edited."""
        if edit_field == "operand":
            return operand_text
        return row.label if edit_field == "label" else row.comment

    def set_field_text(row: ListingRow, text: str) -> None:
        """Change the text of the field being edited."""
        nonlocal operand_text
        if edit_field == "operand":
            operand_text = text
        elif edit_field == "label":
            row.label = text
        else:
            row.comment = text

    def start_field(row: ListingRow) -> None:
        """Put the cursor behind the text of the field being edited. The
        Operand field first takes the target's label."""
        nonlocal operand_text, edit_pos
        if edit_field == "operand":
            operand_text = label_of(row.target)
        edit_pos = len(field_text(row))
    # Why the last save was refused; shown under the window until the next key.
    message = ""

    code_width = 16

    # The window plus one line for the message.
    screen_lines = window_size + 1

    # Reserve space below the prompt line
    sys.stdout.write("\n" * screen_lines)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        sys.stdout.write("\033[?25l\033[?7l")

        while True:
            cols = shutil.get_terminal_size((80, 24)).columns

            # The label column follows the longest label in the rows
            max_label_len = max(len(r.label) for r in rows)
            label_width = max(12, max_label_len + 2)

            # Move the viewport so the cursor stays visible
            if cursor_idx < top_offset:
                top_offset = cursor_idx
            elif cursor_idx >= top_offset + window_size:
                top_offset = cursor_idx - window_size + 1

            # Jump back to the top of the output window
            sys.stdout.write(f"\033[{screen_lines}A\r")

            for i in range(window_size):
                row_idx = top_offset + i
                row = rows[row_idx]
                is_current = row_idx == cursor_idx

                if is_current:
                    indicator = "\033[1;36m>\033[0m " if mode == "NAV" else "\033[1;33mE\033[0m "
                else:
                    indicator = "  "

                if row.address is None:  # the empty line before a .byte block
                    sys.stdout.write(f"\033[2K  {row.gutter.rstrip()}\r\n")
                    continue

                addr_str = f"{row.address:04x}  "
                bytes_str = f"{row.hex_bytes:<8}  "

                # Label field
                is_label_active = is_current and mode == "EDIT" and edit_field == "label"
                label_disp = render_field(
                    row.label, label_width, edit_pos, is_label_active
                )

                is_operand_active = is_current and mode == "EDIT" and edit_field == "operand"
                if is_operand_active:
                    # The field stands in for everything after the mnemonic,
                    # and grows with its text. Its width is counted without
                    # the cursor's escape codes, which take no room.
                    mnemonic = row.instruction.split(" ", 1)[0]
                    field_width = max(code_width - len(mnemonic) - 1, len(operand_text) + 1)
                    code_str = f"  {mnemonic} " + render_field(
                        operand_text, field_width, edit_pos, True
                    )
                    code_len = 2 + len(mnemonic) + 1 + field_width
                else:
                    code_str = f"  {row.instruction:<{code_width}}"
                    code_len = len(code_str)

                # Width left for the comment field
                fixed_prefix_len = 2 + len(row.gutter) + len(addr_str) + len(bytes_str) + label_width + code_len
                available_for_comment = max(0, cols - fixed_prefix_len - 4)  # 4 characters for '  ; '

                # Comment field
                is_comment_active = is_current and mode == "EDIT" and edit_field == "comment"
                if is_comment_active:
                    comment_disp = "  ; " + render_field(
                        row.comment, available_for_comment, edit_pos, True
                    )
                elif row.comment:
                    truncated_comment = row.comment[:available_for_comment]
                    comment_disp = f"  ; {truncated_comment}"
                else:
                    comment_disp = ""

                line_content = f"{indicator}{row.gutter}{addr_str}{bytes_str}{label_disp}{code_str}{comment_disp}"
                sys.stdout.write(f"\033[2K{line_content}\r\n")

            # While the Operand field is edited, and nothing else is to be
            # said: whose label it is.
            shown = message
            if not shown and mode == "EDIT" and edit_field == "operand":
                shown = f"label of ${rows[cursor_idx].target:04x}"
            sys.stdout.write(f"\033[2K  {shown[: max(0, cols - 3)]}\r\n")
            sys.stdout.flush()

            # Read the next key
            key = read_key(fd)
            message = ""

            if mode == "NAV":
                if key in ("q", "CTRL_C"):
                    break
                elif key == "UP":
                    cursor_idx = next_row(rows, cursor_idx, -1)
                elif key == "DOWN":
                    cursor_idx = next_row(rows, cursor_idx, 1)
                elif key == "ENTER":
                    mode = "EDIT"
                    # The field edited last, unless this line has no Operand field.
                    if edit_field == "operand" and rows[cursor_idx].target is None:
                        edit_field = "label"
                    start_field(rows[cursor_idx])

            elif mode == "EDIT":
                current_row = rows[cursor_idx]

                if key in ("ENTER", "TAB"):
                    if edit_field == "operand":
                        # The Operand field labels the operand's target.
                        message = save_edit(current_row.target, "label", operand_text) or ""
                    else:
                        message = save_edit(
                            current_row.address, edit_field, field_text(current_row)
                        ) or ""
                    if not message:
                        # Saved: load again, so operands show a new label. A
                        # label never changes the number of rows, so
                        # cursor_idx stays on the same line.
                        rows = load_rows()
                        if key == "ENTER":
                            mode = "NAV"
                        else:
                            edit_field = next_field(rows[cursor_idx], edit_field)
                            start_field(rows[cursor_idx])
                elif key == "ESC":
                    # Not saved: loading again brings the old text back.
                    rows = load_rows()
                    mode = "NAV"
                elif key == "LEFT":
                    if edit_pos > 0:
                        edit_pos -= 1
                elif key == "RIGHT":
                    current_text = field_text(current_row)
                    if edit_pos < len(current_text):
                        edit_pos += 1
                elif key == "BACKSPACE":
                    text = field_text(current_row)
                    if edit_pos > 0:
                        set_field_text(current_row, text[: edit_pos - 1] + text[edit_pos:])
                        edit_pos -= 1
                elif key == "DELETE":
                    text = field_text(current_row)
                    if edit_pos < len(text):
                        set_field_text(current_row, text[:edit_pos] + text[edit_pos + 1 :])
                elif len(key) == 1 and key.isprintable():
                    text = field_text(current_row)
                    set_field_text(current_row, text[:edit_pos] + key + text[edit_pos:])
                    edit_pos += 1

    finally:
        sys.stdout.write("\033[?25h\033[?7h")
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.flush()


def load_data() -> list[ListingRow]:
    """Stand-in for edit()'s load_rows: copies of DATA, so that Esc brings
    the saved text back, not the typed one."""
    return [copy.copy(row) for row in DATA]


def save_into_data(address: int, field: str, text: str) -> str | None:
    """Stand-in for edit()'s save_edit: keeps the change in DATA, refuses
    nothing. Operands don't change: DATA has no disassembler behind it."""
    for row in DATA:
        if row.address == address:
            setattr(row, field, text)
    return None


if __name__ == "__main__":
    height = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    run_editor(load_data, save_into_data, window_size=height)
