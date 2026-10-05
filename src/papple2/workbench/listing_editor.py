#!/usr/bin/env python3
"""Inline viewer and editor for a 6502 disassembly listing.

Supports vertical navigation, viewport scrolling and inline editing of
the label and comment fields. Prevents line wrapping by turning off the
terminal's auto-wrap (\033[?7l) and by scrolling fields horizontally.

Keys:
  In navigation mode (NAV):
    Arrow UP / DOWN     : move the line cursor (scrolls at the window edge)
    Enter               : switch the line into edit mode
    q or Ctrl+C         : quit (prints the current annotations as JSON)

  In edit mode (EDIT):
    Tab                 : switch between 'Label' and 'Comment'
    Arrow LEFT / RIGHT  : move the cursor in the text field
    Backspace           : delete the character before the cursor
    Typing              : insert text at the cursor
    Esc or Enter        : leave edit mode, back to NAV

The empty line before a .byte block is drawn empty; the cursor skips it.
"""

import json
import os
import select
import shutil
import sys
import termios
import tty

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


def next_row(rows: list[ListingRow], index: int, step: int) -> int:
    """The index of the next row from index in direction step (+1 or -1)
    that has an address; index itself if there is none."""
    candidate = index + step
    while 0 <= candidate < len(rows):
        if rows[candidate].address is not None:
            return candidate
        candidate += step
    return index


def run_editor(rows: list[ListingRow], window_size: int = 14) -> None:
    if not any(row.address is not None for row in rows):
        print("Nothing to edit: no lines in this range.")
        return

    window_size = min(window_size, len(rows))
    # Start on the first line with an address, not on an empty line.
    cursor_idx = next_row(rows, -1, 1)
    top_offset = 0

    mode = "NAV"  # "NAV" or "EDIT"
    edit_field = 0  # 0: Label, 1: Comment
    edit_pos = 0

    code_width = 16

    # Reserve space below the prompt line
    sys.stdout.write("\n" * window_size)
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
            sys.stdout.write(f"\033[{window_size}A\r")

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
                is_label_active = is_current and mode == "EDIT" and edit_field == 0
                label_disp = render_field(
                    row.label, label_width, edit_pos, is_label_active
                )

                code_str = f"  {row.instruction:<{code_width}}"

                # Width left for the comment field
                fixed_prefix_len = 2 + len(row.gutter) + len(addr_str) + len(bytes_str) + label_width + len(code_str)
                available_for_comment = max(0, cols - fixed_prefix_len - 4)  # 4 characters for '  ; '

                # Comment field
                is_comment_active = is_current and mode == "EDIT" and edit_field == 1
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

            sys.stdout.flush()

            # Read the next key
            key = read_key(fd)

            if mode == "NAV":
                if key in ("q", "CTRL_C"):
                    break
                elif key == "UP":
                    cursor_idx = next_row(rows, cursor_idx, -1)
                elif key == "DOWN":
                    cursor_idx = next_row(rows, cursor_idx, 1)
                elif key == "ENTER":
                    mode = "EDIT"
                    current_text = rows[cursor_idx].label if edit_field == 0 else rows[cursor_idx].comment
                    edit_pos = len(current_text)

            elif mode == "EDIT":
                current_row = rows[cursor_idx]

                if key in ("ESC", "ENTER"):
                    mode = "NAV"
                elif key == "TAB":
                    edit_field = 1 - edit_field
                    current_text = current_row.label if edit_field == 0 else current_row.comment
                    edit_pos = len(current_text)
                elif key == "LEFT":
                    if edit_pos > 0:
                        edit_pos -= 1
                elif key == "RIGHT":
                    current_text = current_row.label if edit_field == 0 else current_row.comment
                    if edit_pos < len(current_text):
                        edit_pos += 1
                elif key == "BACKSPACE":
                    if edit_field == 0:
                        text = current_row.label
                        if edit_pos > 0:
                            current_row.label = text[: edit_pos - 1] + text[edit_pos:]
                            edit_pos -= 1
                    else:
                        text = current_row.comment
                        if edit_pos > 0:
                            current_row.comment = text[: edit_pos - 1] + text[edit_pos:]
                            edit_pos -= 1
                elif key == "DELETE":
                    if edit_field == 0:
                        text = current_row.label
                        if edit_pos < len(text):
                            current_row.label = text[:edit_pos] + text[edit_pos + 1 :]
                    else:
                        text = current_row.comment
                        if edit_pos < len(text):
                            current_row.comment = text[:edit_pos] + text[edit_pos + 1 :]
                elif len(key) == 1 and key.isprintable():
                    if edit_field == 0:
                        text = current_row.label
                        current_row.label = text[:edit_pos] + key + text[edit_pos:]
                        edit_pos += 1
                    else:
                        text = current_row.comment
                        current_row.comment = text[:edit_pos] + key + text[edit_pos:]
                        edit_pos += 1

    finally:
        sys.stdout.write("\033[?25h\033[?7h")
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.flush()

    labels = {f"{r.address:04x}": r.label for r in rows if r.label}
    comments = {f"{r.address:04x}": r.comment for r in rows if r.comment}
    result = {"labels": labels, "comments": comments}

    print("\n--- Current state (in the format of annotations.json) ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    height = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    run_editor(DATA, window_size=height)
