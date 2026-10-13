"""Shell: functions for looking at a run at the IPython prompt.

The analysis objects keep addresses as plain ints, which Python prints in
decimal. Only a function that knows what each number means can choose its
format, so these show addresses in hex, as the reports do, and leave
counts in decimal. The commands that show something (the show_ commands,
listing() and hexdump()) return it as Text, which IPython shows as Out[n]
and keeps in _; clip() copies it. The print_* functions print.

Ranges are half-open, as everywhere in the workbench: start is the first
byte, end the first byte behind. So a block printed as 6004-6007 is
listing_rows(emulator, 0x6004, 0x6007).

The reports folder is the home of an experiment: write_report() writes
there. use_reports_folder() sets it, in a recipe or at the prompt. There is
one at a time, kept in the module's Session object; reports from other
experiments are read by their full paths instead.

The dossier is everything we know about one program, in a folder of its
own (dossiers/lode_runner/). Its annotations, the labels and comments, are
one part of it, in annotations.json. use_dossier() makes a dossier the
current one; label(), comment(), unlabel() and uncomment() change its
annotations, and every change is saved at once. There is one current
dossier at a time, kept in the module's Session object. Named hidden
ranges are kept separately in hidden.json; hide() and unhide() change
their definitions.

The current run is what one run left behind: the machine and the
instrumentations that were attached to it, and, once the tiling's reports
are written, the run's routines and the graph of every block it ran.
run() only runs, with the instrumentations it is given; what is written
afterwards is up to the experiment, one command per kind of report:
tiling_reports(), stack_tracking_reports(), cross_referencing_reports().
set_current_run() sets the routines from a run made elsewhere, by its
reports. show_routines(), show_blocks(), show_callers(),
listing() and loop_reports() work on the routines, with the current
dossier's labels and comments if one is open. The print_* functions take
the objects they print instead, for any graph.
"""

import contextlib
import functools
import io
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import graphviz
from IPython import get_ipython

from papple2.core.cpu import JMP_absolute, JMP_indirect, JSR
from papple2.core.emulator import Emulator
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    Routines,
    routine_calls,
    routine_exits,
    write_loop_reports,
)
from papple2.workbench.colors import MIX_COLOR
# Not used here, but offered by the shell: listing_rows() for the
# commands on objects (docs/workbench.md), assign_lanes and draw_gutter
# for tests/test_shell.py.
from papple2.workbench.listing import (  # noqa: F401
    LISTING_COLORS,
    assign_lanes,
    draw_gutter,
    listing_rows,
    print_listing,
)
from papple2.workbench.listing_editor import Place, PickerItem, edit_rows
from papple2.workbench.memory_map import (
    has_mix,
    map_rows,
    print_map_legend,
    print_memory_map,
)
from papple2.workbench.session import Session
from papple2.workbench.tiling import address

class Text(str):
    """What a command shows, returned instead of printed. IPython shows it
    as it is, line by line, not as a string in quotes, and keeps it in _
    and Out[n]. As a str, it goes wherever text goes: str(), splitlines(),
    the clipboard."""

    def __new__(
            cls, text: str, display_text: str | None = None
    ) -> "Text":
        instance = super().__new__(cls, text)
        instance.display_text = text if display_text is None else display_text
        return instance

    def __repr__(self) -> str:
        return str(self)

    def _repr_pretty_(self, printer, cycle: bool) -> None:
        # IPython's own way to show an object; without it, IPython would
        # show a str subclass like any str, in quotes.
        printer.text(self.display_text)


def returns_text[**P](command: Callable[P, None]) -> Callable[P, Text]:
    """Make command, which prints, return what it printed as Text instead.
    The command itself keeps printing, so it stays simple, and the print_*
    functions it calls stay as they are."""

    @functools.wraps(command)
    def returning(*args: P.args, **kwargs: P.kwargs) -> Text:
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            command(*args, **kwargs)
        return Text(printed.getvalue().rstrip("\n"))

    return returning


# The state of the working session: the reports folder and the current
# dossier. Commands look `session` up when they are called, so a test can
# replace it.
session = Session()


def use_reports_folder(folder: Path) -> None:
    """Make folder the reports folder, where write_report() writes. The
    folder need not exist yet."""
    session.use_reports_folder(folder)


def write_report(file_name: str, text: str) -> None:
    """Write text into the reports folder as file_name, creating the folder
    if needed. Stops if no reports folder is set, rather than guessing one."""
    path = session.write_report(file_name, text)
    print(f"wrote {path}")


def use_dossier(folder: Path) -> None:
    """Make folder the current dossier and open its annotations, hidden
    ranges and colors. A dossier without annotations yet starts with the
    Apple II's standard labels; after that, they are left alone, so a
    removed one doesn't come back. Opening hidden ranges and colors writes
    nothing."""
    session.use_dossier(folder)


def label(address: int | str, text: str) -> None:
    """Give address, an address or a label, the label text in the current
    dossier. Given a label, this renames it."""
    session.current_annotations().label(session.address_of(address), text)


def unlabel(address: int | str) -> None:
    """Remove the label of address, an address or a label, from the current
    dossier."""
    session.current_annotations().unlabel(session.address_of(address))


def comment(address: int | str, text: str) -> None:
    """Give address, an address or a label, the comment text in the current
    dossier."""
    session.current_annotations().comment(session.address_of(address), text)


def uncomment(address: int | str) -> None:
    """Remove the comment of address, an address or a label, from the
    current dossier."""
    session.current_annotations().uncomment(session.address_of(address))


def hide(name: str, start: int | str, end: int | str, note: str) -> None:
    """Save a named hidden range in the current dossier's hidden.json.

    start and end are addresses or labels; end is exclusive. Reusing name
    replaces its definition. Overlaps with other named ranges are refused.
    Labels are read afresh before the bounds are resolved, so labels given
    in another session can be used too. No current run is required.
    """
    store = session.current_hidden()
    session.refresh_annotations()
    store.hide(name, session.address_of(start), session.address_of(end), note)


def unhide(name: str) -> None:
    """Remove a named hidden range from the current dossier."""
    session.current_hidden().unhide(name)


def color(
        name: str, start: int | str, end: int | str, shade: str
) -> None:
    """Save a named, half-open color range in the current dossier.

    Bounds are addresses or labels, resolved before saving. Reusing name
    replaces its definition; overlaps are allowed. No current run is
    required. For a routine, use color(name, *to_range(routine), shade).
    """
    store = session.current_colors()
    session.refresh_annotations()
    store.color(name, session.address_of(start), session.address_of(end), shade)


def uncolor(name: str) -> None:
    """Remove a named color range from the current dossier."""
    session.current_colors().uncolor(name)


@returns_text
def colors() -> None:
    """Show the current dossier's color definitions in address order."""
    store = session.current_colors()
    store.reload()
    if not store.ranges:
        print("no color ranges")
        return
    print(f"{'range':<9}  {'color':<7}  name")
    for name, definition in sorted(
            store.ranges.items(),
            key=lambda item: (item[1].start, item[0]),
    ):
        print(
            f"{definition.start:04x}-{definition.end:04x}  "
            f"{definition.shade:<7}  {name}"
        )


def to_range(
        start: int | str, end: int | str | None = None
) -> tuple[int, int]:
    """Return half-open bounds for argument unpacking into color().

    With start alone, return the current routine's listing bounds. With
    end, resolve both bounds as addresses or labels; no run is required.
    Labels are read afresh before resolution.
    """
    session.refresh_annotations()
    if end is None:
        return session.listing_range(start)
    return session.address_of(start), session.address_of(end)


def hx(value: int) -> Text:
    """Show value in hex, as the listings do: lowercase, with a $ and at
    least four digits, e.g. hx(0x1d26 - 0x1c9a) gives $008c. Python does
    the arithmetic; hx() only shows the result. A negative value keeps its
    sign (-$008c), and a value past $ffff shows all its digits ($1008c)."""
    sign = "-" if value < 0 else ""
    return Text(f"{sign}${abs(value):04x}")


def memory_map(
    start: int | str = 0x0000,
    end: int | str = 0x10000,
    cell_bytes: int = 0x100,
    legend: bool = True,
) -> Text:
    """Show the current dossier's color ranges from start up to, not
    including, end: 16 cells per row, each cell_bytes bytes, a power of 2.
    The default shows the whole 64 KB, a page per cell; cell_bytes=0x10
    makes each row one page. start and end are addresses or labels, and
    are rounded out to whole rows. No run is needed.

    A cell has the color of the bytes in it (Colors.color_of_bytes), light
    yellow where different colors meet. Below the map, a legend lists the
    color ranges in the range shown; legend=False leaves it out. The text
    kept for str() and clip()
    shows a letter per colored cell and dots for the others."""
    store = session.current_colors()
    session.refresh_annotations()
    first, behind = session.address_of(start), session.address_of(end)
    store.reload()
    rows = map_rows(store.color_of_bytes, first, behind, cell_bytes)
    entries = sorted(
        (
            (name, definition)
            for name, definition in store.ranges.items()
            if definition.start < behind and first < definition.end
        ),
        key=lambda item: (item[1].start, item[0]),
    )

    def shown(colored: bool) -> str:
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            print_memory_map(rows, cell_bytes, colored)
            if legend and entries:
                print()
                print_map_legend(entries, has_mix(rows), colored)
        return printed.getvalue().rstrip("\n")

    return Text(shown(colored=False), shown(colored=True))


# How show_callers() names the leaps that lead into a routine.
CALL_KINDS = {JSR: "JSR", JMP_absolute: "JMP", JMP_indirect: "JMP ()"}

# Where show_routine_graph() renders its picture: a view with the dossier's
# labels, not a report, so it goes into tmp/, not the reports folder. The
# file is tmp/routine_graph.svg.
ROUTINE_GRAPH_FILE = Path("tmp/routine_graph")

# How routine_graph() draws an exit into another routine's entry, by its
# kind: the word in front of the count, and the arrow's look. Calls (JSR)
# are drawn plain, with the count alone.
EXIT_LOOKS = {
    "jmp": ("JMP", {"style": "dashed", "color": "blue"}),
    "branch": ("branch", {"style": "dotted", "color": "darkorange"}),
    "glide": ("glide", {"style": "dashed", "color": "gray50"}),
    "stack jump": ("RTS", {"style": "bold", "color": "purple"}),
}


def set_current_run(
        emulator: Emulator,
        start: int,
        split_tiles: Path,
        split_transitions: Path,
        returns: Path | None = None,
) -> None:
    """Make the run emulator has made the current run. Its routines and the
    graph of every block are built from its two split reports, each read by
    its full path: the files are the only connection, as in the walkthrough.
    start is where the run began, which no report records. With returns,
    the stack tracking's report, the targets of the run's stack jumps
    become routines too. Every routine entry without a label gets one in
    the current dossier, see label_routines()."""
    count = session.set_current_run(
        emulator, start, split_tiles, split_transitions, returns
    )
    print(f"{count} routines")


def run(
        emulator: Emulator,
        instructions: int,
        *instrumentations: type,
) -> None:
    """Run emulator for the given number of instructions, from where its PC
    stands, with the instrumentations attached, e.g.
    run(lode_runner.boot(), 4_000_000, Tiling).

    The emulator comes ready from a program's boot(), e.g.
    papple2.programs.lode_runner.boot(): run() only runs it. Each
    instrumentation is a class, created on the emulator's CPU. run() writes
    nothing: the reports are the experiment's choice, afterwards. The
    routines of an earlier run are forgotten."""
    count, seconds = session.run(emulator, instructions, *instrumentations)
    print(f"{count:,} instructions in {seconds:.2f} s")


def tiling_reports() -> None:
    """Write the tiling reports of the current run into the reports folder,
    and build the run's routines and run graph from them: the files are the
    only connection. The run must have had Tiling attached."""
    count = session.tiling_reports()
    print(f"{count} routines")


def stack_tracking_reports() -> None:
    """Write the stack tracking report of the current run into the reports
    folder: lr_returns.csv, how every frame of the shadow stack ended. The
    run must have had StackTracking attached. If tiling_reports() has
    already built the run's routines, they are built again with the
    report, so that the targets of stack jumps become routines too."""
    count = session.stack_tracking_reports()
    if count is not None:
        print(f"{count} routines")


def cross_referencing_reports() -> None:
    """Write the cross reference report of the current run into the
    reports folder: lr_xrefs.csv, one row per instruction, kind of access,
    target and effective address, with how often, and the indexes, values
    and old values seen. The run must have had CrossReferencing attached.
    The rows are read back from the file and kept in session.run_xrefs."""
    session.cross_referencing_reports()


@returns_text
def show_routines() -> None:
    """Every routine of the current run, with the dossier's labels."""
    session.refresh_annotations()
    found = session.current_routines()
    print_routines(
        found.graphs,
        found.loops_of,
        found.calls_into,
        session.annotations.labels if session.annotations is not None else None,
    )


@returns_text
def show_blocks(entry: int | str) -> None:
    """The blocks of the routine starting at entry, an address or a label,
    with its loops and the dossier's labels."""
    session.refresh_annotations()
    found = session.current_routines()
    entry = session.routine_at(entry)
    print_blocks(
        found.graphs[entry],
        found.loops_of[entry],
        session.annotations.labels if session.annotations is not None else None,
    )


@dataclass(frozen=True)
class CallSite:
    """One place that leaps into a routine: the address of the leap, its
    opcode (JSR, JMP, JMP ()), how often it was taken, and the entries of
    the routines whose blocks hold it, in address order."""

    site: int
    opcode: int
    count: int
    holders: tuple[int, ...]


def call_sites(entry: int) -> list[CallSite]:
    """Every place in the current run that leaps into the routine starting
    at entry, in address order. Prints nothing; show_callers() prints them.

    JMPs count as callers for now: a JMP into a routine's entry may be a
    tail call, which only a shadow stack can tell apart. A site can lie in
    several routines, where code is shared, so all of them are holders."""
    found = session.current_routines()

    # Count per site and leap, adding up in case a site has several rows.
    counts: dict[tuple[int, int], int] = {}
    blocks_of: dict[int, int] = {}
    for row in session.run_transitions or []:
        if row.target_tile != entry or row.opcode not in CALL_KINDS:
            continue
        key = (row.leap_from_pc, row.opcode)
        counts[key] = counts.get(key, 0) + row.count
        blocks_of[row.leap_from_pc] = row.source_tile

    return [
        CallSite(
            site,
            opcode,
            count,
            tuple(
                sorted(
                    holder
                    for holder, graph in found.graphs.items()
                    if blocks_of[site] in graph.blocks
                )
            ),
        )
        for (site, opcode), count in sorted(counts.items())
    ]


def caller_items(entry: int) -> list[PickerItem]:
    """The callers of the routine starting at entry, as the listing
    editor's picker lists them: one line per call site and routine that
    holds it, e.g. 8352  JSR     r_11x2_1 (1,782), with the site's count.
    Enter opens that routine with the bar on the call site."""
    session.refresh_annotations()
    labels = session.annotations.labels if session.annotations is not None else {}
    items = []
    for call in call_sites(entry):
        for holder in call.holders:
            name = labels.get(holder, address(holder))
            text = (
                f"{address(call.site)}  {CALL_KINDS[call.opcode]:<6}  "
                f"{name} ({call.count:,})"
            )
            items.append(PickerItem(text, holder, call.site))
    return items


@returns_text
def show_callers(entry: int | str) -> None:
    """Every place that leaps into the routine starting at entry, an
    address or a label: one line per call site, as call_sites() finds
    them, with its leap (JSR, JMP, JMP ()), how often it was taken, and
    the routines whose blocks hold the site, with the dossier's labels."""
    session.refresh_annotations()
    entry = session.routine_at(entry)
    labels = session.annotations.labels if session.annotations is not None else {}

    calls = call_sites(entry)
    if not calls:
        print(f"no JSR or JMP leads into {address(entry)}")
        return
    print(f"{'site':<4}  {'leap':<6}  {'count':>6}  routines")
    for call in calls:
        holders = [
            f"{address(holder)} {labels.get(holder, '')}".rstrip()
            for holder in call.holders
        ]
        print(
            f"{address(call.site)}  {CALL_KINDS[call.opcode]:<6}  {call.count:>6,}  "
            + ", ".join(holders)
        )


def show_routine_graph() -> None:
    """Draw every routine of the current run, the JSRs between them and
    the edges from one into another's entry, with the dossier's labels,
    into tmp/routine_graph.svg, and put its link on the clipboard, to
    paste into a browser. It doesn't open the picture itself: the system's
    viewer for SVG may be the wrong one, e.g. Edge in the Windows VM.
    A routine that lies wholly in color ranges of one shade gets a thick
    border in that shade, as its breadcrumb in the editor does.
    Needs Graphviz's dot program."""
    session.refresh_annotations()
    found = session.current_routines()
    shades: dict[int, str] = {}
    if session.color_store is not None:
        # Read once for the whole graph, not once per routine.
        session.color_store.reload()
        for entry in found.graphs:
            shade = session.color_store.color_for_range(
                *session.listing_range(entry)
            )
            # A routine covered by ranges of different shades gets no
            # border: Graphviz knows no color by the mix color's name.
            if shade is not None and shade != MIX_COLOR:
                shades[entry] = shade
    graph = routine_graph(
        found,
        routine_calls(found, session.run_transitions or []),
        session.annotations.labels if session.annotations is not None else None,
        routine_exits(found, session.run_transitions or [], session.run_stack_jumps),
        shades,
    )
    path = graph.render(ROUTINE_GRAPH_FILE, format="svg", cleanup=True)
    print(f"wrote {path}")
    link = Path(path).resolve().as_uri()
    try:
        # pbcopy is macOS's clipboard, as in make commit-hash
        subprocess.run(["pbcopy"], input=link, text=True, check=True)
        print(f"link on the clipboard: {link}")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"link (not copied, no pbcopy): {link}")


def clip(text: str | None = None) -> None:
    """Copy text to the clipboard; without text, the last output IPython
    showed, as in _: e.g. listing("lookup_hgr"), then clip(). An older
    output by its number: clip(Out[12]). Uses pbcopy, macOS's clipboard,
    as show_routine_graph() does."""
    if text is None:
        ipython = get_ipython()
        if ipython is None:
            raise RuntimeError("not in IPython: give clip() the text to copy")
        text = ipython.user_ns.get("_", "")
    text = str(text)
    if not text:
        print("nothing to copy")
        return
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("not copied: no pbcopy")
        return
    lines = len(text.splitlines())
    print(f"copied {lines:,} line{'' if lines == 1 else 's'}")


def listing(start: int | str, end: int | str | None = None) -> Text:
    """Show the current listing with location colors, retaining plain text
    for string operations and the clipboard. Comments, arrows and collapsed
    rows remain uncolored. Bounds as for Session.current_listing_rows()."""
    rows = session.current_listing_rows(start, end)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        print_listing(rows)
    plain = printed.getvalue().rstrip("\n")

    if session.dossier_folder is None or session.color_store is None:
        return Text(plain)
    session.color_store.reload()
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        print_listing(rows, color_of=session.color_store.color_at)
    return Text(plain, printed.getvalue().rstrip("\n"))


def edit(start: int | str, end: int | str | None = None, height: int = 25) -> None:
    """Open the listing editor on the same lines listing() prints. start and
    end as for Session.current_listing_rows(). Every label and comment changed there
    is saved to the current dossier at once, through save_edit(). The
    operand field labels the address an operand names, wherever the line
    is. Enter on a JSR opens the routine it calls; each routine opens as it
    was last left, while the run lasts. g opens a list of the run's
    routines, to go to one of them; u a list of the callers of the routine
    shown, to go to one of their call sites. height is the number of lines the
    editor shows at a time. The name in an operand has the color of the
    address it names, if that address lies in a color range.

    Needs a real terminal."""
    # Stop before the editor opens, not at the first save.
    session.current_annotations()

    def color_of(entry: int) -> str | None:
        if session.color_store is None:
            return None
        session.color_store.reload()
        first, behind = session.listing_range(entry)
        return session.color_store.color_for_range(first, behind)

    def target_color_of(address: int) -> str | None:
        # Called for every visible operand on every redraw, so it reads the
        # definitions in memory: loaded below when the editor opens, and
        # again whenever color_of() reloads them for the breadcrumbs.
        if session.color_store is None:
            return None
        return session.color_store.color_at(address)

    def label_of(address: int) -> str:
        return session.current_annotations().labels.get(address, "")

    if session.color_store is not None:
        session.color_store.reload()
    if end is None:
        place = routine_place(session.routine_at(start))
    else:
        # Turned into addresses once: the editor reloads the rows after
        # every save, and a label given as start could be the one just
        # renamed.
        first, behind = session.listing_range(start, end)
        place = Place(
            first, lambda: session.current_listing_rows(first, behind), routine=False
        )
    edit_rows(
        place,
        save_edit,
        label_of,
        height,
        open_routine=routine_place,
        remembered=session.editor_views,
        goto_entries=sorted(session.current_routines().graphs),
        callers_of=caller_items,
        color_of=color_of,
        target_color_of=target_color_of,
    )


def routine_place(entry: int) -> Place | None:
    """The routine of the current run starting at entry, as the listing
    editor shows it: the whole routine, as listing(entry) lists it. None if
    no routine starts there."""
    if session.routines is None or entry not in session.routines.graphs:
        return None
    first, behind = session.listing_range(entry)
    return Place(entry, lambda: session.current_listing_rows(first, behind))


def save_edit(address: int, field: str, text: str) -> str | None:
    """Save one field the listing editor changed: field is "label" or
    "comment". Empty text removes the field's entry; text equal to the
    dossier's changes nothing, not even the file. Returns why the change
    was refused (e.g. a label already used elsewhere), or None.

    A label typed as .name is a local label: the dossier saves it by its
    full name, with the global label above it, e.g. routine_6238.loop1."""
    dossier = session.current_annotations()
    entries = dossier.labels if field == "label" else dossier.comments
    if text == entries.get(address, ""):
        return None
    try:
        if field == "label" and text:
            dossier.label(address, text)
        elif field == "label":
            dossier.unlabel(address)
        elif text:
            dossier.comment(address, text)
        else:
            dossier.uncomment(address)
    except ValueError as refusal:
        return str(refusal)
    return None


# How hexdump() lays out memory: 16 bytes per line, and 16 lines, one page,
# when no end is given.
HEXDUMP_WIDTH = 16
HEXDUMP_LINES = 16


@dataclass
class HexdumpRow:
    """One line of a hexdump: the address of its first byte, and its bytes."""

    address: int
    values: list[int]


def hexdump(start: int | str, end: int | str | None = None) -> Text:
    """Show the current run's memory from start up to, not including, end,
    16 bytes per line: hex on the left, text on the right. start and end are
    addresses or labels. start may lie anywhere in the first line, and end
    is rounded up to a full line, see hexdump_rows(). Without end, 16
    lines: one page, 256 bytes.

    Each hex byte has the color of its address, if it lies in a color
    range; the text column stays plain. The text kept for str() and clip()
    has no colors, as in listing()."""
    session.refresh_annotations()
    if session.run_emulator is None:
        raise RuntimeError("no run; call run() or set_current_run() first")
    first = session.address_of(start)
    if end is None:
        behind = first - first % HEXDUMP_WIDTH + HEXDUMP_WIDTH * HEXDUMP_LINES
    else:
        behind = session.address_of(end)
    rows = hexdump_rows(session.run_emulator, first, behind)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        print_hexdump(rows)
    plain = printed.getvalue().rstrip("\n")

    if session.dossier_folder is None or session.color_store is None:
        return Text(plain)
    session.color_store.reload()
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        print_hexdump(rows, color_of=session.color_store.color_at)
    return Text(plain, printed.getvalue().rstrip("\n"))


def hexdump_rows(emulator: Emulator, start: int, end: int) -> list[HexdumpRow]:
    """The lines of a hexdump from start up to, not including, end. start
    is rounded down to the start of its line, end up to a full line, and
    neither goes past $FFFF. Prints nothing; print_hexdump() prints them.

    The bytes come straight from the memory list, past soft switches and
    hooks: read_byte() would flip a soft switch at $C0xx."""
    # Memory's own list, read from outside on purpose, as the disassembler does.
    memory = emulator.apple2.memory._mem
    first = start - start % HEXDUMP_WIDTH
    behind = min(-(-end // HEXDUMP_WIDTH) * HEXDUMP_WIDTH, len(memory))
    return [
        HexdumpRow(address, list(memory[address : address + HEXDUMP_WIDTH]))
        for address in range(first, behind, HEXDUMP_WIDTH)
    ]


def apple_char(value: int) -> str:
    """The character a byte stands for in a hexdump's text column. Bit 7 is
    dropped, so Apple's normal text ($C1, the high bit set) and plain ASCII
    ($41) both show as A. What is not printable then shows as a dot."""
    low = value & 0x7F
    return chr(low) if 0x20 <= low < 0x7F else "."


def print_hexdump(
    rows: list[HexdumpRow],
    color_of: Callable[[int], str | None] | None = None,
) -> None:
    """Print the rows hexdump_rows() gives: address, the bytes in two groups
    of eight, and the text between bars.

    With color_of, each hex byte is printed in the color of its address;
    the spaces between the bytes, the address and the text stay plain. The
    text column is read like a comment, so it takes no color."""

    def hex_byte(address: int, value: int) -> str:
        shade = color_of(address) if color_of is not None else None
        if shade is None:
            return f"{value:02x}"
        return f"{LISTING_COLORS[shade]}{value:02x}\x1b[0m"

    for row in rows:
        values = [
            hex_byte(row.address + offset, value)
            for offset, value in enumerate(row.values)
        ]
        left = " ".join(values[:8])
        right = " ".join(values[8:])
        text = "".join(apple_char(value) for value in row.values)
        print(f"{row.address:04x}  {left}  {right}  |{text}|")



def loop_reports(entry: int | str) -> None:
    """Write the loop reports of the routine starting at entry, an address
    or a label, into the reports folder, with the entry in their names:
    lr_loops_<entry>.csv and lr_loop_members_<entry>.csv."""
    found = session.current_routines()
    entry = session.routine_at(entry)
    if session.reports_folder is None:
        raise RuntimeError("no reports folder set; call use_reports_folder() first")
    write_loop_reports(session.reports_folder, found.graphs[entry], found.loops_of[entry])


def loop_ids(loops: dict[int, Loop]) -> dict[int, str]:
    """L01, L02, ... in header-address order, as in the loop reports."""
    return {
        header: f"L{number:02d}"
        for number, header in enumerate(sorted(loops), start=1)
    }


def innermost_loop(block: int, loops: dict[int, Loop]) -> Loop | None:
    """The smallest loop whose body holds block, or None. The loops holding
    a block are nested in each other, so the smallest is the innermost."""
    containing = [loop for loop in loops.values() if block in loop.body]
    return min(containing, key=lambda loop: len(loop.body), default=None)


def print_blocks(
    graph: BlockGraph,
    loops: dict[int, Loop] | None = None,
    labels: dict[int, str] | None = None,
) -> None:
    """One line per basic block: its bytes, how often it ran, and, if loops
    are given, the innermost loop it belongs to. If labels are given, a
    block whose first address has a label shows it at the end."""
    ids = loop_ids(loops) if loops else {}
    header = f"{'block':<9}  {'runs':>6}"
    if loops:
        header += "  loop"
    if labels is not None:
        header += "  label"
    print(header)
    for start, block in graph.blocks.items():
        line = f"{address(start)}-{address(block.end)}  {block.executions:>6,}"
        if loops:
            innermost = innermost_loop(start, loops)
            loop_id = "-" if innermost is None else ids[innermost.header]
            line += f"  {loop_id:<4}"
        if labels is not None:
            line += "  " + labels.get(start, "")
        print(line.rstrip())


def print_routines(
    graphs: dict[int, BlockGraph],
    loops_of: dict[int, dict[int, Loop]],
    calls_into: dict[int, int],
    labels: dict[int, str] | None = None,
) -> None:
    """One line per routine, in address order: its entry, how many basic
    blocks and bytes it has, how often it was called, and how many loops
    it has. If labels are given, a routine whose entry has a label shows
    it at the end."""
    header = f"{'routine':<7}  {'blocks':>6}  {'bytes':>5}  {'called':>6}  {'loops':>5}"
    if labels is not None:
        header += "  label"
    print(header)
    for entry in sorted(graphs):
        blocks = graphs[entry].blocks
        size = sum(block.end - block.start for block in blocks.values())
        line = (
            f"{address(entry):<7}  {len(blocks):>6}  {size:>5}"
            f"  {calls_into[entry]:>6,}  {len(loops_of[entry]):>5}"
        )
        if labels is not None:
            line += "  " + labels.get(entry, "")
        print(line.rstrip())


def print_edges(graph: BlockGraph, loops: dict[int, Loop] | None = None) -> None:
    """One line per edge: source and target block, how often it was taken,
    and, if loops are given, which edges are back edges."""
    back_edge_of: dict[tuple[int, int], str] = {}
    if loops:
        ids = loop_ids(loops)
        for loop in loops.values():
            for edge in loop.back_edges:
                back_edge_of[edge] = ids[loop.header]
    print(f"{'edge':<12}  {'count':>6}")
    for (source, target), count in graph.edges.items():
        line = f"{address(source)} -> {address(target)}  {count:>6,}"
        if (source, target) in back_edge_of:
            line += f"  back edge of {back_edge_of[(source, target)]}"
        print(line)


def print_loops(loops: dict[int, Loop]) -> None:
    """One line per loop, in the order and with the ids of the loop
    reports: header, nesting depth, enclosing loop, back edge sources,
    member blocks."""
    ids = loop_ids(loops)
    print(
        f"{'loop':<4}  {'header':<6}  {'depth':>5}  {'outer':<5}  "
        f"{'back from':<9}  members"
    )
    for header in sorted(loops):
        loop = loops[header]
        outer = "-" if loop.parent is None else ids[loop.parent]
        sources = " ".join(address(source) for source, _ in loop.back_edges)
        members = " ".join(address(block) for block in sorted(loop.body))
        print(
            f"{ids[header]:<4}  {address(header):<6}  {loop.depth:>5}  "
            f"{outer:<5}  {sources:<9}  {members}"
        )


def routine_graph(
    routines: Routines,
    calls: dict[tuple[int, int], int],
    labels: dict[int, str] | None = None,
    exits: dict[tuple[int, int, str], int] | None = None,
    shades: dict[int, str] | None = None,
) -> graphviz.Digraph:
    """The routine graph: one box per routine, in address order, and one
    arrow per caller and callee, with how often the calls were made, as
    routine_calls() gives them. If labels are given, a routine whose entry
    has a label shows it above its address. If exits are given, as
    routine_exits() gives them, each one is one more arrow, drawn in the
    look of its kind (EXIT_LOOKS). If shades are given, a routine whose
    entry has a shade there gets a thick border in it. Draws nothing:
    render() does."""
    labels = labels or {}
    shades = shades or {}
    graph = graphviz.Digraph("routines")
    graph.attr("node", shape="box", fontname="Menlo")
    #graph.attr(rankdir="LR")
    for entry in sorted(routines.graphs):
        text = address(entry)
        if entry in labels:
            # \n, two characters: dot's own line break, centred
            text = labels[entry] + "\\n" + text
        look: dict[str, str] = {}
        if entry in shades:
            # Graphviz knows the shade names as colors: blue, cyan, ...
            look = {"color": shades[entry], "penwidth": "3"}
        graph.node(address(entry), text, **look)
    for (caller, callee), count in calls.items():
        graph.edge(address(caller), address(callee), label=f"{count:,}")
    for (source, target, kind), count in (exits or {}).items():
        word, look = EXIT_LOOKS[kind]
        graph.edge(
            address(source), address(target), label=f"{word} {count:,}", **look
        )
    return graph
