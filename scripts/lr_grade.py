"""Grade the routines of Lode Runner's attract play against the answer key.

The answer key, docs/lr_answer_key.csv, gives every block of the run the
unit of Xekri's source it lies in: a Xekri subroutine, or an unmarked unit
(docs/lr_structures.md, "The answer key"). A unit agrees if one routine
holds exactly its blocks, no more and no fewer.

There is no run here: the routines are built from the committed reports of
lr_basic_blocks_analysis (the two split reports and lr_returns.csv) by
Session.set_current_run(), the same code that builds them after a run.
Before grading, the script checks that it got the routines listed in
lr_routines.csv, which the same run wrote; if not, it stops.

Blocks the key gives no unit (marked "-", the loader jump at 0800) are not
graded; they are listed apart, with the routine that holds them.

Run from the repo root:

    make lr-grade

or in IPython:

    %run scripts/lr_grade.py
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from papple2.programs import lode_runner
from papple2.workbench.annotations import Annotations
from papple2.workbench.basic_blocks_analysis import Routines
from papple2.workbench.overview import ROUTINES_FILE
from papple2.workbench.session import Session
from papple2.workbench.stack_tracking import RETURNS_FILE
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    address,
)

# The reports the routines are built from, and the key they are graded by.
REPORTS_FOLDER = Path("docs/reports/lr_basic_blocks_analysis")
ANSWER_KEY = Path("docs/lr_answer_key.csv")

# Only read, for the routines' labels; nothing is written to it.
DOSSIER = Path("dossiers/lode_runner")

# The answer key's mark for a block that lies in no unit.
NO_UNIT = "-"


@dataclass(frozen=True)
class AnswerKeyRow:
    """One row of lr_answer_key.csv: a block of the run, and the unit it
    lies in. A block in no unit has NO_UNIT as its unit and no unit_start."""

    block_start: int
    block_end: int  # exclusive
    executions: int
    unit: str
    unit_start: int | None
    note: str


def read_answer_key(filename: Path) -> list[AnswerKeyRow]:
    """Read an answer key (lr_answer_key.csv) by its full path."""
    with filename.open(newline="", encoding="utf-8") as key_file:
        rows = [
            AnswerKeyRow(
                block_start=int(row["block_start"], 16),
                block_end=int(row["block_end"], 16),
                executions=int(row["executions"]),
                unit=row["xekri_subroutine"],
                unit_start=(
                    None
                    if row["xekri_start"] == NO_UNIT
                    else int(row["xekri_start"], 16)
                ),
                note=row["note"],
            )
            for row in csv.DictReader(key_file)
        ]
    return rows


def routines_from_reports(folder: Path) -> Routines:
    """The routines of the run whose reports lie in folder, built as
    tiling_reports() and stack_tracking_reports() build them after a run."""
    session = Session()
    # No emulator: set_current_run() only keeps it, for the listings. And
    # no dossier is open in this Session, so it gives no routine a label:
    # the dossier stays as it is.
    session.set_current_run(
        None,
        lode_runner.LOAD_ADDRESS,
        folder / SPLIT_TILES_FILE,
        folder / SPLIT_TRANSITIONS_FILE,
        returns=folder / RETURNS_FILE,
    )
    return session.current_routines()


def check_routines(routines: Routines, filename: Path) -> None:
    """Stop unless routines has exactly the entries of filename, a routines
    report (lr_routines.csv) written by the same run."""
    with filename.open(newline="", encoding="utf-8") as routines_file:
        committed = {int(row["routine"], 16) for row in csv.DictReader(routines_file)}
    built = set(routines.graphs)
    if built != committed:
        only_built = " ".join(address(entry) for entry in sorted(built - committed))
        only_committed = " ".join(
            address(entry) for entry in sorted(committed - built)
        )
        raise RuntimeError(
            f"the routines built here are not those of {filename}: "
            f"only here: {only_built or '-'}; only there: {only_committed or '-'}"
        )


def print_grade(
    routines: Routines, key: list[AnswerKeyRow], labels: dict[int, str]
) -> None:
    """Print how the routines agree with the key: the counts, then each
    unit that disagrees with the routines holding its blocks, then the
    blocks in no unit."""
    # Which routines hold each block. Since 2026-10-18 there should be
    # exactly one per block, but the grade counts it rather than trusts it.
    holders_of: dict[int, list[int]] = defaultdict(list)
    for entry, graph in sorted(routines.graphs.items()):
        for block in graph.blocks:
            holders_of[block].append(entry)

    key_blocks = {row.block_start for row in key}
    stray = sorted(set(holders_of) - key_blocks)
    if stray:
        raise RuntimeError(
            "blocks of the routines that the answer key doesn't have: "
            + " ".join(address(block) for block in stray)
        )

    blocks_of_unit: dict[str, set[int]] = defaultdict(set)
    start_of_unit: dict[str, int] = {}
    no_unit = [row for row in key if row.unit == NO_UNIT]
    for row in key:
        if row.unit != NO_UNIT:
            blocks_of_unit[row.unit].add(row.block_start)
            start_of_unit[row.unit] = row.unit_start

    def holders(blocks: set[int]) -> list[int]:
        return sorted({entry for block in blocks for entry in holders_of.get(block, [])})

    def agrees(blocks: set[int]) -> bool:
        found = holders(blocks)
        return len(found) == 1 and set(routines.graphs[found[0]].blocks) == blocks

    def holders_text(blocks: set[int]) -> str:
        """Each routine holding some of blocks, with how many of them it
        holds, of how many blocks it has, e.g. 0800 routine_0800 (5 of 40)."""
        parts = []
        for entry in holders(blocks):
            own = routines.graphs[entry].blocks
            name = f"{address(entry)} {labels.get(entry, '')}".rstrip()
            parts.append(f"{name} ({len(blocks & own.keys())} of {len(own)})")
        lost = sum(1 for block in blocks if not holders_of.get(block))
        if lost:
            parts.append(f"no routine ({lost})")
        return ", ".join(parts)

    units = sorted(blocks_of_unit, key=lambda unit: (start_of_unit[unit], unit))
    disagreeing = [unit for unit in units if not agrees(blocks_of_unit[unit])]
    in_none = sum(1 for block in key_blocks if not holders_of.get(block))
    in_several = sum(1 for block in key_blocks if len(holders_of.get(block, [])) > 1)

    print("ROUTINES AGAINST THE ANSWER KEY")
    print(
        f"  answer key: {len(key)} blocks, {len(units)} units, "
        f"{len(no_unit)} block(s) in no unit"
    )
    print(f"  routines: {len(routines.graphs)}")
    print(f"  blocks in no routine: {in_none}")
    print(f"  blocks in more than one routine: {in_several}")
    print(f"  units that agree: {len(units) - len(disagreeing)} of {len(units)}")
    print()

    print("UNITS THAT DISAGREE (k of n: k of the unit's blocks, of the routine's n)")
    if not disagreeing:
        print("  none")
    else:
        width = max(len("unit"), *(len(unit) for unit in disagreeing))
        print(f"  {'unit':<{width}}  start  blocks  routines")
        for unit in disagreeing:
            blocks = blocks_of_unit[unit]
            print(
                f"  {unit:<{width}}  {address(start_of_unit[unit])}   "
                f"{len(blocks):>6}  {holders_text(blocks)}"
            )
    print()

    print("BLOCKS IN NO UNIT (not graded)")
    if not no_unit:
        print("  none")
    for row in no_unit:
        print(
            f"  {address(row.block_start)}-{address(row.block_end)}  "
            f"{holders_text({row.block_start})}"
        )


if __name__ == "__main__":
    grade_routines = routines_from_reports(REPORTS_FOLDER)
    check_routines(grade_routines, REPORTS_FOLDER / ROUTINES_FILE)
    print_grade(
        grade_routines, read_answer_key(ANSWER_KEY), Annotations(DOSSIER).labels
    )
