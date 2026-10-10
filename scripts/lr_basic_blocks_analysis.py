"""Find every routine of Lode Runner's attract play, for the IPython prompt.

Boots Lode Runner headless, attaches the tiling instrumentation
(papple2.workbench.tiling) and the stack tracking
(papple2.workbench.stack_tracking), runs the attract play, and writes
their reports into docs/reports/lr_basic_blocks_analysis/, under git:
    lr_unbroken_tiles.csv
    lr_unbroken_transitions.csv
    lr_measurements.txt
    lr_split_tiles.csv
    lr_split_transitions.csv
    lr_returns.csv
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

or in IPython, which keeps the commands of papple2.workbench.shell in its
namespace afterwards. The run is the shell's current run: its machine,
instrumentations, routines and run graph are kept in shell.session, as
run_emulator, run_instrumentations, routines and run_graph. Lode
Runner's dossier (dossiers/lode_runner/, under git) is the current
dossier: label(), comment(), unlabel() and uncomment() change its
annotations at once, and listing() shows a range with the whole run's
arrows and the dossier's labels and comments:

    %run scripts/lr_basic_blocks_analysis.py
    show_routines()
    show_blocks(0x6238)
    listing(0x6238, 0x62c4)
    loop_reports(0x6238)
    comment(0x627e, "two 4-bit values per byte")
    label(0x6238, "LOAD_LEVEL")

use_dossier() starts a new dossier with the Apple II's standard labels;
after that, it leaves its labels alone.

show_routines() lists every routine of the run; show_blocks(entry) shows
the blocks of one of them. Both show labels. loop_reports(entry) writes
the loop reports of one more routine into the reports folder:
lr_loops_<entry>.csv and lr_loop_members_<entry>.csv.
"""

import argparse
from pathlib import Path

from papple2.programs import lode_runner
from papple2.workbench import shell  # noqa: F401
from papple2.workbench.stack_tracking import StackTracking
from papple2.workbench.tiling import Tiling

# Imported so that IPython's %run leaves them in its namespace, ready for
# looking at the run.
from papple2.workbench.shell import (  # noqa: F401
    color,
    colors,
    clip,
    comment,
    edit,
    hexdump,
    hide,
    label,
    listing,
    listing_rows,
    loop_reports,
    print_blocks,
    print_edges,
    print_listing,
    print_loops,
    print_routines,
    run,
    set_current_run,
    show_blocks,
    show_callers,
    show_routine_graph,
    show_routines,
    stack_tracking_reports,
    tiling_reports,
    to_range,
    uncolor,
    uncomment,
    unhide,
    unlabel,
    use_dossier,
    use_reports_folder,
)

# One folder per script, named after it. Under git: the reports are what
# the analysis leaves behind for reading, by us and by other LLMs.
REPORTS_FOLDER = Path("docs/reports/lr_basic_blocks_analysis")

# What we know about Lode Runner's addresses, kept across runs, under git.
DOSSIER = Path("dossiers/lode_runner")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "binary",
        nargs="?",
        default=lode_runner.DEFAULT_BINARY,
        help=f"path to LODE_RUNNER.BIN (default: {lode_runner.DEFAULT_BINARY})",
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
    # The recipe: the same lines could be typed at the prompt.
    arguments = parse_arguments()
    use_reports_folder(REPORTS_FOLDER)
    use_dossier(DOSSIER)
    run(
        lode_runner,
        arguments.instructions,
        Tiling,
        StackTracking,
        binary=arguments.binary,
    )
    tiling_reports()
    stack_tracking_reports()

    # The loop reports the run leaves behind: those of the start, and of
    # every routine named with --loop-reports, each written once.
    for entry in dict.fromkeys([lode_runner.LOAD_ADDRESS, *arguments.loop_reports]):
        loop_reports(entry)
