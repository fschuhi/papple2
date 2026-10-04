"""Print an overview of the whole run: routines, their loops, their calls.

A recipe that works from reports alone, with no emulator run. It reads
three reports of the tiling, each by its full path, from
docs/reports/lr_tiles/ (written by `make lr-tiles`), prints the overview,
and writes it into its reports folder, docs/reports/lr_overview/, as
lr_overview.txt, so it can be kept and diffed. A routine is the code
reachable from an entry without following calls: the run's start, or the
target of any JSR that ran. Each routine is analysed on its own, with the
basic blocks analysis.

overview() is local to this recipe: it can be called at the prompt after
%run, with other report files, but it is no contract of the workbench yet.

Run from the repo root:

    .venv/bin/python scripts/lr_overview.py
"""

import io
from pathlib import Path

# Python puts the folder of the started script on its search path,
# so the sibling boot script can be imported directly.
from boot_lode_runner import LOAD_ADDRESS
from papple2.core.cpu import JSR
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    SplitTile,
    find_routines,
    read_split_tiles,
    read_split_transitions,
)
from papple2.workbench.shell import use_reports_folder, write_report
from papple2.workbench.tiling import address

# The file the overview is saved as, in the reports folder.
OVERVIEW_FILE = "lr_overview.txt"


def observed_instructions(measurements: Path) -> str:
    """The instruction count, as the tiling's measurements state it."""
    if measurements.exists():
        for line in measurements.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("Observed instructions:"):
                return line.split(":", 1)[1].strip()
    return "?"


def print_loop_tree(
        loops: dict[int, Loop],
        graph: BlockGraph,
        parent: int | None,
        indent: int,
        out: io.StringIO,
) -> None:
    """Print the loops whose enclosing loop is parent, each followed by its
    own inner loops, one step further indented."""
    for header, loop in loops.items():
        if loop.parent == parent:
            runs = graph.blocks[header].executions
            print(f"{'  ' * indent}loop {address(header)}  {runs:>9,}x", file=out)
            print_loop_tree(loops, graph, header, indent + 1, out)


def overview(
        start: int,
        split_tiles: Path,
        split_transitions: Path,
        measurements: Path,
        save: bool = False,
) -> None:
    """Print the overview of a whole run: totals, routines, pieces in no
    routine, loops per routine. Reads the three tiling reports by their
    full paths. start is where the run began, which no report records.
    With save, also writes the overview into the reports folder."""
    tiles = read_split_tiles(split_tiles)
    transitions = read_split_transitions(split_transitions)
    routines = find_routines(tiles, transitions, start)
    graphs = routines.graphs
    loops_of = routines.loops_of
    calls_into = routines.calls_into
    entries = list(graphs)

    all_loops = {header: loop for loops in loops_of.values() for header, loop in loops.items()}
    covered = {start for graph in graphs.values() for start in graph.blocks}
    uncovered: list[SplitTile] = [tile for tile in tiles if tile.start not in covered]

    # Collect the overview in a buffer, so it can be printed and written alike.
    out = io.StringIO()
    print("WHOLE RUN", file=out)
    print(f"  {observed_instructions(measurements)} instructions", file=out)
    print(f"  {len(tiles):,} pieces of code, {sum(t.end - t.start for t in tiles):,} bytes", file=out)
    print(f"  {len(entries)} routines", file=out)
    deepest = max((loop.depth for loop in all_loops.values()), default=-1) + 1
    print(f"  {len(all_loops)} loops, at most {deepest} inside each other", file=out)
    print(file=out)

    print("ROUTINES (in address order)", file=out)
    print(f"  {'routine':<8}{'pieces':>7}{'bytes':>7}{'called':>11}{'loops':>7}  calls", file=out)
    for entry in entries:
        graph = graphs[entry]
        size = sum(block.end - block.start for block in graph.blocks.values())
        callees = sorted(
            {
                row.target_tile
                for row in transitions
                if row.opcode == JSR and row.source_tile in graph.blocks
            }
        )
        print(
            f"  {address(entry):<8}{len(graph.blocks):>7}{size:>7}"
            f"{calls_into[entry]:>11,}{len(loops_of[entry]):>7}  "
            + " ".join(address(callee) for callee in callees),
            file=out,
        )
    print(file=out)

    print(f"PIECES IN NO ROUTINE: {len(uncovered)}", file=out)
    starts = [address(tile.start) for tile in uncovered]
    for position in range(0, len(starts), 12):
        print("  " + " ".join(starts[position:position + 12]), file=out)
    print(file=out)

    print("LOOPS PER ROUTINE (runs = how often the loop's first piece ran)", file=out)
    for entry in entries:
        if loops_of[entry]:
            print(f"  routine {address(entry)}", file=out)
            print_loop_tree(loops_of[entry], graphs[entry], parent=None, indent=2, out=out)

    text = out.getvalue()
    print(text, end="")
    if save:
        write_report(OVERVIEW_FILE, text)


if __name__ == "__main__":
    # The recipe: the same lines could be typed at the prompt.
    use_reports_folder(Path("docs/reports/lr_overview"))
    overview(
        LOAD_ADDRESS,
        split_tiles=Path("docs/reports/lr_tiles/lr_split_tiles.csv"),
        split_transitions=Path("docs/reports/lr_tiles/lr_split_transitions.csv"),
        measurements=Path("docs/reports/lr_tiles/lr_measurements.txt"),
        save=True,
    )
