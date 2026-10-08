#!/usr/bin/env python3
"""The listing editor, built on prompt_toolkit.

Shows the rows of a listing inline, below the prompt, and erases itself
on exit, so nothing of it stays on the screen. The label of the bar's row,
and the label of the address its operand names, are edited in place.

Keys in the listing:
  Up / Down            : move the bar one line
  PageUp / PageDown    : move the bar one window
  Tab                  : edit the label of the bar's row
  c                    : copy the visible lines to the clipboard
  q, Esc or Ctrl+C     : leave

Keys in a field:
  Tab                  : save, then go on: label -> operand -> label
  Enter                : save, back to the listing
  Esc                  : back to the listing without saving
  Ctrl+C               : leave without saving

The operand field labels the address the operand names (row.target), not
the line's own: $1a85 in LDA $1a85,Y, the pointer $1b in STA ($1b),Y.
While it is open, the line under the listing says whose label it is. A row
whose operand names no address has no operand field: Tab stays on the
label. A refused save (e.g. a label already used elsewhere) shows its
reason in the line under the listing, and the field stays open.

After every save the rows are loaded again, so a new label also shows in
the operands that point at its address.

The columns are worked out from all rows, so they stay where they are
while the bar moves; after a save, they are worked out again. An instruction longer than INSTRUCTION_CAP is cut,
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
from collections.abc import Callable
from dataclasses import dataclass

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

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
# field: a label being edited. message: a refusal or a hint, in the line
# under the listing.
STYLE = Style.from_dict(
    {
        "bar": "bg:#303030",
        "marker": "bold ansicyan",
        "rule": "ansibrightblack",
        "field": "bg:#4a4a4a",
        "message": "ansiyellow",
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


def mnemonic(row: ListingRow) -> str:
    """The instruction's mnemonic: LDY in LDY row_num."""
    return row.instruction.split(" ", 1)[0]


def field_start(row: ListingRow, widths: ColumnWidths, field: str) -> int:
    """Where field ("label" or "operand") starts in row's line, as
    format_row() lays it out: the label column, or the operand behind the
    mnemonic."""
    start = len(f"{row.gutter}{row.address:04x}  {row.hex_bytes:<8}  ")
    if field == "label":
        return start
    if widths.label:
        start += widths.label + 2
    return start + len(mnemonic(row)) + 1


def field_width(row: ListingRow, widths: ColumnWidths, field: str, text: str) -> int:
    """How wide field is while text is typed into it: at least as wide as
    its column, so nothing of the line shows through, and one more than
    the text, for the cursor behind it."""
    if field == "label":
        column = widths.label
    else:
        column = widths.instruction - len(mnemonic(row)) - 1
    return max(column, len(text) + 1)


@dataclass
class EditorState:
    """The rows, their columns, the row the bar is on and the first row in
    the window; the field being edited ("label", "operand" or None), and
    the message for the line under the listing."""

    rows: list[ListingRow]
    widths: ColumnWidths
    cursor: int
    top: int = 0
    field: str | None = None
    message: str = ""


def keep_in_view(state: EditorState, height: int) -> None:
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


def edit_rows(
    load_rows: Callable[[], list[ListingRow]],
    save_edit: Callable[[int, str, str], str | None],
    label_of: Callable[[int], str] = lambda address: "",
    height: int = 25,
) -> None:
    """Show the rows load_rows() gives, inline, height lines at a time, and
    let labels be edited, until q, Esc or Ctrl+C. Nothing stays on the
    screen afterwards.

    save_edit(address, "label", text) saves a label and returns why it
    refused, or None; after every save the rows are loaded again.
    label_of(address) gives the label an address has now: the operand field
    starts with the label of the operand's target."""
    rows = load_rows()
    if not any(row.address is not None for row in rows):
        print("Nothing to show: no lines in this range.")
        return
    height = min(height, len(rows))
    state = EditorState(rows, column_widths(rows), cursor=next_line(rows, -1, 1))

    def visible_lines(columns: int) -> list[str]:
        return [
            format_row(row, state.widths, columns)
            for row in state.rows[state.top : state.top + height]
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

    def message_text() -> FormattedText:
        """The line under the listing: a refusal, or whose label the
        operand field holds."""
        text = state.message
        if not text and state.field == "operand":
            text = f"label of ${state.rows[state.cursor].target:04x}"
        if not text:
            return FormattedText([])
        return FormattedText(
            [("class:rule", "── "), ("class:message", text), ("class:rule", " ")]
        )

    def go(distance: int) -> None:
        state.cursor = move(state.rows, state.cursor, distance)
        keep_in_view(state, height)

    # One window less than its height, so one line of the old window
    # stays in view after a page.
    page = max(1, height - 1)

    listing = Window(
        # Focusable, so the listing has the focus: prompt_toolkit
        # hides the terminal's cursor only for the focused
        # window. Without it, the cursor blinked on and off at
        # every key press.
        FormattedTextControl(listing_text, focusable=True, show_cursor=False),
        height=height,
        wrap_lines=False,
    )
    # prompt_toolkit's own text field: cursor keys, Home/End, Backspace,
    # Delete and undo come with it.
    field = TextArea(multiline=False, wrap_lines=False, style="class:field")

    def current_field_width() -> int:
        return field_width(
            state.rows[state.cursor], state.widths, state.field or "label", field.text
        )

    # The field floats over the label or operand of the bar's row. Its
    # place is set when it opens; its width follows the text.
    field_float = Float(
        # Shown only while a field is open.
        ConditionalContainer(field, filter=Condition(lambda: state.field is not None)),
        top=0,
        left=0,
        width=current_field_width,
        height=1,
    )

    def open_field(name: str) -> None:
        """Open the field name on the bar's row, holding the label it
        edits, with the cursor behind the text."""
        row = state.rows[state.cursor]
        state.field = name
        text = row.label if name == "label" else label_of(row.target)
        field.text = text
        field.buffer.cursor_position = len(text)
        # + 1 for the rule above the listing.
        field_float.top = 1 + state.cursor - state.top
        field_float.left = MARKER_WIDTH + field_start(row, state.widths, name)
        get_app().layout.focus(field)

    def close_field() -> None:
        state.field = None
        state.message = ""
        get_app().layout.focus(listing)

    def save() -> bool:
        """Save the field's text as the label of the row, or of the
        operand's target. Refused: keep the reason for the line under the
        listing, and return False. Saved: load the rows again."""
        row = state.rows[state.cursor]
        address = row.address if state.field == "label" else row.target
        refusal = save_edit(address, "label", field.text)
        if refusal:
            state.message = refusal
            return False
        state.message = ""
        # A label never changes the number of rows, so the bar stays on
        # the same line.
        state.rows = load_rows()
        state.widths = column_widths(state.rows)
        return True

    in_listing = has_focus(listing)
    in_field = has_focus(field)
    bindings = KeyBindings()

    # The listing's keys only while it has the focus: the app's own keys
    # come before typing, so a q typed into a field would leave otherwise.

    @bindings.add("up", filter=in_listing)
    def _up(event: KeyPressEvent) -> None:
        go(-1)

    @bindings.add("down", filter=in_listing)
    def _down(event: KeyPressEvent) -> None:
        go(1)

    @bindings.add("pageup", filter=in_listing)
    def _page_up(event: KeyPressEvent) -> None:
        go(-page)

    @bindings.add("pagedown", filter=in_listing)
    def _page_down(event: KeyPressEvent) -> None:
        go(page)

    @bindings.add("c", filter=in_listing)
    def _copy(event: KeyPressEvent) -> None:
        # The lines as shown, without the marker column.
        copy_to_clipboard("\n".join(visible_lines(text_width())))

    @bindings.add("tab", filter=in_listing)
    def _edit(event: KeyPressEvent) -> None:
        open_field("label")

    @bindings.add("q", filter=in_listing)
    @bindings.add("escape", filter=in_listing)
    @bindings.add("c-c")
    def _leave(event: KeyPressEvent) -> None:
        event.app.exit()

    @bindings.add("tab", filter=in_field)
    def _next_field(event: KeyPressEvent) -> None:
        if save():
            row = state.rows[state.cursor]
            has_operand = row.target is not None
            open_field("operand" if state.field == "label" and has_operand else "label")

    @bindings.add("enter", filter=in_field)
    def _save(event: KeyPressEvent) -> None:
        if save():
            close_field()

    @bindings.add("escape", filter=in_field)
    def _cancel(event: KeyPressEvent) -> None:
        close_field()

    def rule() -> Window:
        """A thin line across the whole width."""
        return Window(height=1, char="─", style="class:rule")

    app = Application(
        layout=Layout(
            FloatContainer(
                HSplit(
                    [
                        rule(),
                        listing,
                        Window(
                            FormattedTextControl(message_text),
                            height=1,
                            char="─",
                            style="class:rule",
                        ),
                    ]
                ),
                floats=[field_float],
            ),
            focused_element=listing,
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
    # Then it waits this long for a key that would make Esc the first of a
    # two-key binding, e.g. Esc b, which Option+Left sends for word left.
    # Its default is a second; with both waits shortened, Esc closes a
    # field in about 0.1 s. Option+Left still works: both of its keys
    # arrive at once.
    app.timeoutlen = 0.05

    app.run()


if __name__ == "__main__":
    # Imported here: listing_editor needs termios, which this module
    # itself doesn't.
    from papple2.workbench.listing_editor import DATA, load_data, save_into_data

    def label_in_data(address: int) -> str:
        return next((row.label for row in DATA if row.address == address), "")

    edit_rows(
        load_data,
        save_into_data,
        label_in_data,
        int(sys.argv[1]) if len(sys.argv) > 1 else 25,
    )
