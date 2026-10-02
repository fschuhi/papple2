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
functions (papple2.workbench.shell):

    %run scripts/lr_basic_blocks_analysis.py
    show_loops(loops)
    dis(emulator, 0x6238, 0x62c4, graph=graph)
"""

import argparse
import sys
import time
from pathlib import Path

# Python puts the folder of a started script on its search path, so the
# sibling boot script can be imported. IPython's %run may not, so the
# folder is added here as well.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from boot_lode_runner import boot  # noqa: E402
from papple2.core.emulator import Emulator  # noqa: E402
from papple2.debug.stop_conditions import instruction_count_reaches  # noqa: E402
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

# Not used here: imported so that IPython's %run leaves them in its
# namespace, ready for looking at the run.
from papple2.workbench.shell import (  # noqa: E402, F401
    dis,
    show_blocks,
    show_edges,
    show_loops,
)

# One folder per script, named after it.
REPORTS_FOLDER = Path("tmp/lr_basic_blocks_analysis")

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
