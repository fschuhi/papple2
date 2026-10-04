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

or in IPython, which keeps the run's objects (emulator, tiling) in its
namespace afterwards, together with the commands of papple2.workbench.shell.
The run is the shell's current run, its routines and run graph kept as
shell.routines and shell.run_graph. Lode Runner's dossier
(dossiers/lode_runner/, under git) is the current dossier: label(),
comment(), unlabel() and uncomment() change its annotations at once, and
listing() shows a range with the whole run's arrows and the dossier's
labels and comments:

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
import time
from pathlib import Path

from papple2.core.emulator import Emulator
from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.programs.lode_runner import LOAD_ADDRESS, boot
from papple2.workbench.tiling import Tiling

from papple2.workbench import shell  # noqa: F401

# Imported so that IPython's %run leaves them in its namespace, ready for
# looking at the run.
from papple2.workbench.shell import (  # noqa: F401
    comment,
    dis,
    label,
    listing,
    loop_reports,
    print_blocks,
    print_edges,
    print_loops,
    print_routines,
    set_current_run,
    show_blocks,
    show_routines,
    uncomment,
    unlabel,
    use_dossier,
    use_reports_folder,
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

    use_reports_folder(REPORTS_FOLDER)
    use_dossier(DOSSIER)
    # The analysis reads the reports back from the folder: the files are
    # the only connection, as in the walkthrough.
    set_current_run(
        emulator,
        LOAD_ADDRESS,
        split_tiles=REPORTS_FOLDER / "lr_split_tiles.csv",
        split_transitions=REPORTS_FOLDER / "lr_split_transitions.csv",
    )

    # The loop reports the run leaves behind: those of the start, and of
    # every routine named with --loop-reports, each written once.
    for entry in dict.fromkeys([LOAD_ADDRESS, *arguments.loop_reports]):
        loop_reports(entry)
