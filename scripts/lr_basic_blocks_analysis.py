"""Find every routine of Lode Runner's attract play, for the IPython prompt.

Boots Lode Runner headless, attaches the tiling instrumentation
(papple2.workbench.tiling), runs the attract play, and writes the tiling
reports into docs/reports/lr_basic_blocks_analysis/, under git:
    lr_unbroken_tiles.csv
    lr_unbroken_transitions.csv
    lr_measurements.txt
    lr_split_tiles.csv
    lr_split_transitions.csv
Then the basic blocks analysis (papple2.workbench.basic_blocks_analysis)
finds every routine of the run: the run's start and every JSR target.
It writes the loop reports of the start, $0800, into the same folder:
    lr_loops_0800.csv
    lr_loop_members_0800.csv
--loop-reports adds the pair for each routine named, e.g.
--loop-reports 6238 for LOAD_LEVEL. Calls are not followed, so each pair
shows the loops of its routine only, not of the routines it calls.

Run from the repo root:

    make lr-basic-blocks-analysis

or in IPython, which keeps the run's objects (emulator, tiling, routines,
run_graph) in its namespace afterwards, together with dis() and the show_*
functions (papple2.workbench.shell). There, Lode Runner's dossier
(dossiers/lode_runner/annotations.json, under git) is open as
annotations: label(), comment(), unlabel() and uncomment() write to it
at once, and listing() shows a range with the whole run's arrows and the
dossier's labels and comments:

    %run scripts/lr_basic_blocks_analysis.py
    show_routines()
    show_blocks(0x6238)
    listing(0x6238, 0x62c4)
    loop_reports(0x6238)
    comment(0x627e, "two 4-bit values per byte")
    label(0x6238, "LOAD_LEVEL")

The dossier's first run starts it with the Apple II's standard labels;
after that, the script leaves its labels alone.

show_routines() lists every routine of the run; show_blocks(entry) shows
the blocks of one of them. Both show labels. loop_reports(entry) writes
the loop reports of one more routine into the same folder:
lr_loops_<entry>.csv and lr_loop_members_<entry>.csv.
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
from papple2.core.emulator import Emulator  # noqa: E402
from papple2.debug.disassembler import STANDARD_LABELS  # noqa: E402
from papple2.debug.stop_conditions import instruction_count_reaches  # noqa: E402
from papple2.workbench.annotations import Annotations  # noqa: E402
from papple2.workbench.basic_blocks_analysis import (  # noqa: E402
    build_run_graph,
    find_routines,
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

# One folder per script, named after it. Under git: the reports are what
# the analysis leaves behind for reading, by us and by other LLMs.
REPORTS_FOLDER = Path("docs/reports/lr_basic_blocks_analysis")

# What we know about Lode Runner's addresses, kept across runs, under git.
DOSSIER = Path("dossiers/lode_runner")

# Relative to the repo root, where make and IPython are started.
DEFAULT_BINARY = "data/bin/LODE_RUNNER.BIN"


def analyse(
    binary: str, instructions: int, folder: Path
) -> tuple[Emulator, Tiling]:
    """Run Lode Runner with Tiling attached for the given number of
    instructions, and write the tiling reports into folder."""
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
    return emulator, tiling


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
        "--loop-reports",
        nargs="*",
        type=lambda text: int(text, 16),
        default=[],
        metavar="ENTRY",
        help="hex entries of further routines to write loop reports for "
        "(those of the start, 0800, are always written)",
    )
    arguments = parser.parse_args()
    if arguments.instructions <= 0:
        parser.error("--instructions must be positive")
    return arguments


if __name__ == "__main__":
    # At module level on purpose: IPython's %run keeps these names in its
    # namespace, so the run can be inspected afterwards.
    arguments = parse_arguments()
    emulator, tiling = analyse(
        arguments.binary, arguments.instructions, REPORTS_FOLDER
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
        """dis() with the arrows of the whole run and the dossier's labels
        and comments."""
        dis(emulator, start, end, annotations.labels, run_graph, annotations.comments)

    # Every routine of the run. The analysis reads the reports back from
    # the folder: the files are the only connection, as in the walkthrough.
    tiles, transitions = read_split_reports(REPORTS_FOLDER)
    routines = find_routines(tiles, transitions, LOAD_ADDRESS)
    print(f"{len(routines.graphs)} routines")
    # Every block and edge of the run, for listing()'s arrows.
    run_graph = build_run_graph(tiles, transitions, LOAD_ADDRESS)

    def show_routines() -> None:
        """Every routine of the run, with the dossier's labels."""
        shell.show_routines(
            routines.graphs,
            routines.loops_of,
            routines.calls_into,
            annotations.labels,
        )

    def show_blocks(entry: int) -> None:
        """The blocks of the routine starting at entry, with its loops and
        the dossier's labels."""
        if entry not in routines.graphs:
            raise ValueError(
                f"{address(entry)} is not a routine; show_routines() lists them"
            )
        shell.show_blocks(
            routines.graphs[entry], routines.loops_of[entry], annotations.labels
        )

    def loop_reports(entry: int) -> None:
        """Write the loop reports of the routine starting at entry into
        the reports folder, with the entry in their names."""
        if entry not in routines.graphs:
            raise ValueError(
                f"{address(entry)} is not a routine; show_routines() lists them"
            )
        write_loop_reports(
            REPORTS_FOLDER, routines.graphs[entry], routines.loops_of[entry]
        )

    # The loop reports the run leaves behind: those of the start, and of
    # every routine named with --loop-reports, each written once.
    for entry in dict.fromkeys([LOAD_ADDRESS, *arguments.loop_reports]):
        loop_reports(entry)
