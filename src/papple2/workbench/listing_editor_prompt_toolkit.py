#!/usr/bin/env python3
"""The listing viewer, built on prompt_toolkit: the coming listing editor.

Shows the rows of a listing inline, below the prompt, and erases itself
on exit, so nothing of it stays on the screen. Step 1 of the editor in
EDITOR.md: it only shows and moves; editing follows.

Keys:
  Up / Down            : move the bar one line
  PageUp / PageDown    : move the bar one window
  c                    : copy the visible lines to the clipboard
  q, Esc or Ctrl+C     : leave

The columns are worked out once from all rows, so they stay where they are
while the bar moves. An instruction longer than INSTRUCTION_CAP is cut,
and so is a comment that doesn't fit the terminal; both end in "...".

The empty line before a .byte block is shown, but the bar skips it.

The bar's row has a cyan > in front of it and a faint background. A thin
line runs above and below the listing.

At the prompt, edit() in papple2.workbench.shell opens it on the current
run. Try it on a piece of Lode Runner typed in by hand:

    make prototype
"""

import subprocess
import sys
from dataclasses import dataclass

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

# The instruction column follows the longest instruction, up to this width.
# Beyond it, one long operand label would push every comment to the right.
INSTRUCTION_CAP = 32

# What a cut text ends in.
ELLIPSIS = "..."

# Between the instruction column and a comment.
COMMENT_START = "  ; "

# The column in front of each line, where the bar's row shows "> ".
MARKER_WIDTH = 2

# bar: the faint background of the bar's row, a little lighter than a dark
# terminal's own; change the colour here if it is too faint or too loud.
# marker: the > in front of it. rule: the lines above and below.
STYLE = Style.from_dict(
    {
        "bar": "bg:#303030",
        "marker": "bold ansicyan",
        "rule": "ansibrightblack",
    }
)


@dataclass
class ListingRow:
    """One line of a listing, its pieces kept apart, so that each caller
    lays them out as it needs: print_listing() prints them, the listing
    editor shows them in columns of its own. address is None for the empty
    line before a .byte block; there, every field but the gutter is empty.

    target is the address the operand names, the one a label in the operand
    stands for: $1a85 in LDA $1a85,Y, the pointer $1b in STA ($1b),Y, a
    branch's target. None where the operand names no address: implied,
    accumulator and immediate operands, and .byte lines."""

    address: int | None
    gutter: str
    hex_bytes: str
    label: str
    instruction: str
    comment: str
    target: int | None = None


@dataclass(frozen=True)
class ColumnWidths:
    """The widths of the columns that depend on the rows. 0 for label:
    no row has a label, so there is no label column."""

    label: int
    instruction: int


def column_widths(rows: list[ListingRow]) -> ColumnWidths:
    """The widths from all rows, not only the visible ones, so the columns
    don't move while the bar moves."""
    lines = [row for row in rows if row.address is not None]
    label = max((len(row.label) for row in lines), default=0)
    instruction = max((len(row.instruction) for row in lines), default=0)
    return ColumnWidths(label, min(instruction, INSTRUCTION_CAP))


def cut(text: str, width: int) -> str:
    """text, cut to width, ending in "..." if it was cut."""
    if len(text) <= width:
        return text
    if width <= len(ELLIPSIS):
        return text[: max(0, width)]
    return text[: width - len(ELLIPSIS)] + ELLIPSIS


def format_row(row: ListingRow, widths: ColumnWidths, columns: int) -> str:
    """One row as one line: gutter, address, bytes, label, instruction,
    comment. columns is the terminal's width: the comment is cut to fit
    it. The empty line before a .byte block is its gutter alone."""
    if row.address is None:
        return row.gutter.rstrip()
    line = f"{row.gutter}{row.address:04x}  {row.hex_bytes:<8}  "
    if widths.label:
        line += f"{row.label:<{widths.label}}  "
    line += f"{cut(row.instruction, widths.instruction):<{widths.instruction}}"
    room = columns - len(line) - len(COMMENT_START)
    if row.comment and room > 0:
        line += COMMENT_START + cut(row.comment, room)
    return line.rstrip()


def next_line(rows: list[ListingRow], index: int, step: int) -> int:
    """The index of the next row from index in direction step (+1 or -1)
    that has an address; index itself if there is none."""
    candidate = index + step
    while 0 <= candidate < len(rows):
        if rows[candidate].address is not None:
            return candidate
        candidate += step
    return index


def move(rows: list[ListingRow], index: int, distance: int) -> int:
    """Where the bar lands when it moves distance rows from index: kept
    inside the rows, and never on a row without an address. If it would
    land on one, it goes on in the same direction, or back if nothing
    lies that way."""
    target = max(0, min(len(rows) - 1, index + distance))
    if rows[target].address is not None:
        return target
    step = 1 if distance > 0 else -1
    found = next_line(rows, target, step)
    if found == target:
        found = next_line(rows, target, -step)
    return found


@dataclass
class ViewState:
    """The row the bar is on, and the first row in the window."""

    cursor: int
    top: int = 0


def keep_in_view(state: ViewState, height: int) -> None:
    """Scroll the window so that the bar's row is in it."""
    if state.cursor < state.top:
        state.top = state.cursor
    elif state.cursor >= state.top + height:
        state.top = state.cursor - height + 1


def copy_to_clipboard(text: str) -> None:
    """Copy text with pbcopy, macOS's clipboard, as clip() in shell.py
    does. Silent: a message printed while the view is open would break
    its lines."""
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass


def view_rows(rows: list[ListingRow], height: int = 25) -> None:
    """Show rows inline, height lines at a time, until q, Esc or Ctrl+C.
    Nothing stays on the screen afterwards."""
    if not any(row.address is not None for row in rows):
        print("Nothing to show: no lines in this range.")
        return
    height = min(height, len(rows))
    widths = column_widths(rows)
    state = ViewState(cursor=next_line(rows, -1, 1))

    def visible_lines(columns: int) -> list[str]:
        return [
            format_row(row, widths, columns)
            for row in rows[state.top : state.top + height]
        ]

    def text_width() -> int:
        """The terminal's width, less the marker column."""
        return get_app().output.get_size().columns - MARKER_WIDTH

    def listing_text() -> FormattedText:
        width = text_width()
        fragments = []
        for offset, text in enumerate(visible_lines(width)):
            if state.top + offset == state.cursor:
                fragments.append(("class:bar class:marker", ">".ljust(MARKER_WIDTH)))
                # The bar runs across the whole width, not only the text.
                fragments.append(("class:bar", text.ljust(width)))
            else:
                fragments.append(("", " " * MARKER_WIDTH))
                fragments.append(("", text))
            fragments.append(("", "\n"))
        fragments.pop()  # no line break after the last line
        return FormattedText(fragments)

    def go(distance: int) -> None:
        state.cursor = move(rows, state.cursor, distance)
        keep_in_view(state, height)

    # One window less than its height, so one line of the old window
    # stays in view after a page.
    page = max(1, height - 1)

    bindings = KeyBindings()

    @bindings.add("up")
    def _up(event: KeyPressEvent) -> None:
        go(-1)

    @bindings.add("down")
    def _down(event: KeyPressEvent) -> None:
        go(1)

    @bindings.add("pageup")
    def _page_up(event: KeyPressEvent) -> None:
        go(-page)

    @bindings.add("pagedown")
    def _page_down(event: KeyPressEvent) -> None:
        go(page)

    @bindings.add("c")
    def _copy(event: KeyPressEvent) -> None:
        # The lines as shown, without the marker column.
        copy_to_clipboard("\n".join(visible_lines(text_width())))

    @bindings.add("q")
    @bindings.add("escape")
    @bindings.add("c-c")
    def _leave(event: KeyPressEvent) -> None:
        event.app.exit()

    def rule() -> Window:
        """A thin line across the whole width."""
        return Window(height=1, char="─", style="class:rule")

    app = Application(
        layout=Layout(
            HSplit(
                [
                    rule(),
                    Window(
                        # Focusable, so the listing has the focus: prompt_toolkit
                        # hides the terminal's cursor only for the focused
                        # window. Without it, the cursor blinked on and off at
                        # every key press.
                        FormattedTextControl(
                            listing_text, focusable=True, show_cursor=False
                        ),
                        height=height,
                        wrap_lines=False,
                    ),
                    rule(),
                ]
            )
        ),
        key_bindings=bindings,
        style=STYLE,
        full_screen=False,
        erase_when_done=True,
    )
    # After Esc, prompt_toolkit waits this long for more keys that would
    # make it an arrow key's sequence. Its default, half a second, makes
    # leaving with Esc feel slow.
    app.ttimeoutlen = 0.05
    app.run()


if __name__ == "__main__":
    # Imported here: listing_editor needs termios, which this module
    # itself doesn't.
    from papple2.workbench.listing_editor import DATA

    view_rows(DATA, int(sys.argv[1]) if len(sys.argv) > 1 else 25)
