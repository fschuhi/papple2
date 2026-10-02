"""Tests for papple2.workbench.tiling.

The program is the one from scripts/walkthrough.py: two nested loops,
one JSR, and a JMP over the subroutine to DONE.
"""

import csv
from pathlib import Path

from papple2.debug.stop_conditions import at_address
from papple2.workbench.tiling import (
    MEASUREMENTS_FILE,
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    Tiling,
)

PROGRAM = """
        *=$6000
        LDY #$02
OUTER   LDX #$03
INNER   JSR SUB
        DEX
        BNE INNER
        DEY
        BNE OUTER
        JMP DONE
SUB     INC $10
        RTS
DONE    NOP
"""

DONE = 0x6013


def run_with_tiling(make_emulator, stop: int, folder: Path) -> Tiling:
    """Run PROGRAM until stop with Tiling attached, then write the reports."""
    _, emulator = make_emulator(PROGRAM)
    tiling = Tiling(emulator.cpu)
    emulator.attach(tiling)
    emulator.run(until=at_address(stop))
    emulator.detach(tiling)
    tiling.write_reports(folder, emulator.instructions, rwts_reads=0)
    return tiling


def read_rows(filename: Path) -> list[dict[str, str]]:
    with filename.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_run_stopped_right_after_a_leap_writes_its_reports(
    make_emulator, tmp_path: Path
) -> None:
    # Stopping at DONE ends the run right after the JMP: the tile at DONE
    # is entered, but its NOP never runs.
    tiling = run_with_tiling(make_emulator, DONE, tmp_path)

    assert tiling.current_tile.start_pc == DONE
    assert tiling.current_tile.instructions == 0

    split_tiles = read_rows(tmp_path / SPLIT_TILES_FILE)
    split_transitions = read_rows(tmp_path / SPLIT_TRANSITIONS_FILE)
    assert "6013" not in [row["tile_start_PC"] for row in split_tiles]
    assert "6013" not in [row["target_tile"] for row in split_transitions]

    measurements = (tmp_path / MEASUREMENTS_FILE).read_text(encoding="utf-8")
    assert "Leaps into a tile that never ran: 1" in measurements


def test_run_stopped_after_the_last_tile_ran_leaves_nothing_out(
    make_emulator, tmp_path: Path
) -> None:
    # Stopping behind the NOP: the tile at DONE has run, so it is a split
    # tile like any other.
    run_with_tiling(make_emulator, DONE + 1, tmp_path)

    split_tiles = read_rows(tmp_path / SPLIT_TILES_FILE)
    assert "6013" in [row["tile_start_PC"] for row in split_tiles]

    measurements = (tmp_path / MEASUREMENTS_FILE).read_text(encoding="utf-8")
    assert "Leaps into a tile that never ran: 0" in measurements
