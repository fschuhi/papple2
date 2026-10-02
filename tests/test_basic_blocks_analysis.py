"""Tests for papple2.workbench.basic_blocks_analysis.

The graph tests build small hand-made graphs from a few rows, without
files; one test reads the two CSVs from a temporary folder.
"""

from pathlib import Path

import pytest

from papple2.core.cpu import BNE, JMP_absolute, JMP_indirect, JSR, RTS
from papple2.workbench.basic_blocks_analysis import (
    SplitTile,
    SplitTransition,
    build_graph,
    read_split_reports,
)
from papple2.workbench.tiling import (
    BRK,
    RTI,
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
)


def tile(start: int, end: int, executions: int = 1) -> SplitTile:
    return SplitTile(start, end, executions)


def leap(
        source: int, pc: int, opcode: int, target: int, count: int = 1,
        outcome: str = "",
) -> SplitTransition:
    return SplitTransition(source, pc, opcode, outcome, target, count)


def glide(source: int, target: int, count: int = 1) -> SplitTransition:
    return SplitTransition(source, None, None, "glide", target, count)


def test_glide_edges_are_kept():
    tiles = [tile(0x1000, 0x1004, 5), tile(0x1004, 0x1008, 5)]
    graph = build_graph(tiles, [glide(0x1000, 0x1004, 5)], entry=0x1000)

    assert graph.edges == {(0x1000, 0x1004): 5}
    assert sorted(graph.blocks) == [0x1000, 0x1004]


def test_branch_and_jmp_edges_are_kept():
    tiles = [tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1010, 0x1013)]
    transitions = [
        leap(0x1000, 0x1001, BNE, 0x1010, 3, outcome="taken"),
        leap(0x1000, 0x1001, BNE, 0x1003, 2, outcome="fall_through"),
        leap(0x1003, 0x1003, JMP_absolute, 0x1010, 2),
        leap(0x1010, 0x1010, JMP_indirect, 0x1000, 1),
    ]
    graph = build_graph(tiles, transitions, entry=0x1000)

    assert graph.edges == {
        (0x1000, 0x1003): 2,
        (0x1000, 0x1010): 3,
        (0x1003, 0x1010): 2,
        (0x1010, 0x1000): 1,
    }
    assert graph.successors[0x1000] == [0x1003, 0x1010]
    assert graph.predecessors[0x1010] == [0x1000, 0x1003]


def test_self_loop_edge():
    # Like .loop1 in LOAD_LEVEL: a block that branches back to its own start.
    tiles = [tile(0x1000, 0x1006, 31), tile(0x1006, 0x1008, 1)]
    transitions = [
        leap(0x1000, 0x1004, BNE, 0x1000, 30, outcome="taken"),
        leap(0x1000, 0x1004, BNE, 0x1006, 1, outcome="fall_through"),
    ]
    graph = build_graph(tiles, transitions, entry=0x1000)

    assert graph.edges[(0x1000, 0x1000)] == 30
    assert graph.successors[0x1000] == [0x1000, 0x1006]
    assert graph.predecessors[0x1000] == [0x1000]


def test_jsr_gives_call_fall_through_edge_instead_of_edge_into_callee():
    # Caller block with a JSR at $1000; the callee at $2000 returns with RTS
    # to $1003. Neither the call nor the return becomes an edge, so the
    # callee is not reachable from the caller.
    tiles = [tile(0x1000, 0x1003, 4), tile(0x1003, 0x1004, 4), tile(0x2000, 0x2001, 4)]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000, 4),
        leap(0x2000, 0x2000, RTS, 0x1003, 4),
    ]
    graph = build_graph(tiles, transitions, entry=0x1000)

    assert graph.edges == {(0x1000, 0x1003): 4}
    assert sorted(graph.blocks) == [0x1000, 0x1003]


def test_no_call_fall_through_edge_when_jsr_never_returned():
    tiles = [tile(0x1000, 0x1003), tile(0x2000, 0x2001)]
    graph = build_graph(tiles, [leap(0x1000, 0x1000, JSR, 0x2000)], entry=0x1000)

    assert graph.edges == {}
    assert sorted(graph.blocks) == [0x1000]


@pytest.mark.parametrize("opcode", [RTS, RTI, BRK])
def test_returns_and_brk_give_no_edge(opcode: int):
    tiles = [tile(0x1000, 0x1001), tile(0x3000, 0x3001)]
    graph = build_graph(tiles, [leap(0x1000, 0x1000, opcode, 0x3000)], entry=0x1000)

    assert graph.edges == {}
    assert sorted(graph.blocks) == [0x1000]


def test_only_blocks_reachable_from_entry_are_kept():
    # $4000-$4003 is a separate piece of code that jumps into the reachable
    # part. Its edge must not show up as a predecessor of $1000.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006),
        tile(0x4000, 0x4003), tile(0x4003, 0x4006),
    ]
    transitions = [
        glide(0x1000, 0x1003),
        glide(0x4000, 0x4003),
        leap(0x4003, 0x4003, JMP_absolute, 0x1000),
    ]
    graph = build_graph(tiles, transitions, entry=0x1000)

    assert sorted(graph.blocks) == [0x1000, 0x1003]
    assert graph.edges == {(0x1000, 0x1003): 1}
    assert graph.predecessors[0x1000] == []


def test_entry_must_be_a_basic_block():
    with pytest.raises(ValueError):
        build_graph([tile(0x1000, 0x1003)], [], entry=0x1001)


def test_edge_to_a_missing_block_is_refused():
    with pytest.raises(ValueError):
        build_graph(
            [tile(0x1000, 0x1003)],
            [leap(0x1000, 0x1000, JMP_absolute, 0x5000)],
            entry=0x1000,
        )


def test_read_split_reports(tmp_path: Path):
    (tmp_path / SPLIT_TILES_FILE).write_text(
        "tile_start_PC,tile_end_PC,length_bytes,executions\n"
        "0800,0803,3,1\n"
        "2813,2821,14,1\n",
        encoding="utf-8",
    )
    (tmp_path / SPLIT_TRANSITIONS_FILE).write_text(
        "source_tile,leap_from_PC,opcode,outcome,target_tile,count\n"
        "0800,0800,$4C,,2800,1\n"
        "2800,2811,$F0,fall_through,2813,1\n"
        "2813,,,glide,2821,1\n",
        encoding="utf-8",
    )
    tiles, transitions = read_split_reports(tmp_path)

    assert tiles == [SplitTile(0x0800, 0x0803, 1), SplitTile(0x2813, 0x2821, 1)]
    assert transitions == [
        SplitTransition(0x0800, 0x0800, 0x4C, "", 0x2800, 1),
        SplitTransition(0x2800, 0x2811, 0xF0, "fall_through", 0x2813, 1),
        SplitTransition(0x2813, None, None, "glide", 0x2821, 1),
    ]
