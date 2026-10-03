"""Find the basic blocks and loops of one routine of Lode Runner.

Boots Lode Runner headless, attaches the tiling instrumentation
(papple2.workbench.tiling), runs the attract play, and has the basic
blocks analysis (papple2.workbench.basic_blocks_analysis) build the graph
from --entry (default 6238, LOAD_LEVEL). Writes into
tmp/lr_basic_blocks_analysis/:
    lr_unbroken_tiles.csv
    lr_unbroken_transitions.csv
    lr_measurements.txt
    lr_split_tiles.csv
    lr_split_transitions.csv
    lr_loops.csv
    lr_loop_members.csv

Run from the repo root:

    make lr-basic-blocks-analysis

or in IPython, which keeps the run's objects (emulator, tiling, graph,
loops) in its namespace afterwards, together with dis() and the show_*
functions (papple2.workbench.shell). There, Lode Runner's dossier
(dossiers/lode_runner/annotations.json, under git) is open as
annotations: label(), comment(), unlabel() and uncomment() write to it
at once, and listing() shows a range with this run's arrows and the
dossier's labels and comments:

    %run scripts/lr_basic_blocks_analysis.py
    show_routines()
    show_blocks(0x6238)
    listing(0x6238, 0x62c4)
    comment(0x627e, "two 4-bit values per byte")
    label(0x6238, "LOAD_LEVEL")

The dossier's first run starts it with the Apple II's standard labels;
after that, the script leaves its labels alone.

show_routines() lists every routine of the run, found as
scripts/lr_overview.py finds them (the run's start and every JSR target);
show_blocks(entry) shows the blocks of one of them. Both show labels.
graph and loops stay those of --entry, and so do listing()'s arrows.
"""

import argparse
import sys
import time
from pathlib import Path

# Python puts the folder of a started script on its search path, so the
# sibling boot script can be imported. IPython's %run may not, so the
# folder is added here as well.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from boot_lode_runner import LOAD_ADDRESS, boot  # noqa: E402
from lr_overview import find_entries  # noqa: E402
from papple2.core.cpu import JSR  # noqa: E402
from papple2.core.emulator import Emulator  # noqa: E402
from papple2.debug.disassembler import STANDARD_LABELS  # noqa: E402
from papple2.debug.stop_conditions import instruction_count_reaches  # noqa: E402
from papple2.workbench.annotations import Annotations  # noqa: E402
from papple2.workbench.basic_blocks_analysis import (  # noqa: E402
    BlockGraph,
    Loop,
    build_graph,
    immediate_dominators,
    natural_loops,
    read_split_reports,
    write_loop_reports,
)
from papple2.workbench.tiling import Tiling, address  # noqa: E402

from papple2.workbench import shell  # noqa: E402

# Apart from dis(), which listing() uses: imported so that IPython's %run
# leaves them in its namespace, ready for looking at the run. show_blocks
# and show_routines are defined below, for the routines of this run.
from papple2.workbench.shell import (  # noqa: E402, F401
    dis,
    show_edges,
    show_loops,
)

# One folder per script, named after it.
REPORTS_FOLDER = Path("tmp/lr_basic_blocks_analysis")

# What we know about Lode Runner's addresses, kept across runs, under git.
DOSSIER = Path("dossiers/lode_runner")

# Relative to the repo root, where make and IPython are started.
DEFAULT_BINARY = "data/bin/LODE_RUNNER.BIN"

LOAD_LEVEL = 0x6238


def analyse(
    binary: str, instructions: int, entry: int, folder: Path
) -> tuple[Emulator, Tiling, BlockGraph, dict[int, Loop]]:
    """Run Lode Runner with Tiling attached for the given number of
    instructions, write the tiling reports into folder, then build the
    graph from entry and write the loop reports there too."""
    emulator, rwts = boot(binary, headless=True)
    tiling = Tiling(emulator.cpu)
    emulator.attach(tiling)

    start = time.perf_counter()
    try:
        emulator.run(until=instruction_count_reaches(instructions))
    finally:
        seconds = time.perf_counter() - start
        emulator.detach(tiling)
    print(f"{emulator.instructions:,} instructions in {seconds:.2f} s")

    # run() counts from 0, so emulator.instructions is what ran while the
    # tiling was attached.
    tiling.write_reports(folder, emulator.instructions, len(rwts.log))

    # The analysis reads the reports back from the folder: the files are
    # the only connection, as in the walkthrough.
    tiles, transitions = read_split_reports(folder)
    graph = build_graph(tiles, transitions, entry=entry)
    loops = natural_loops(graph, immediate_dominators(graph))
    write_loop_reports(folder, graph, loops)
    print(
        f"from {address(entry)}: {len(graph.blocks)} basic blocks, "
        f"{len(loops)} loops"
    )
    return emulator, tiling, graph, loops


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "binary",
        nargs="?",
        default=DEFAULT_BINARY,
        help=f"path to LODE_RUNNER.BIN (default: {DEFAULT_BINARY})",
    )
    parser.add_argument(
        "--instructions",
        type=int,
        default=4_000_000,
        help="stop after N instructions (default: 4000000)",
    )
    parser.add_argument(
        "--entry",
        type=lambda text: int(text, 16),
        default=LOAD_LEVEL,
        help="hex address the graph starts from (default: 6238, LOAD_LEVEL)",
    )
    arguments = parser.parse_args()
    if arguments.instructions <= 0:
        parser.error("--instructions must be positive")
    return arguments


if __name__ == "__main__":
    # At module level on purpose: IPython's %run keeps these names in its
    # namespace, so the run can be inspected afterwards.
    arguments = parse_arguments()
    emulator, tiling, graph, loops = analyse(
        arguments.binary, arguments.instructions, arguments.entry, REPORTS_FOLDER
    )

    annotations = Annotations(DOSSIER)
    if not annotations.path.exists():
        # The dossier's first run: start it with the Apple II's names.
        annotations.add_labels(STANDARD_LABELS)

    # Short names for the prompt.
    label = annotations.label
    comment = annotations.comment
    unlabel = annotations.unlabel
    uncomment = annotations.uncomment

    def listing(start: int, end: int) -> None:
        """dis() with this run's graph and the dossier's labels and
        comments."""
        dis(emulator, start, end, annotations.labels, graph, annotations.comments)

    # Every routine of the run, found as scripts/lr_overview.py finds them.
    tiles, transitions = read_split_reports(REPORTS_FOLDER)
    entries = find_entries(transitions)
    # How often each routine was called: the counts of the JSRs into it.
    calls_into = {entry: 0 for entry in entries}
    for row in transitions:
        if row.opcode == JSR:
            calls_into[row.target_tile] += row.count
    calls_into[LOAD_ADDRESS] += 1  # the run itself enters there once
    graphs = {}
    loops_of = {}
    for entry in entries:
        graphs[entry] = build_graph(tiles, transitions, entry)
        loops_of[entry] = natural_loops(
            graphs[entry], immediate_dominators(graphs[entry])
        )

    def show_routines() -> None:
        """Every routine of the run, with the dossier's labels."""
        shell.show_routines(graphs, loops_of, calls_into, annotations.labels)

    def show_blocks(entry: int) -> None:
        """The blocks of the routine starting at entry, with its loops and
        the dossier's labels."""
        if entry not in graphs:
            raise ValueError(
                f"{address(entry)} is not a routine; show_routines() lists them"
            )
        shell.show_blocks(graphs[entry], loops_of[entry], annotations.labels)
