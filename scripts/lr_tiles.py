"""Collect Lode Runner's tiles and measure their observed structure.

Boots Lode Runner headless, attaches the tiling instrumentation
(`papple2.workbench.tiling`), runs the attract play, prints a summary,
and has the instrumentation check its accounting and write its reports
into tmp/lr_tiles/:
    lr_unbroken_tiles.csv
    lr_unbroken_transitions.csv
    lr_measurements.txt
    lr_split_tiles.csv
    lr_split_transitions.csv

Run from the repo root:

    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN
    .venv/bin/python scripts/lr_tiles.py data/bin/LODE_RUNNER.BIN --instructions 1000000
"""

import argparse
import time
from pathlib import Path

# Python puts the folder of the started script on its search path,
# so the sibling boot script can be imported directly.
from boot_lode_runner import boot
from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.workbench.tiling import Tiling, address, report_findings

# One folder per script, named after it (briefing.md, section 2).
REPORTS_FOLDER = Path("tmp/lr_tiles")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to LODE_RUNNER.BIN")
    parser.add_argument(
        "--instructions",
        type=int,
        default=4_000_000,
        help="stop after N instructions (default: 4000000)",
    )
    args = parser.parse_args()
    if args.instructions <= 0:
        parser.error("--instructions must be positive")

    emulator, rwts = boot(args.binary, headless=True)
    tiling = Tiling(emulator.cpu)
    emulator.attach(tiling)

    # Compare hook accounting with the emulator's instruction delta,
    # rather than assuming boot left its cumulative counter at zero.
    instructions_before = emulator.instructions
    start = time.perf_counter()
    try:
        emulator.run(until=instruction_count_reaches(args.instructions))
    finally:
        seconds = time.perf_counter() - start
        emulator.detach(tiling)

    instructions_executed = emulator.instructions - instructions_before
    first_tile = next(
        tile for tile in tiling.tiles.values() if tile.initial_entries
    )
    print(
        f"run started in tile {address(first_tile.start_pc)}, "
        f"stopped in tile {address(tiling.current_tile.start_pc)}"
    )
    report_findings(tiling)

    print(f"{instructions_executed:,} instructions in {seconds:.2f} s")
    print(f"RWTS reads served: {len(rwts.log)}")
    print(
        f"transitions traversed: {sum(tiling.transitions.values()):,}"
    )

    tiling.write_reports(REPORTS_FOLDER, instructions_executed, len(rwts.log))


if __name__ == "__main__":
    main()
