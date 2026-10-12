"""Run one of the walkthrough's programs through the workbench's pipeline.

The walkthrough is the book of chapters in tests/test_walkthrough.py; this
script is its chapter 0. It runs a program's recipe and writes the
reports into tmp/walkthrough/<program>/. For nested_loops
(papple2.programs.nested_loops: two nested loops, one JSR), seven reports:
    from Tiling (papple2.workbench.tiling):
        lr_unbroken_tiles.csv
        lr_unbroken_transitions.csv
        lr_measurements.txt
        lr_split_tiles.csv
        lr_split_transitions.csv
    from the basic blocks analysis (papple2.workbench.basic_blocks_analysis):
        lr_loops_6000.csv
        lr_loop_members_6000.csv
For rts_dispatch (papple2.programs.rts_dispatch: two commands called
through a jump table, with RTS), the five tiling reports, and from
StackTracking (papple2.workbench.stack_tracking):
        lr_returns.csv

The programs are small enough to follow by hand, so each report's rows
can be predicted before looking.

Run from the repo root:

    make walkthrough

or in IPython, which keeps the commands of papple2.workbench.shell in its
namespace afterwards, with the run as the current run, so you can read
the chapters along at the prompt:

    %run scripts/walkthrough.py nested_loops
    show_routines()
    show_blocks(0x6000)
    listing(0x6000)

and the same with rts_dispatch.
"""

import argparse
from pathlib import Path

from papple2.programs import nested_loops, rts_dispatch
from papple2.workbench.shell import (  # noqa: F401
    listing,
    loop_reports,
    run,
    show_blocks,
    show_routines,
    stack_tracking_reports,
    tiling_reports,
    use_reports_folder,
)
from papple2.workbench.stack_tracking import StackTracking
from papple2.workbench.tiling import Tiling

# One folder per script, named after it, and in it one per program.
REPORTS_FOLDER = Path("tmp/walkthrough")


def nested_loops_recipe() -> None:
    """The recipe: the same lines could be typed at the prompt. 39
    instructions run the program to its end, done's NOP included."""
    use_reports_folder(REPORTS_FOLDER / "nested_loops")
    run(nested_loops.boot(), 39, Tiling)
    tiling_reports()
    loop_reports(nested_loops.LOAD_ADDRESS)


def rts_dispatch_recipe() -> None:
    """The recipe: the same lines could be typed at the prompt. 24
    instructions run the program to its end, done's NOP included."""
    use_reports_folder(REPORTS_FOLDER / "rts_dispatch")
    run(rts_dispatch.boot(), 24, Tiling, StackTracking)
    tiling_reports()
    stack_tracking_reports()


# Each program of the walkthrough, and its recipe.
RECIPES = {
    "nested_loops": nested_loops_recipe,
    "rts_dispatch": rts_dispatch_recipe,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("program", choices=RECIPES)
    RECIPES[parser.parse_args().program]()
