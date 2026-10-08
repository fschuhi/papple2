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
one at a time, kept in this module; reports from other experiments are
read by their full paths instead.

The dossier is everything we know about one program, in a folder of its
own (dossiers/lode_runner/). Its annotations, the labels and comments, are
one part of it, in annotations.json. use_dossier() makes a dossier the
current one; label(), comment(), unlabel() and uncomment() change its
annotations, and every change is saved at once. There is one current
dossier at a time, kept in this module.

The current run is what one run left behind: the machine and the
instrumentations that were attached to it, and, once the tiling's reports
are written, the run's routines and the graph of every block it ran.
run() only runs, with the instrumentations it is given; what is written
afterwards is up to the experiment, one command per kind of report, e.g.
tiling_reports(). set_current_run() sets the routines from a run made
elsewhere, by its reports. show_routines(), show_blocks(), show_callers(),
listing() and loop_reports() work on the routines, with the current
dossier's labels and comments if one is open. The print_* functions take
the objects they print instead, for any graph.
"""

import contextlib
import functools
import io
import re
import subprocess
import time
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import graphviz
from IPython import get_ipython

from papple2.core.cpu import JMP_absolute, JMP_indirect, JSR
from papple2.core.emulator import Emulator
from papple2.debug.disassembler import STANDARD_LABELS, Disassembler
from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.workbench.annotations import Annotations
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    Routines,
    SplitTransition,
    build_run_graph,
    find_routines,
    read_split_tiles,
    read_returns,
    read_split_transitions,
    routine_calls,
    routine_exits,
    stack_jumps,
    write_loop_reports,
)
from papple2.workbench.listing_editor_prompt_toolkit import ListingRow, view_rows
from papple2.workbench.stack_tracking import RETURNS_FILE, StackTracking
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    Tiling,
    address,
)

class Text(str):
    """What a command shows, returned instead of printed. IPython shows it
    as it is, line by line, not as a string in quotes, and keeps it in _
    and Out[n]. As a str, it goes wherever text goes: str(), splitlines(),
    the clipboard."""

    def __repr__(self) -> str:
        return str(self)

    def _repr_pretty_(self, printer, cycle: bool) -> None:
        # IPython's own way to show an object; without it, IPython would
        # show a str subclass like any str, in quotes.
        printer.text(str(self))


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


# Where write_report() writes; None until use_reports_folder() is called.
reports_folder: Path | None = None


def use_reports_folder(folder: Path) -> None:
    """Make folder the reports folder, where write_report() writes. The
    folder need not exist yet."""
    global reports_folder
    reports_folder = Path(folder)


def write_report(file_name: str, text: str) -> None:
    """Write text into the reports folder as file_name, creating the folder
    if needed. Stops if no reports folder is set, rather than guessing one."""
    if reports_folder is None:
        raise RuntimeError("no reports folder set; call use_reports_folder() first")
    path = reports_folder / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


# The current dossier's folder, and the annotations read from it; None
# until use_dossier() is called.
dossier_folder: Path | None = None
annotations: Annotations | None = None


def use_dossier(folder: Path) -> None:
    """Make folder the current dossier and open its annotations. A dossier
    without annotations yet starts with the Apple II's standard labels;
    after that, they are left alone, so a removed one doesn't come back."""
    global dossier_folder, annotations
    dossier_folder = Path(folder)
    annotations = Annotations(dossier_folder)
    if not annotations.path.exists():
        annotations.add_labels(STANDARD_LABELS)


def current_annotations() -> Annotations:
    """The current dossier's annotations. Stops if no dossier is open."""
    if annotations is None:
        raise RuntimeError("no dossier open; call use_dossier() first")
    return annotations


def refresh_annotations() -> None:
    """Read the current dossier's annotations from the file again, so that
    labels and comments given in another session show too. Without an open
    dossier, nothing happens."""
    if annotations is not None:
        annotations.reload()


def address_of(place: int | str) -> int:
    """place itself if it is an address; if it is a label, the address the
    current dossier gives it. A label names one address only: the dossier
    refuses a text used twice."""
    if isinstance(place, int):
        return place
    for labelled, text in current_annotations().labels.items():
        if text == place:
            return labelled
    raise ValueError(f"no label {place} in the dossier")


def label(address: int, text: str) -> None:
    """Give address the label text in the current dossier."""
    current_annotations().label(address, text)


def unlabel(address: int) -> None:
    """Remove address's label from the current dossier."""
    current_annotations().unlabel(address)


def comment(address: int, text: str) -> None:
    """Give address the comment text in the current dossier."""
    current_annotations().comment(address, text)


def uncomment(address: int) -> None:
    """Remove address's comment from the current dossier."""
    current_annotations().uncomment(address)


# The current run: the program setup it ran, the machine as the run left
# it (listing() reads its memory), its RWTS stand-in, and the
# instrumentations that were attached, in the order given to run(). None
# (or empty) until run() is called.
run_program: ModuleType | None = None
run_emulator: Emulator | None = None
run_rwts = None
run_instrumentations: list = []
# The run's routines and the graph of every block it ran (listing()'s
# arrows), built from the tiling's split reports. None until
# tiling_reports() or set_current_run() is called.
routines: Routines | None = None
run_graph: BlockGraph | None = None
# The run's split transitions, as read from its report: who leapt where,
# and how often. show_callers() reads them. None until tiling_reports() or
# set_current_run() is called.
run_transitions: list[SplitTransition] | None = None
# The run's stack jumps, (address of the RTS, target) -> how often, as
# stack_jumps() finds them in the stack tracking's report. None until
# set_current_run() is given that report.
run_stack_jumps: dict[tuple[int, int], int] | None = None

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
    global run_emulator, routines, run_graph, run_transitions, run_stack_jumps
    tiles = read_split_tiles(split_tiles)
    transitions = read_split_transitions(split_transitions)
    run_stack_jumps = (
        stack_jumps(read_returns(returns), transitions) if returns else None
    )
    # How often each target was entered by a stack jump.
    entered: dict[int, int] = {}
    for (_, target), count in (run_stack_jumps or {}).items():
        entered[target] = entered.get(target, 0) + count
    run_emulator = emulator
    routines = find_routines(tiles, transitions, start, entered)
    run_graph = build_run_graph(tiles, transitions, start)
    run_transitions = transitions
    print(f"{len(routines.graphs)} routines")
    label_routines()


def label_routines() -> None:
    """Give every entry of the current run's routines that has no label the
    name routine_6238, after its address, in the current dossier. Entries
    with a label keep it, so names given by hand stay. A global label at
    every entry keeps local labels from belonging to the routine above.
    Without an open dossier, nothing happens."""
    if annotations is None or routines is None:
        return
    annotations.add_labels({entry: f"routine_{entry:04x}" for entry in routines.graphs})


def run(
        program: ModuleType,
        instructions: int,
        *instrumentations: type,
        binary: str | None = None,
) -> None:
    """Run program headless for the given number of instructions, with the
    instrumentations attached, e.g. run(lode_runner, 4_000_000, Tiling).

    program is a program setup from papple2.programs, e.g. lode_runner:
    its boot() loads and starts it from binary, or from its DEFAULT_BINARY.
    Each instrumentation is a class, created on the booted machine's CPU.
    run() writes nothing: the reports are the experiment's choice,
    afterwards. The routines of an earlier run are forgotten."""
    global run_program, run_emulator, run_rwts, run_instrumentations
    global routines, run_graph, run_transitions, run_stack_jumps
    emulator, rwts = program.boot(binary or program.DEFAULT_BINARY, headless=True)
    attached = [instrumentation(emulator.cpu) for instrumentation in instrumentations]
    for instrumentation in attached:
        emulator.attach(instrumentation)

    start = time.perf_counter()
    try:
        emulator.run(until=instruction_count_reaches(instructions))
    finally:
        seconds = time.perf_counter() - start
        for instrumentation in attached:
            emulator.detach(instrumentation)
    print(f"{emulator.instructions:,} instructions in {seconds:.2f} s")

    run_program = program
    run_emulator = emulator
    run_rwts = rwts
    run_instrumentations = attached
    routines = None
    run_graph = None
    run_transitions = None
    run_stack_jumps = None


def tiling_reports() -> None:
    """Write the tiling reports of the current run into the reports folder,
    and build the run's routines and run graph from them: the files are the
    only connection. The run must have had Tiling attached."""
    if run_emulator is None or run_program is None:
        raise RuntimeError("no run; call run() first")
    tilings = [each for each in run_instrumentations if isinstance(each, Tiling)]
    if not tilings:
        raise RuntimeError(
            "the current run had no Tiling attached; run(program, n, Tiling)"
        )
    if reports_folder is None:
        raise RuntimeError("no reports folder set; call use_reports_folder() first")
    # The emulator counts from 0, so emulator.instructions is what ran while
    # the tiling was attached.
    tilings[0].write_reports(
        reports_folder, run_emulator.instructions, len(run_rwts.log)
    )
    set_current_run(
        run_emulator,
        run_program.LOAD_ADDRESS,
        reports_folder / SPLIT_TILES_FILE,
        reports_folder / SPLIT_TRANSITIONS_FILE,
    )


def stack_tracking_reports() -> None:
    """Write the stack tracking report of the current run into the reports
    folder: lr_returns.csv, how every frame of the shadow stack ended. The
    run must have had StackTracking attached. If tiling_reports() has
    already built the run's routines, they are built again with the
    report, so that the targets of stack jumps become routines too."""
    if run_emulator is None:
        raise RuntimeError("no run; call run() first")
    trackings = [
        each for each in run_instrumentations if isinstance(each, StackTracking)
    ]
    if not trackings:
        raise RuntimeError(
            "the current run had no StackTracking attached; "
            "run(program, n, StackTracking)"
        )
    if reports_folder is None:
        raise RuntimeError("no reports folder set; call use_reports_folder() first")
    trackings[0].write_reports(reports_folder)
    if routines is not None:
        set_current_run(
            run_emulator,
            run_program.LOAD_ADDRESS,
            reports_folder / SPLIT_TILES_FILE,
            reports_folder / SPLIT_TRANSITIONS_FILE,
            returns=reports_folder / RETURNS_FILE,
        )


def current_routines() -> Routines:
    """The current run's routines. Stops if there is no current run."""
    if routines is None:
        raise RuntimeError(
            "no routines; call tiling_reports() after run(), or set_current_run()"
        )
    return routines


def routine_at(entry: int | str) -> int:
    """The address of entry, an address or a label, if a routine of the
    current run starts there; stops if not."""
    entry = address_of(entry)
    if entry not in current_routines().graphs:
        raise ValueError(
            f"{address(entry)} is not a routine; show_routines() lists them"
        )
    return entry


@returns_text
def show_routines() -> None:
    """Every routine of the current run, with the dossier's labels."""
    refresh_annotations()
    found = current_routines()
    print_routines(
        found.graphs,
        found.loops_of,
        found.calls_into,
        annotations.labels if annotations is not None else None,
    )


@returns_text
def show_blocks(entry: int | str) -> None:
    """The blocks of the routine starting at entry, an address or a label,
    with its loops and the dossier's labels."""
    refresh_annotations()
    found = current_routines()
    entry = routine_at(entry)
    print_blocks(
        found.graphs[entry],
        found.loops_of[entry],
        annotations.labels if annotations is not None else None,
    )


@returns_text
def show_callers(entry: int | str) -> None:
    """Every place that leaps into the routine starting at entry, an
    address or a label: one line per call site, in address order, with
    its leap (JSR, JMP, JMP ()), how often it was taken, and the routines
    whose blocks hold the site, with the dossier's labels.

    JMPs count as callers for now: a JMP into a routine's entry may be a
    tail call, which only a shadow stack can tell apart. A site can lie in
    several routines, where code is shared, so all of them are listed."""
    refresh_annotations()
    found = current_routines()
    entry = routine_at(entry)
    labels = annotations.labels if annotations is not None else {}

    # Count per site and leap, adding up in case a site has several rows.
    counts: dict[tuple[int, int], int] = {}
    blocks_of: dict[int, int] = {}
    for row in run_transitions or []:
        if row.target_tile != entry or row.opcode not in CALL_KINDS:
            continue
        key = (row.leap_from_pc, row.opcode)
        counts[key] = counts.get(key, 0) + row.count
        blocks_of[row.leap_from_pc] = row.source_tile

    if not counts:
        print(f"no JSR or JMP leads into {address(entry)}")
        return
    print(f"{'site':<4}  {'leap':<6}  {'count':>6}  routines")
    for (site, opcode), count in sorted(counts.items()):
        holders = [
            f"{address(holder)} {labels.get(holder, '')}".rstrip()
            for holder, graph in found.graphs.items()
            if blocks_of[site] in graph.blocks
        ]
        print(
            f"{address(site)}  {CALL_KINDS[opcode]:<6}  {count:>6,}  "
            + ", ".join(sorted(holders))
        )


def show_routine_graph() -> None:
    """Draw every routine of the current run, the JSRs between them and
    the edges from one into another's entry, with the dossier's labels,
    into tmp/routine_graph.svg, and put its link on the clipboard, to
    paste into a browser. It doesn't open the picture itself: the system's
    viewer for SVG may be the wrong one, e.g. Edge in the Windows VM.
    Needs Graphviz's dot program."""
    refresh_annotations()
    found = current_routines()
    graph = routine_graph(
        found,
        routine_calls(found, run_transitions or []),
        annotations.labels if annotations is not None else None,
        routine_exits(found, run_transitions or [], run_stack_jumps),
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


def listing_range(
    start: int | str, end: int | str | None = None
) -> tuple[int, int]:
    """The addresses from start up to, not including, end. start and end are
    addresses or labels.

    With start alone, start is a routine's entry, and the range covers the
    whole routine: from its lowest block to its highest, so any gap between
    its blocks shows too, e.g. code the run never reached."""
    found = current_routines()
    if end is None:
        blocks = found.graphs[routine_at(start)].blocks.values()
        return (
            min(block.start for block in blocks),
            max(block.end for block in blocks),
        )
    return address_of(start), address_of(end)


def current_listing_rows(
    start: int | str, end: int | str | None = None
) -> list[ListingRow]:
    """The rows of the current run's memory in the range listing_range()
    gives, with the arrows of the whole run and the dossier's labels and
    comments. The annotations are read from the file first, so a listing,
    and the editor after every save or Esc, shows what another session
    has given."""
    refresh_annotations()
    start, end = listing_range(start, end)
    return listing_rows(
        run_emulator,
        start,
        end,
        annotations.labels if annotations is not None else None,
        run_graph,
        annotations.comments if annotations is not None else None,
    )


@returns_text
def listing(start: int | str, end: int | str | None = None) -> None:
    """Print the listing of the current run's memory from start up to, not
    including, end. start and end as for current_listing_rows()."""
    print_listing(current_listing_rows(start, end))


def edit(start: int | str, end: int | str | None = None, height: int = 25) -> None:
    """Open the listing editor on the same lines listing() prints. start and
    end as for current_listing_rows(). height is the number of lines the
    editor shows at a time. It shows and moves for now; until it edits,
    label() and comment() give labels and comments at the prompt.

    Needs a real terminal, so it doesn't work under pytest."""
    view_rows(current_listing_rows(start, end), height)


def save_edit(address: int, field: str, text: str) -> str | None:
    """Save one field the listing editor changed: field is "label" or
    "comment". Empty text removes the field's entry; text equal to the
    dossier's changes nothing, not even the file. Returns why the change
    was refused (e.g. a label already used elsewhere), or None.

    A label typed as .name is a local label: the dossier saves it by its
    full name, with the global label above it, e.g. routine_6238.loop1."""
    dossier = current_annotations()
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


@returns_text
def hexdump(start: int | str, end: int | str | None = None) -> None:
    """Print the current run's memory from start up to, not including, end,
    16 bytes per line: hex on the left, text on the right. start and end are
    addresses or labels. start may lie anywhere in the first line, and end
    is rounded up to a full line, see hexdump_rows(). Without end, 16
    lines: one page, 256 bytes."""
    refresh_annotations()
    if run_emulator is None:
        raise RuntimeError("no run; call run() or set_current_run() first")
    first = address_of(start)
    if end is None:
        behind = first - first % HEXDUMP_WIDTH + HEXDUMP_WIDTH * HEXDUMP_LINES
    else:
        behind = address_of(end)
    print_hexdump(hexdump_rows(run_emulator, first, behind))


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


def print_hexdump(rows: list[HexdumpRow]) -> None:
    """Print the rows hexdump_rows() gives: address, the bytes in two groups
    of eight, and the text between bars."""
    for row in rows:
        left = " ".join(f"{value:02x}" for value in row.values[:8])
        right = " ".join(f"{value:02x}" for value in row.values[8:])
        text = "".join(apple_char(value) for value in row.values)
        print(f"{row.address:04x}  {left}  {right}  |{text}|")



def loop_reports(entry: int | str) -> None:
    """Write the loop reports of the routine starting at entry, an address
    or a label, into the reports folder, with the entry in their names:
    lr_loops_<entry>.csv and lr_loop_members_<entry>.csv."""
    found = current_routines()
    entry = routine_at(entry)
    if reports_folder is None:
        raise RuntimeError("no reports folder set; call use_reports_folder() first")
    write_loop_reports(reports_folder, found.graphs[entry], found.loops_of[entry])


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
) -> graphviz.Digraph:
    """The routine graph: one box per routine, in address order, and one
    arrow per caller and callee, with how often the calls were made, as
    routine_calls() gives them. If labels are given, a routine whose entry
    has a label shows it above its address. If exits are given, as
    routine_exits() gives them, each one is one more arrow, drawn in the
    look of its kind (EXIT_LOOKS). Draws nothing: render() does."""
    labels = labels or {}
    graph = graphviz.Digraph("routines")
    graph.attr("node", shape="box", fontname="Menlo")
    #graph.attr(rankdir="LR")
    for entry in sorted(routines.graphs):
        text = address(entry)
        if entry in labels:
            # \n, two characters: dot's own line break, centred
            text = labels[entry] + "\\n" + text
        graph.node(address(entry), text)
    for (caller, callee), count in calls.items():
        graph.edge(address(caller), address(callee), label=f"{count:,}")
    for (source, target, kind), count in (exits or {}).items():
        word, look = EXIT_LOOKS[kind]
        graph.edge(
            address(source), address(target), label=f"{word} {count:,}", **look
        )
    return graph


def assign_lanes(spans: list[tuple[int, int]]) -> list[int]:
    """Give each arrow a lane in the gutter; lane 0 lies next to the code.

    An arrow is given as the span of rows it covers, (first, last). Shorter
    arrows are placed first, each into the lowest lane that holds no arrow
    sharing a row with it. So an arrow inside another one gets the lane
    nearer the code, and arrows that don't overlap can share a lane.
    """
    order = sorted(
        range(len(spans)),
        key=lambda i: (spans[i][1] - spans[i][0], spans[i][0]),
    )
    lanes = [0] * len(spans)
    occupied: list[list[tuple[int, int]]] = []  # the spans in each lane
    for i in order:
        first, last = spans[i]
        lane = 0
        while lane < len(occupied) and any(
            first <= other_last and other_first <= last
            for other_first, other_last in occupied[lane]
        ):
            lane += 1
        if lane == len(occupied):
            occupied.append([])
        occupied[lane].append((first, last))
        lanes[i] = lane
    return lanes


def draw_gutter(
    row_count: int, arrows: list[tuple[int, int]], lanes: list[int]
) -> list[str]:
    """The gutter left of the code, one string per row.

    arrows are (source row, target row), lanes as assign_lanes() gives
    them. Each lane is two characters wide, followed by two for the arrow
    heads. An arrow starts with "+--" at its source and ends with "+->"
    at its target, and "|" joins the two. No arrows, no gutter.
    """
    if not arrows:
        return [""] * row_count
    lane_count = max(lanes) + 1
    width = 2 * lane_count + 2
    cells = [[" "] * width for _ in range(row_count)]
    # Outer lanes first, so an inner arrow's corner is drawn over an outer
    # arrow's line where the two meet in one row.
    for (source, target), lane in sorted(
        zip(arrows, lanes), key=lambda item: -item[1]
    ):
        column = 2 * (lane_count - 1 - lane)
        for row in range(min(source, target) + 1, max(source, target)):
            if cells[row][column] == " ":
                cells[row][column] = "|"
        # The target is drawn last, so an arrow to its own row shows ">".
        for row, head in ((source, "-"), (target, ">")):
            cells[row][column] = "+"
            for between in range(column + 1, width - 2):
                cells[row][between] = "-"
            cells[row][width - 2] = head
    return ["".join(row) for row in cells]


def listing_rows(
    emulator: Emulator,
    start: int,
    end: int,
    labels: dict[int, str] | None = None,
    graph: BlockGraph | None = None,
    comments: dict[int, str] | None = None,
) -> list[ListingRow]:
    """The rows of a listing from start up to, not including, end, one per
    instruction: address, bytes, instruction. Read from the emulator's
    memory as it is now, i.e. after the run, past anything that watches the
    CPU. Prints nothing; print_listing() prints the rows.

    With labels, an operand whose address has a name shows the name
    (JSR SUB instead of JSR $6010), and an instruction whose own address
    has a name carries it in its label. A local label (routine_6238.loop1)
    shows by its short part, .loop1: always in the label column, since the
    dossier keeps every local label under the global label above it; in an
    operand only if the line lies in the same scope, i.e. under the same
    global label. An operand leading into another scope shows the full name.

    With comments, an instruction whose own address has a comment carries
    it in its comment.

    With graph, the jumps the run took are drawn as arrows in the gutter:
    every edge whose target is not simply the next instruction (taken
    branches, JMPs). Glides, fall-throughs and calls are not drawn. An
    arrow is drawn only if both of its ends lie in the range.

    An instruction that starts before end is listed whole, even if its
    operand reaches past end. A block's end always lies behind its last
    instruction, so this only shows for ranges that cut an instruction.

    Each instruction's row carries the address its operand names in target,
    as the disassembler works it out, so the listing editor can label it.
    """
    disassembler = Disassembler(emulator.cpu, labels, comments)
    # disassemble() takes an inclusive end.
    rows = disassembler.disassemble(start, end - 1)
    gutter = draw_gutter(len(rows), *arrows_in(rows, graph))
    # The addresses of the global labels, sorted, to find each line's scope.
    global_addresses = sorted(
        address for address, text in (labels or {}).items() if "." not in text
    )
    result = []
    for row, prefix in zip(rows, gutter):
        row_address, row_bytes, label, mnemonic, operand, comment = row
        instruction = f"{mnemonic} {operand}".rstrip()
        target = None
        if row_address:
            # The disassembler gives "$6004": four hex digits behind the "$".
            address = int(row_address.removeprefix("$"), 16)
            if "." in label:
                label = label[label.index(".") :]
            owner = scope_of(address, global_addresses, labels or {})
            if owner is not None:
                instruction = shorten_locals(instruction, owner)
            if mnemonic != ".byte":
                info, _length = disassembler.collect_op_info(address)
                target = info.get("operand_address")
        else:  # the empty line before a .byte block
            address = None
        result.append(
            ListingRow(
                address=address,
                gutter=prefix,
                hex_bytes=row_bytes,
                label=label,
                instruction=instruction,
                comment=comment,
                target=target,
            )
        )
    return result


def scope_of(
    address: int, global_addresses: list[int], labels: dict[int, str]
) -> str | None:
    """The global label whose scope address lies in: the one at address
    itself or the nearest above it. None above the first global label.
    global_addresses holds the addresses of labels' global labels, sorted."""
    index = bisect_right(global_addresses, address) - 1
    if index < 0:
        return None
    return labels[global_addresses[index]]


def shorten_locals(instruction: str, owner: str) -> str:
    """instruction with owner's local labels shown short: BNE
    routine_6238.loop1 -> BNE .loop1, if owner is routine_6238. A name that
    only ends in the owner's name (xroutine_6238.loop1) is left alone."""
    return re.sub(
        rf"(?<![A-Za-z0-9_:.]){re.escape(owner)}\.(?=[A-Za-z0-9_])",
        ".",
        instruction,
    )


def print_listing(rows: list[ListingRow]) -> None:
    """Print the rows listing_rows() gives: gutter, address, bytes, label,
    instruction, comment.

    The label column is as wide as the longest label in the rows, and left
    out if no row has a label. The comments line up two spaces after the
    widest commented instruction, so .byte lines don't push them out; lines
    without a comment end with their instruction.
    """
    width = max((len(row.label) for row in rows), default=0)
    instruction_width = max(
        (len(row.instruction) for row in rows if row.comment), default=0
    )
    for row in rows:
        if row.address is None:  # the empty line before a .byte block
            print(row.gutter.rstrip())
            continue
        name_column = f"{row.label:<{width}}  " if width else ""
        instruction = row.instruction
        if row.comment:
            instruction = f"{instruction:<{instruction_width}}  ; {row.comment}"
        print(
            f"{row.gutter}{row.address:04x}  {row.hex_bytes:<8}  "
            f"{name_column}{instruction}".rstrip()
        )


def arrows_in(
    rows: list[list[str]], graph: BlockGraph | None
) -> tuple[list[tuple[int, int]], list[int]]:
    """The arrows for the rows of a listing, as (source row, target row),
    and their lanes. An arrow starts at the last instruction of an edge's
    source block, the leap, and ends at the edge's target."""
    if graph is None:
        return [], []
    # Row number of each instruction, by its address; empty lines and
    # .byte blocks are no instructions.
    row_of = {
        int(row[0].removeprefix("$"), 16): number
        for number, row in enumerate(rows)
        if row[0] and row[3] != ".byte"
    }
    arrows = []
    for (source, target), _count in graph.edges.items():
        block = graph.blocks[source]
        if target == block.end:  # just the next instruction: no arrow
            continue
        leaps = [address for address in row_of if source <= address < block.end]
        if not leaps or target not in row_of:  # an end lies outside the range
            continue
        arrows.append((row_of[max(leaps)], row_of[target]))
    spans = [(min(source, target), max(source, target)) for source, target in arrows]
    return arrows, assign_lanes(spans)
