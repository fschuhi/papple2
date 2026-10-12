"""Walk a tiny program through the workbench's pipeline.

Runs nested_loops (papple2.programs.nested_loops: two nested loops, one
JSR) with the tiling instrumentation attached, and writes seven reports
into tmp/walkthrough/:
    from Tiling (papple2.workbench.tiling):
        lr_unbroken_tiles.csv
        lr_unbroken_transitions.csv
        lr_measurements.txt
        lr_split_tiles.csv
        lr_split_transitions.csv
    from the basic blocks analysis (papple2.workbench.basic_blocks_analysis):
        lr_loops_6000.csv
        lr_loop_members_6000.csv

The program is small enough to follow by hand, so each report's rows can
be predicted before looking.

Run from the repo root:

    make walkthrough

or in IPython, which keeps the commands of papple2.workbench.shell in its
namespace afterwards, with the run as the current run:

    %run scripts/walkthrough.py
    show_routines()
    show_blocks(0x6000)
    listing(0x6000)
"""

from pathlib import Path

from papple2.programs import nested_loops
from papple2.workbench.shell import (  # noqa: F401
    listing,
    loop_reports,
    run,
    show_blocks,
    show_routines,
    tiling_reports,
    use_reports_folder,
)
from papple2.workbench.tiling import Tiling

# One folder per script, named after it.
REPORTS_FOLDER = Path("tmp/walkthrough")


if __name__ == "__main__":
    # The recipe: the same lines could be typed at the prompt. 39
    # instructions run the program to its end, done's NOP included.
    use_reports_folder(REPORTS_FOLDER)
    run(nested_loops.boot(), 39, Tiling)
    tiling_reports()
    loop_reports(nested_loops.LOAD_ADDRESS)
