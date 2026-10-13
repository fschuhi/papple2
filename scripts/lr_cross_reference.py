"""Count every access to memory in Lode Runner's attract play.

Every access is counted by the instruction that made it. Boots Lode Runner headless, attaches the cross referencing
(papple2.workbench.cross_referencing), runs the attract play, and writes
its report into docs/reports/lr_cross_reference/:
    lr_xrefs.csv
one row per instruction, kind of access, target and effective address,
with how often, and the indexes, values and old values seen.

Then xref_summary() reads the report back and prints what it holds: rows
and accesses per kind, how many instructions touched memory, and how many
rows land on the hi-res screen pages, where a drawing routine's
STA (ptr),Y touches thousands of different bytes.

Run from the repo root:

    make lr-cross-reference

or in IPython, which keeps the commands of papple2.workbench.shell in its
namespace afterwards, with the run as the current run:

    %run scripts/lr_cross_reference.py
    xref_summary(REPORTS_FOLDER / XREFS_FILE)

Only CrossReferencing is attached, so the time the run takes is its own.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from papple2.programs import lode_runner
from papple2.workbench import shell  # noqa: F401
from papple2.workbench.cross_referencing import KIND_ORDER, XREFS_FILE, CrossReferencing

# Imported so that IPython's %run leaves them in its namespace, ready for
# looking at the run.
from papple2.workbench.shell import (  # noqa: F401
    clip,
    cross_referencing_reports,
    hexdump,
    hx,
    run,
    use_reports_folder,
)

# One folder per script, named after it. Under git: the reports are what
# the analysis leaves behind for reading, by us and by other LLMs.
REPORTS_FOLDER = Path("docs/reports/lr_cross_reference")

# The hi-res screen pages, half-open, as everywhere in the workbench.
HGR_PAGES = {
    "HGR page 1": (0x2000, 0x4000),
    "HGR page 2": (0x4000, 0x6000),
}


def xref_summary(path: Path) -> None:
    """Print what a cross reference report holds: its size, its rows and
    accesses per kind, the instructions that touched memory, and the rows
    on each hi-res page."""
    rows = Counter()
    accesses = Counter()
    instructions = set()
    on_page = Counter()
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            kind = row["kind"]
            rows[kind] += 1
            accesses[kind] += int(row["count"])
            instructions.add(row["instruction"])
            effective_address = int(row["effective_address"], 16)
            for page, (start, end) in HGR_PAGES.items():
                if start <= effective_address < end:
                    on_page[page] += 1

    total = sum(rows.values())
    print(f"{path}: {path.stat().st_size / 1024:,.0f} KB, {total:,} rows")
    print(f"{len(instructions):,} instructions touched memory")
    print()
    print("kind                rows      accesses")
    for kind in KIND_ORDER:
        print(f"{kind:<14}  {rows[kind]:>8,}  {accesses[kind]:>12,}")
    print()
    for page in HGR_PAGES:
        share = on_page[page] / total if total else 0
        print(f"{page}: {on_page[page]:,} rows ({share:.0%})")


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
    arguments = parser.parse_args()
    if arguments.instructions <= 0:
        parser.error("--instructions must be positive")
    return arguments


if __name__ == "__main__":
    # The recipe: the same lines could be typed at the prompt.
    arguments = parse_arguments()
    use_reports_folder(REPORTS_FOLDER)
    run(lode_runner.boot(arguments.binary), arguments.instructions, CrossReferencing)
    cross_referencing_reports()

    xref_summary(REPORTS_FOLDER / XREFS_FILE)
