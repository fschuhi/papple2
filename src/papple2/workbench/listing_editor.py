#!/usr/bin/env python3
"""The listing editor, built on prompt_toolkit.

Shows the rows of a listing inline, below the prompt, and erases itself
on exit, so nothing of it stays on the screen. The label of the bar's row,
and the label of the address its operand names, are edited in place; its
comment in a box over the bottom lines of the listing.

Keys in the listing:
  Up / Down            : move the bar one line
  PageUp / PageDown    : move the bar one window
  Enter                : follow the JSR, JMP or branch on the bar's row
  Backspace            : back to where the last Enter was pressed
  f                    : forward again, to where Backspace came from
  Tab                  : edit the label of the bar's row
  e                    : edit the comment of the bar's row
  g                    : open the picker, to go to another routine
  u                    : open the picker on the callers of the routine shown
  c                    : copy the visible lines to the clipboard
  q, Esc or Ctrl+C     : leave

Keys in a field:
  Tab                  : save, then go on: label -> operand -> label
  Enter                : save, back to the listing
  Esc                  : back to the listing without saving
  Ctrl+C               : leave without saving

Keys in the comment box:
  Enter                : save, back to the listing
  Esc                  : back to the listing without saving
  Ctrl+C               : leave without saving

Keys in the picker:
  Up / Down            : move the selection one line
  Enter                : go to the selected routine
  Esc                  : back to the listing
  Ctrl+C               : leave

Ctrl keys in a field and in the comment box (prompt_toolkit's own):
  Ctrl+A / Ctrl+E      : start / end of the text (Home / End too)
  Ctrl+B / Ctrl+F      : one character left / right
  Ctrl+Left / Right    : one word left / right (Esc B / Esc F too)
  Ctrl+D / Ctrl+H      : delete the character under / before the cursor
  Ctrl+K / Ctrl+U      : delete to the end / from the start; Ctrl+U at the
                         end empties the field
  Ctrl+W               : delete the word before the cursor
  Esc D / Esc Backspace: delete the word after / before the cursor
  Ctrl+Y               : paste back what Ctrl+K, Ctrl+U or Ctrl+W deleted
  Ctrl+T               : swap the two characters before the cursor
  Ctrl+_               : undo
  Esc U / Esc L / Esc C: word to upper / lower case / capitalised

The comment box is COMMENT_LINES high and as wide as the terminal; a long
comment wraps in it, and has no line breaks of its own. In the listing, a
comment shows as one line, cut if it doesn't fit.

Enter on a JSR opens the routine it calls, and so does Enter on a JMP into
another routine's entry; Enter on a branch, or on a JMP to a row in the
listing, moves the bar there. Backspace undoes the last Enter: the same
routine, window and bar as before. f undoes the last Backspace, as long as
no new step was taken since: Enter, or going somewhere with the picker,
forgets where Backspace came from. Each routine remembers its window and
bar when it is left, and opens again as it was. The breadcrumbs in the
rule above the listing show the routines followed into, the one shown last;
a jump within a routine adds none. Behind it, in grey, the routines f
would go forward to. The editor keeps its height, whatever
the routine's length.

g opens the picker over the bottom lines of the listing, PICKER_LINES high:
a list of the routines edit_rows() was given, by entry and label, the
selection on the routine shown. Enter goes there, as Enter on a JSR would,
so Backspace comes back and the breadcrumbs grow.

u opens the same picker on the callers of the routine shown, as
edit_rows() gets them from callers_of: one line per call site, with its
leap, the routine that holds it, and how often it was taken. Enter opens
that routine with the bar on the call site, and Backspace comes back.

The operand field labels the address the operand names (row.target), not
the line's own: $1a85 in LDA $1a85,Y, the pointer $1b in STA ($1b),Y.
While it is open, the line under the listing says whose label it is. A row
whose operand names no address has no operand field: Tab stays on the
label. A refused save (e.g. a label already used elsewhere) shows its
reason in the line under the listing, and the field stays open.

After every save the rows are loaded again, so a new label also shows in
the operands that point at its address.

The columns are worked out from all rows, so they stay where they are
while the bar moves; after a save, they are worked out again. An
instruction longer than INSTRUCTION_CAP is cut, and so is a comment that
doesn't fit the terminal; both end in "...".

The empty line before a .byte block is shown, but the bar skips it.

The bar's row has a cyan > in front of it and a faint background. A thin
line runs above and below the listing.

At the prompt, edit() in papple2.workbench.shell opens it on the current
run.
"""

import subprocess
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

# How many lines of the listing the comment box covers, at most.
COMMENT_LINES = 4

# How many lines of the listing the picker covers, at most.
PICKER_LINES = 10

# The mnemonics whose target Enter follows within the listing.
BRANCHES = frozenset({"BPL", "BMI", "BVC", "BVS", "BCC", "BCS", "BNE", "BEQ"})

# Between two breadcrumbs.
CRUMB_SEPARATOR = " > "

# bar: the faint background of the bar's row, a little lighter than a dark
# terminal's own; change the colour here if it is too faint or too loud.
# marker: the > in front of it. rule: the lines above and below.
# field: a label being edited. message: a refusal or a hint, in the line
# under the listing. crumb: the routines followed into, in the line above;
# crumb-here: the one shown; crumb-future: the ones f goes forward to. picker: the picker's box; its selected line
# has the bar's look.
STYLE = Style.from_dict(
    {
        "bar": "bg:#303030",
        "marker": "bold ansicyan",
        "rule": "ansibrightblack",
        "field": "bg:#4a4a4a",
        "message": "ansiyellow",
        "crumb": "#9e9e9e",
        "crumb-here": "bold ansiwhite",
        "crumb-future": "#585858",
        "picker": "bg:#262626",
    }
)


@dataclass
class ListingRow:
    """One line of a listing, its pieces kept apart, so that each caller
    lays them out as it needs: print_listing() prints them, the listing
    editor shows them in columns of its own. address is None for a row that
    is no instruction: the empty line before a .byte block, and a gap the
    run never reached, whose text is in instruction ("... 6004-6006: 2
    bytes never ran ..."). There, every other field but the gutter is
    empty, and the bar skips the row.

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
        return (row.gutter + row.instruction).rstrip()
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


@dataclass(frozen=True)
class Place:
    """What the editor shows: the rows load_rows() gives, named in the
    breadcrumbs after entry, the address of the routine's entry. routine
    is False for a range given by its start and end, whose window and bar
    are not remembered."""

    entry: int
    load_rows: Callable[[], list[ListingRow]]
    routine: bool = True


@dataclass(frozen=True)
class PickerItem:
    """One line of the picker: its text, the entry of the routine Enter
    opens, and the address of the row the bar goes to there. Without an
    address, the routine opens as it was last left, else on its entry."""

    text: str
    entry: int
    address: int | None = None


def row_of(rows: list[ListingRow], address: int) -> int | None:
    """The index of the row at address, or None if no row is."""
    for index, row in enumerate(rows):
        if row.address == address:
            return index
    return None


def breadcrumbs(names: list[str], width: int) -> list[str]:
    """names, as they fit into width when joined by CRUMB_SEPARATOR: the
    first ones are left out if need be, with "..." in their place. The
    last one always stays."""
    if len(CRUMB_SEPARATOR.join(names)) <= width:
        return list(names)
    shown = list(names)
    while len(shown) > 1 and len(CRUMB_SEPARATOR.join([ELLIPSIS, *shown])) > width:
        shown.pop(0)
    return [ELLIPSIS, *shown]


def future_crumbs(names: list[str], room: int) -> list[str]:
    """names, the nearest first, as many as fit into room behind the
    breadcrumbs, each with CRUMB_SEPARATOR in front of it. The last ones
    are left out if need be, with "..." in their place."""
    shown: list[str] = []
    used = 0
    for index, name in enumerate(names):
        cost = len(CRUMB_SEPARATOR) + len(name)
        # If more come behind this one, keep room for the "..." standing
        # in for them.
        more = index < len(names) - 1
        reserve = len(CRUMB_SEPARATOR) + len(ELLIPSIS) if more else 0
        if used + cost + reserve > room:
            if used + len(CRUMB_SEPARATOR) + len(ELLIPSIS) <= room:
                shown.append(ELLIPSIS)
            break
        shown.append(name)
        used += cost
    return shown


@dataclass
class EditorState:
    """The rows, their columns, the row the bar is on and the first row in
    the window; the field being edited ("label", "operand", "comment" or
    None), the message for the line under the listing, and the place the
    rows come from. While the picker is open, picker holds the items it
    lists, picker_index the selected one and picker_top the first one in
    its box; picker is None while it is closed."""

    rows: list[ListingRow]
    widths: ColumnWidths
    cursor: int
    top: int = 0
    field: str | None = None
    message: str = ""
    place: Place | None = None
    picker: list[PickerItem] | None = None
    picker_index: int = 0
    picker_top: int = 0


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
    place: Place,
    save_edit: Callable[[int, str, str], str | None],
    label_of: Callable[[int], str] = lambda address: "",
    height: int = 25,
    open_routine: Callable[[int], Place | None] = lambda address: None,
    remembered: dict[int, tuple[int, int]] | None = None,
    goto_entries: list[int] | None = None,
    callers_of: Callable[[int], list[PickerItem]] = lambda entry: [],
) -> None:
    """Show the rows of place, inline, height lines at a time, and let
    labels and comments be edited, until q, Esc or Ctrl+C. Nothing stays on
    the screen afterwards.

    save_edit(address, field, text) saves a label or a comment and returns
    why it refused, or None; after every save the rows are loaded again.
    label_of(address) gives the label an address has now: the operand field
    starts with the label of the operand's target, and the breadcrumbs show
    the labels of the routines' entries. open_routine(address) gives the
    routine starting at address, or None: Enter on a JSR opens it.
    remembered keeps, by entry, the first row in the window and the bar's
    row of every routine left, (top, cursor); it outlives the editor, if
    the caller keeps it. goto_entries are the entries the picker lists, in
    the order given; g goes to one of them through open_routine().
    callers_of(entry) gives the picker's items for the callers of the
    routine starting at entry; u opens the picker on them."""
    rows = place.load_rows()
    if not any(row.address is not None for row in rows):
        print("Nothing to show: no lines in this range.")
        return
    height = min(height, len(rows))
    remembered = {} if remembered is None else remembered
    goto_entries = [] if goto_entries is None else goto_entries
    state = EditorState(rows, column_widths(rows), cursor=0, place=place)
    # Where Backspace goes: (place, top, cursor) before each Enter.
    history: list[tuple[Place, int, int]] = []
    # Where f goes: (place, top, cursor) before each Backspace, the nearest
    # last.
    future: list[tuple[Place, int, int]] = []

    def step(here: tuple[Place, int, int]) -> None:
        """Note here as where Backspace goes, before a new step. A new step
        forgets where f would have gone."""
        history.append(here)
        future.clear()

    def arrive(
        place: Place, view: tuple[int, int] | None, at: int | None = None
    ) -> None:
        """Show place, its rows loaded afresh: the window and bar as in
        view; else as remembered; else from its first row, with the bar on
        its entry. With at, the bar then goes to the row at that address,
        if there is one."""
        state.place = place
        state.rows = place.load_rows()
        state.widths = column_widths(state.rows)
        if view is None and place.routine:
            view = remembered.get(place.entry)
        if view is not None and view[1] < len(state.rows):
            state.top, state.cursor = view
        else:
            entry_row = row_of(state.rows, place.entry)
            state.top = 0
            state.cursor = (
                entry_row if entry_row is not None else next_line(state.rows, -1, 1)
            )
        keep_in_view(state, height)
        if at is not None and row_of(state.rows, at) is not None:
            state.cursor = row_of(state.rows, at)
            keep_in_view(state, height)

    def remember() -> None:
        """Keep how the routine shown looks, to show it so again."""
        if state.place.routine:
            remembered[state.place.entry] = (state.top, state.cursor)

    arrive(place, None)

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
        operand field or whose comment the box holds."""
        text = state.message
        row = state.rows[state.cursor]
        if not text and state.field == "operand":
            text = f"label of ${row.target:04x}"
        if not text and state.field == "comment":
            text = f"comment of ${row.address:04x}"
        if not text and state.picker is not None:
            text = "go to: Enter goes there, Esc closes"
        if not text:
            return FormattedText([])
        return FormattedText(
            [("class:rule", "── "), ("class:message", text), ("class:rule", " ")]
        )

    def crumbs_text() -> FormattedText:
        """The line above the listing: the routines followed into, by the
        labels of their entries, the one shown last, and behind it, in
        grey, the ones f goes forward to. A jump within a routine adds no
        crumb."""

        def name_of(entry: int) -> str:
            return label_of(entry) or f"{entry:04x}"

        entries: list[int] = []
        for followed, _top, _cursor in [*history, (state.place, 0, 0)]:
            if not entries or entries[-1] != followed.entry:
                entries.append(followed.entry)
        # The nearest first: future holds it last.
        ahead: list[int] = []
        for followed, _top, _cursor in reversed(future):
            last = ahead[-1] if ahead else entries[-1]
            if followed.entry != last:
                ahead.append(followed.entry)
        # Room for the rule's ends: "── " before, " ─" behind.
        room = text_width() + MARKER_WIDTH - 5
        shown = breadcrumbs([name_of(entry) for entry in entries], room)
        shown_ahead = future_crumbs(
            [name_of(entry) for entry in ahead],
            room - len(CRUMB_SEPARATOR.join(shown)),
        )
        fragments = [("class:rule", "── ")]
        for index, name in enumerate(shown):
            if index:
                fragments.append(("class:crumb", CRUMB_SEPARATOR))
            last = index == len(shown) - 1
            fragments.append(("class:crumb-here" if last else "class:crumb", name))
        for name in shown_ahead:
            fragments.append(("class:crumb-future", CRUMB_SEPARATOR))
            fragments.append(("class:crumb-future", name))
        fragments.append(("class:rule", " "))
        return FormattedText(fragments)

    def go(distance: int) -> None:
        state.message = ""
        state.cursor = move(state.rows, state.cursor, distance)
        keep_in_view(state, height)

    def follow() -> None:
        """Follow the leap on the bar's row: a JSR, or a JMP into another
        routine's entry, opens that routine; a branch, or a JMP to a row in
        the listing, moves the bar there. Anything else: a message."""
        state.message = ""
        row = state.rows[state.cursor]
        name = mnemonic(row)
        # JMP ($0036) names its pointer, not where it leads.
        jmp = name == "JMP" and "(" not in row.instruction
        if row.target is None or not (name == "JSR" or jmp or name in BRANCHES):
            state.message = "Enter follows a JSR, a JMP or a branch"
            return
        here = (state.place, state.top, state.cursor)
        if name == "JSR" or jmp:
            routine = open_routine(row.target)
            # A JMP back to the routine's own entry is a loop: stay.
            if routine is not None and (name == "JSR" or routine.entry != state.place.entry):
                remember()
                step(here)
                arrive(routine, None)
                return
        target_row = row_of(state.rows, row.target) if name != "JSR" else None
        if target_row is None:
            state.message = f"no routine at ${row.target:04x}"
            return
        step(here)
        state.cursor = target_row
        keep_in_view(state, height)

    def back() -> None:
        """Undo the last Enter: its place, window and bar."""
        state.message = ""
        if not history:
            state.message = "nothing to go back to"
            return
        here = (state.place, state.top, state.cursor)
        place, top, cursor = history.pop()
        remember()
        future.append(here)
        arrive(place, (top, cursor))

    def forward() -> None:
        """Undo the last Backspace: its place, window and bar."""
        state.message = ""
        if not future:
            state.message = "nothing to go forward to"
            return
        here = (state.place, state.top, state.cursor)
        place, top, cursor = future.pop()
        remember()
        history.append(here)
        arrive(place, (top, cursor))

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
        # Shown only while the label or the operand field is open, not
        # while the comment box is: it is a field of its own.
        ConditionalContainer(
            field, filter=Condition(lambda: state.field in ("label", "operand"))
        ),
        top=0,
        left=0,
        width=current_field_width,
        height=1,
    )

    # The comment box covers the bottom lines of the listing, so the editor
    # keeps its height. Fewer lines if the listing is short, so the bar's
    # row stays visible above it.
    box_lines = max(1, min(COMMENT_LINES, height - 1))
    # Multi-line, so that it wraps: a one-line field has one line. Enter
    # saves all the same: our binding comes before the one that would
    # insert a line break.
    comment_box = TextArea(multiline=True, wrap_lines=True, style="class:field")
    comment_float = Float(
        ConditionalContainer(
            comment_box, filter=Condition(lambda: state.field == "comment")
        ),
        # + 1 for the rule above the listing.
        top=1 + height - box_lines,
        left=0,
        right=0,
        height=box_lines,
    )

    def open_comment() -> None:
        """Open the comment box with the bar's row's comment, the cursor
        behind it. If the bar's row lies under the box, the listing
        scrolls up first."""
        lowest = height - box_lines - 1  # the lowest row above the box
        if state.cursor - state.top > lowest:
            state.top = state.cursor - lowest
        state.field = "comment"
        state.message = ""
        text = state.rows[state.cursor].comment
        comment_box.text = text
        comment_box.buffer.cursor_position = len(text)
        get_app().layout.focus(comment_box)

    # The picker covers the bottom lines of the listing, as the comment box
    # does, but more of them: a list wants more lines than a comment.
    picker_lines = max(1, min(PICKER_LINES, height - 1))

    def picker_text() -> FormattedText:
        """The lines of the picker's box: the items' texts, the selected
        one with the bar's look."""
        width = text_width()
        fragments = []
        shown = state.picker[state.picker_top : state.picker_top + picker_lines]
        for offset, item in enumerate(shown):
            text = item.text
            if state.picker_top + offset == state.picker_index:
                fragments.append(("class:bar class:marker", ">".ljust(MARKER_WIDTH)))
                fragments.append(("class:bar", text.ljust(width)))
            else:
                fragments.append(("", " " * MARKER_WIDTH))
                fragments.append(("", text))
            fragments.append(("", "\n"))
        if fragments:
            fragments.pop()  # no line break after the last line
        return FormattedText(fragments)

    # Focusable, so the picker's keys reach it, and not the listing's.
    picker = Window(
        FormattedTextControl(picker_text, focusable=True, show_cursor=False),
        style="class:picker",
        wrap_lines=False,
    )
    picker_float = Float(
        ConditionalContainer(
            picker, filter=Condition(lambda: state.picker is not None)
        ),
        # + 1 for the rule above the listing.
        top=1 + height - picker_lines,
        left=0,
        right=0,
        height=picker_lines,
    )

    def goto_items() -> list[PickerItem]:
        """Go To's items: every routine of goto_entries, by entry and
        label. Made each time the picker opens, so a label given since
        shows."""
        return [
            PickerItem(f"{entry:04x}  {label_of(entry)}".rstrip(), entry)
            for entry in goto_entries
        ]

    def open_picker(items: list[PickerItem], empty: str) -> None:
        """Open the picker on items, the selection on the first one that
        leads into the routine shown, else on the first one. Without items,
        empty goes into the line under the listing instead."""
        state.message = ""
        if not items:
            state.message = empty
            return
        state.picker = items
        entries = [item.entry for item in items]
        entry = state.place.entry
        state.picker_index = entries.index(entry) if entry in entries else 0
        state.picker_top = 0
        move_picker(0)
        get_app().layout.focus(picker)

    def move_picker(distance: int) -> None:
        """Move the picker's selection, kept inside the list, and scroll
        its box so that the selection is in it."""
        last = len(state.picker) - 1
        state.picker_index = max(0, min(last, state.picker_index + distance))
        if state.picker_index < state.picker_top:
            state.picker_top = state.picker_index
        elif state.picker_index >= state.picker_top + picker_lines:
            state.picker_top = state.picker_index - picker_lines + 1

    def close_picker() -> None:
        state.picker = None
        state.message = ""
        get_app().layout.focus(listing)

    def go_to_picked() -> None:
        """Go to the routine of the item selected in the picker, as Enter
        on a JSR would, and there to the item's row, if it names one.
        Picking the routine shown changes nothing."""
        item = state.picker[state.picker_index]
        close_picker()
        routine = open_routine(item.entry)
        if routine is None:
            state.message = f"no routine at ${item.entry:04x}"
            return
        if routine.entry == state.place.entry:
            return
        here = (state.place, state.top, state.cursor)
        remember()
        step(here)
        arrive(routine, None, item.address)

    def open_field(name: str) -> None:
        """Open the field name on the bar's row, holding the label it
        edits, with the cursor behind the text."""
        row = state.rows[state.cursor]
        state.field = name
        state.message = ""
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
        operand's target, or the box's text as the row's comment. Refused:
        keep the reason for the line under the listing, and return False.
        Saved: load the rows again."""
        row = state.rows[state.cursor]
        if state.field == "comment":
            refusal = save_edit(row.address, "comment", comment_box.text)
        else:
            address = row.address if state.field == "label" else row.target
            refusal = save_edit(address, "label", field.text)
        if refusal:
            state.message = refusal
            return False
        state.message = ""
        # A label never changes the number of rows, so the bar stays on
        # the same line.
        state.rows = state.place.load_rows()
        state.widths = column_widths(state.rows)
        return True

    in_listing = has_focus(listing)
    in_field = has_focus(field)
    in_comment = has_focus(comment_box)
    in_picker = has_focus(picker)
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

    @bindings.add("enter", filter=in_listing)
    def _follow(event: KeyPressEvent) -> None:
        follow()

    @bindings.add("backspace", filter=in_listing)
    def _back(event: KeyPressEvent) -> None:
        back()

    @bindings.add("f", filter=in_listing)
    def _forward(event: KeyPressEvent) -> None:
        forward()

    @bindings.add("tab", filter=in_listing)
    def _edit(event: KeyPressEvent) -> None:
        open_field("label")

    @bindings.add("e", filter=in_listing)
    def _edit_comment(event: KeyPressEvent) -> None:
        open_comment()

    @bindings.add("g", filter=in_listing)
    def _go_to(event: KeyPressEvent) -> None:
        open_picker(goto_items(), "no routines to go to")

    @bindings.add("u", filter=in_listing)
    def _callers(event: KeyPressEvent) -> None:
        if not state.place.routine:
            state.message = "u shows the callers of a routine, not of a range"
            return
        entry = state.place.entry
        open_picker(callers_of(entry), f"no JSR or JMP leads into ${entry:04x}")

    @bindings.add("up", filter=in_picker)
    def _picker_up(event: KeyPressEvent) -> None:
        move_picker(-1)

    @bindings.add("down", filter=in_picker)
    def _picker_down(event: KeyPressEvent) -> None:
        move_picker(1)

    @bindings.add("enter", filter=in_picker)
    def _picker_go(event: KeyPressEvent) -> None:
        go_to_picked()

    @bindings.add("escape", filter=in_picker)
    def _picker_close(event: KeyPressEvent) -> None:
        close_picker()

    @bindings.add("q", filter=in_listing)
    @bindings.add("escape", filter=in_listing)
    @bindings.add("c-c")
    def _leave(event: KeyPressEvent) -> None:
        remember()
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

    @bindings.add("enter", filter=in_comment)
    def _save_comment(event: KeyPressEvent) -> None:
        if save():
            close_field()

    @bindings.add("escape", filter=in_field)
    @bindings.add("escape", filter=in_comment)
    def _cancel(event: KeyPressEvent) -> None:
        close_field()

    app = Application(
        layout=Layout(
            FloatContainer(
                HSplit(
                    [
                        Window(
                            FormattedTextControl(crumbs_text),
                            height=1,
                            char="─",
                            style="class:rule",
                        ),
                        listing,
                        Window(
                            FormattedTextControl(message_text),
                            height=1,
                            char="─",
                            style="class:rule",
                        ),
                    ]
                ),
                floats=[field_float, comment_float, picker_float],
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
