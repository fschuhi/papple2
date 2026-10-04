"""Shell: functions for looking at a run at the IPython prompt.

The analysis objects keep addresses as plain ints, which Python prints in
decimal. Only a function that knows what each number means can choose its
format, so these print addresses in hex, as the reports do, and leave
counts in decimal. They print and return nothing, so IPython adds no
output line of its own.

Ranges are half-open, as everywhere in the workbench: start is the first
byte, end the first byte behind. So a block printed as 6004-6007 is
dis(emulator, 0x6004, 0x6007).

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

import time
from pathlib import Path
from types import ModuleType

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
    read_split_transitions,
    write_loop_reports,
)
from papple2.workbench.stack_tracking import StackTracking
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    Tiling,
    address,
)

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

# How show_callers() names the leaps that lead into a routine.
CALL_KINDS = {JSR: "JSR", JMP_absolute: "JMP", JMP_indirect: "JMP ()"}


def set_current_run(
        emulator: Emulator, start: int, split_tiles: Path, split_transitions: Path
) -> None:
    """Make the run emulator has made the current run. Its routines and the
    graph of every block are built from its two split reports, each read by
    its full path: the files are the only connection, as in the walkthrough.
    start is where the run began, which no report records."""
    global run_emulator, routines, run_graph, run_transitions
    tiles = read_split_tiles(split_tiles)
    transitions = read_split_transitions(split_transitions)
    run_emulator = emulator
    routines = find_routines(tiles, transitions, start)
    run_graph = build_run_graph(tiles, transitions, start)
    run_transitions = transitions
    print(f"{len(routines.graphs)} routines")


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
    global routines, run_graph, run_transitions
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
    run must have had StackTracking attached."""
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


def show_routines() -> None:
    """Every routine of the current run, with the dossier's labels."""
    found = current_routines()
    print_routines(
        found.graphs,
        found.loops_of,
        found.calls_into,
        annotations.labels if annotations is not None else None,
    )


def show_blocks(entry: int | str) -> None:
    """The blocks of the routine starting at entry, an address or a label,
    with its loops and the dossier's labels."""
    found = current_routines()
    entry = routine_at(entry)
    print_blocks(
        found.graphs[entry],
        found.loops_of[entry],
        annotations.labels if annotations is not None else None,
    )


def show_callers(entry: int | str) -> None:
    """Every place that leaps into the routine starting at entry, an
    address or a label: one line per call site, in address order, with
    its leap (JSR, JMP, JMP ()), how often it was taken, and the routines
    whose blocks hold the site, with the dossier's labels.

    JMPs count as callers for now: a JMP into a routine's entry may be a
    tail call, which only a shadow stack can tell apart. A site can lie in
    several routines, where code is shared, so all of them are listed."""
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


def listing(start: int | str, end: int | str | None = None) -> None:
    """dis() of the current run's memory from start up to, not including,
    end, with the arrows of the whole run and the dossier's labels and
    comments. start and end are addresses or labels.

    With start alone, start is a routine's entry, and the whole routine is
    listed: from its lowest block to its highest, so any gap between its
    blocks shows too, e.g. code the run never reached."""
    found = current_routines()
    if end is None:
        blocks = found.graphs[routine_at(start)].blocks.values()
        start = min(block.start for block in blocks)
        end = max(block.end for block in blocks)
    else:
        start = address_of(start)
        end = address_of(end)
    dis(
        run_emulator,
        start,
        end,
        annotations.labels if annotations is not None else None,
        run_graph,
        annotations.comments if annotations is not None else None,
    )


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


def dis(
    emulator: Emulator,
    start: int,
    end: int,
    labels: dict[int, str] | None = None,
    graph: BlockGraph | None = None,
    comments: dict[int, str] | None = None,
) -> None:
    """Print the instructions from start up to, not including, end: address,
    bytes, instruction. Read from the emulator's memory as it is now, i.e.
    after the run, past anything that watches the CPU.

    With labels, an operand whose address has a name shows the name
    (JSR SUB instead of JSR $6010). An instruction whose own
    address has a name shows it in a column of its own, before the
    instruction. The column is as wide as the longest name in the range,
    and left out if no address in the range has a name.

    With comments, an instruction whose own address has a comment shows
    it behind the instruction, after "; ". The comments line up two spaces
    after the widest commented instruction in the range, so .byte lines
    don't push them out; lines without a comment end with their
    instruction.

    With graph, the jumps the run took are drawn as arrows in a gutter on
    the left: every edge whose target is not simply the next instruction
    (taken branches, JMPs). Glides, fall-throughs and calls are not drawn.
    An arrow is drawn only if both of its ends lie in the range.

    An instruction that starts before end is printed whole, even if its
    operand reaches past end. A block's end always lies behind its last
    instruction, so this only shows for ranges that cut an instruction.
    """
    disassembler = Disassembler(emulator.cpu, labels, comments)
    # disassemble() takes an inclusive end.
    rows = disassembler.disassemble(start, end - 1)
    width = max((len(row[2]) for row in rows), default=0)
    instructions = [f"{row[3]} {row[4]}".rstrip() for row in rows]
    instruction_width = max(
        (len(text) for row, text in zip(rows, instructions) if row[5]), default=0
    )
    gutter = draw_gutter(len(rows), *arrows_in(rows, graph))
    for row, prefix, instruction in zip(rows, gutter, instructions):
        row_address, row_bytes, label, _mnemonic, _operand, comment = row
        if not row_address:  # the empty line before a .byte block
            print(prefix.rstrip())
            continue
        name_column = f"{label:<{width}}  " if width else ""
        if comment:
            instruction = f"{instruction:<{instruction_width}}  ; {comment}"
        print(
            f"{prefix}{row_address.removeprefix('$'):<4}  {row_bytes:<8}  "
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
