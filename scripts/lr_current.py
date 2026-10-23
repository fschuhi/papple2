"""Lode Runner's current run at the IPython prompt, from the committed reports.

Boots Lode Runner headless and runs the attract play without
instrumentations, only to have the memory as the run left it: listing(),
edit(), hexdump() and show_xrefs() read it. Then it makes that run the
current one, built from the reports the experiments committed:
    docs/reports/lr_basic_blocks_analysis/
        lr_split_tiles.csv
        lr_split_transitions.csv
        lr_returns.csv
    docs/reports/lr_cross_reference/
        lr_xrefs.csv
So the routines, edit() and show_xrefs() all work in one session.

It writes the overview of the run, with the dossier's labels as they are
now (papple2.workbench.overview), into docs/reports/lr_current/:
    lr_overview.txt
    lr_routines.csv
    lr_listing.tsv

The reports must come from a run of the same length: RUN_INSTRUCTIONS
here, --instructions there. The run without instrumentations is a
stand-in for a snapshot of the memory.

Run from the repo root:

    make lr-current

which starts IPython with this script, or in IPython:

    %run scripts/lr_current.py
    show_routines()
    edit("hx_to_byte_shift")
    show_xrefs("tbl_hx_byte")
"""

from pathlib import Path

from papple2.programs import lode_runner
from papple2.workbench import shell  # noqa: F401
from papple2.workbench.cross_referencing import XREFS_FILE
from papple2.workbench.stack_tracking import RETURNS_FILE
from papple2.workbench.tiling import SPLIT_TILES_FILE, SPLIT_TRANSITIONS_FILE

# Imported so that IPython's %run leaves them in its namespace, ready for
# looking at the run.
from papple2.workbench.shell import (  # noqa: F401
    clip,
    color,
    colors,
    comment,
    edit,
    hexdump,
    hide,
    hx,
    label,
    listing,
    listing_rows,
    memory_map,
    overview_reports,
    print_blocks,
    print_edges,
    print_listing,
    print_loops,
    print_routines,
    run,
    set_current_run,
    show_blocks,
    show_routine_graph,
    show_routines,
    show_ways_in,
    show_xrefs,
    to_range,
    uncolor,
    uncomment,
    unhide,
    unlabel,
    use_dossier,
    use_reports_folder,
)

# Where the reports come from, under git.
BASIC_BLOCKS_REPORTS = Path("docs/reports/lr_basic_blocks_analysis")
CROSS_REFERENCE_REPORTS = Path("docs/reports/lr_cross_reference")

# Where this script writes: only what it derives, with today's labels.
REPORTS_FOLDER = Path("docs/reports/lr_current")

# What we know about Lode Runner's addresses, kept across runs, under git.
DOSSIER = Path("dossiers/lode_runner")

# The length of the run the reports came from: the default of
# lr_basic_blocks_analysis.py and lr_cross_reference.py.
RUN_INSTRUCTIONS = 4_000_000


if __name__ == "__main__":
    # The recipe: the same lines could be typed at the prompt.
    use_reports_folder(REPORTS_FOLDER)
    use_dossier(DOSSIER)
    emulator = lode_runner.boot()
    run(emulator, RUN_INSTRUCTIONS)
    set_current_run(
        emulator,
        lode_runner.LOAD_ADDRESS,
        split_tiles=BASIC_BLOCKS_REPORTS / SPLIT_TILES_FILE,
        split_transitions=BASIC_BLOCKS_REPORTS / SPLIT_TRANSITIONS_FILE,
        returns=BASIC_BLOCKS_REPORTS / RETURNS_FILE,
        xrefs=CROSS_REFERENCE_REPORTS / XREFS_FILE,
    )
    overview_reports()
