"""Tests for papple2.workbench.basic_blocks_analysis.

The graph tests build small hand-made graphs from a few rows, without
files; one test reads the two CSVs from a temporary folder.
"""

from pathlib import Path

import pytest

from papple2.core.cpu import BNE, JMP_absolute, JMP_indirect, JSR, RTS
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    SplitTile,
    SplitTransition,
    back_edges,
    build_graph,
    build_run_graph,
    dominates,
    find_routines,
    immediate_dominators,
    natural_loops,
    read_split_reports,
    read_split_tiles,
    read_split_transitions,
    reverse_postorder,
    routine_calls,
    write_loop_reports,
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


def test_the_run_graph_keeps_every_block_and_edge():
    # The same rows as above: the run graph keeps what build_graph() drops,
    # so a listing can draw the JMP from $4003, which no entry reaches.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006),
        tile(0x4000, 0x4003), tile(0x4003, 0x4006),
    ]
    transitions = [
        glide(0x1000, 0x1003),
        glide(0x4000, 0x4003),
        leap(0x4003, 0x4003, JMP_absolute, 0x1000),
    ]
    graph = build_run_graph(tiles, transitions, start=0x1000)

    assert graph.entry == 0x1000
    assert sorted(graph.blocks) == [0x1000, 0x1003, 0x4000, 0x4003]
    assert graph.edges == {
        (0x1000, 0x1003): 1,
        (0x4000, 0x4003): 1,
        (0x4003, 0x1000): 1,
    }
    assert graph.predecessors[0x1000] == [0x4003]


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


def test_read_split_tiles_by_its_full_path(tmp_path: Path):
    # Any name in any folder: the reader doesn't assume lr_split_tiles.csv.
    tiles_file = tmp_path / "elsewhere" / "tiles.csv"
    tiles_file.parent.mkdir()
    tiles_file.write_text(
        "tile_start_PC,tile_end_PC,length_bytes,executions\n"
        "0800,0803,3,1\n",
        encoding="utf-8",
    )
    assert read_split_tiles(tiles_file) == [SplitTile(0x0800, 0x0803, 1)]


def test_read_split_transitions_by_its_full_path(tmp_path: Path):
    transitions_file = tmp_path / "elsewhere" / "transitions.csv"
    transitions_file.parent.mkdir()
    transitions_file.write_text(
        "source_tile,leap_from_PC,opcode,outcome,target_tile,count\n"
        "0800,0800,$4C,,2800,1\n"
        "2813,,,glide,2821,1\n",
        encoding="utf-8",
    )
    assert read_split_transitions(transitions_file) == [
        SplitTransition(0x0800, 0x0800, 0x4C, "", 0x2800, 1),
        SplitTransition(0x2813, None, None, "glide", 0x2821, 1),
    ]


# --- Dominators ---------------------------------------------------------------

# The worked example: two nested loops, blocks named in address order.
E, H1, H2, B, L, X = 0x1000, 0x1010, 0x1020, 0x1030, 0x1040, 0x1050
NESTED_LOOPS = [(E, H1), (H1, H2), (H2, B), (B, H2), (B, L), (L, H1), (L, X)]


def graph_from_edges(edges: list[tuple[int, int]], entry: int) -> BlockGraph:
    """A graph with exactly these edges: one tile per block, one JMP row
    per edge. Enough for the dominator tests, which only look at edges."""
    blocks = sorted({block for edge in edges for block in edge} | {entry})
    tiles = [tile(block, block + 3) for block in blocks]
    transitions = [leap(source, source, JMP_absolute, target) for source, target in edges]
    return build_graph(tiles, transitions, entry)


def test_reverse_postorder_of_nested_loops():
    assert reverse_postorder(graph_from_edges(NESTED_LOOPS, E)) == [E, H1, H2, B, L, X]


def test_immediate_dominators_of_nested_loops():
    idom = immediate_dominators(graph_from_edges(NESTED_LOOPS, E))

    assert idom == {E: E, H1: E, H2: H1, B: H2, L: B, X: L}


def test_dominates_follows_the_tree():
    idom = immediate_dominators(graph_from_edges(NESTED_LOOPS, E))

    assert dominates(idom, H1, L)
    assert not dominates(idom, L, H1)
    assert dominates(idom, B, B)
    assert dominates(idom, E, X)


def test_diamond():
    a, b, d = 0x1010, 0x1020, 0x1030
    idom = immediate_dominators(graph_from_edges([(E, a), (E, b), (a, d), (b, d)], E))

    assert idom[d] == E
    assert not dominates(idom, a, d)
    assert not dominates(idom, b, d)


def test_self_loop_does_not_change_the_idom():
    s, x = 0x1010, 0x1020
    idom = immediate_dominators(graph_from_edges([(E, s), (s, s), (s, x)], E))

    assert idom == {E: E, s: E, x: s}


def test_loop_with_two_entries_has_no_dominating_header():
    # Neither A nor B dominates the other, so neither edge between them is
    # a back edge: natural-loop detection will not see this loop.
    a, b = 0x1010, 0x1020
    idom = immediate_dominators(graph_from_edges([(E, a), (E, b), (a, b), (b, a)], E))

    assert idom == {E: E, a: E, b: E}
    assert not dominates(idom, a, b)
    assert not dominates(idom, b, a)


def test_reverse_postorder_of_a_long_chain():
    # Deeper than Python's recursion limit: the search must not recurse.
    chain = [0x1000 + 4 * i for i in range(2000)]
    graph = graph_from_edges(list(zip(chain[:-1], chain[1:])), chain[0])

    assert reverse_postorder(graph) == chain


# --- Natural loops ------------------------------------------------------------


def loops_of(edges: list[tuple[int, int]], entry: int) -> dict[int, Loop]:
    graph = graph_from_edges(edges, entry)
    return natural_loops(graph, immediate_dominators(graph))


def test_natural_loops_of_nested_loops():
    graph = graph_from_edges(NESTED_LOOPS, E)
    idom = immediate_dominators(graph)

    assert back_edges(graph, idom) == [(B, H2), (L, H1)]
    assert natural_loops(graph, idom) == {
        H1: Loop(H1, ((L, H1),), frozenset({H1, H2, B, L}), parent=None, depth=0),
        H2: Loop(H2, ((B, H2),), frozenset({H2, B}), parent=H1, depth=1),
    }


def test_back_edges_into_one_header_make_one_loop():
    # Like a `continue`: both a and b branch back to h.
    h, a, b, x = 0x1010, 0x1020, 0x1030, 0x1040
    loops = loops_of([(E, h), (h, a), (a, h), (a, b), (b, h), (b, x)], E)

    assert loops == {
        h: Loop(h, ((a, h), (b, h)), frozenset({h, a, b}), parent=None, depth=0),
    }


def test_self_loop_is_a_loop_of_one_block():
    s, x = 0x1010, 0x1020
    loops = loops_of([(E, s), (s, s), (s, x)], E)

    assert loops == {s: Loop(s, ((s, s),), frozenset({s}), parent=None, depth=0)}


def test_sibling_loops_are_not_nested():
    # Like .loop1 and .loop2 in LOAD_LEVEL: two loops one after the other.
    a, b, x = 0x1010, 0x1020, 0x1030
    loops = loops_of([(E, a), (a, a), (a, b), (b, b), (b, x)], E)

    assert loops == {
        a: Loop(a, ((a, a),), frozenset({a}), parent=None, depth=0),
        b: Loop(b, ((b, b),), frozenset({b}), parent=None, depth=0),
    }


def test_loop_with_two_entries_is_not_found():
    a, b = 0x1010, 0x1020
    assert loops_of([(E, a), (E, b), (a, b), (b, a)], E) == {}


# --- Routines -----------------------------------------------------------------


def test_routines_are_the_start_then_the_jsr_targets_in_address_order():
    # $1000 calls $3000 first, then $2000; $2000 holds a self-loop.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2003, 3), tile(0x2003, 0x2004),
        tile(0x3000, 0x3001),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x3000),
        leap(0x3000, 0x3000, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x2000),
        leap(0x2000, 0x2001, BNE, 0x2000, 2, outcome="taken"),
        leap(0x2000, 0x2001, BNE, 0x2003, 1, outcome="fall_through"),
        leap(0x2003, 0x2003, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    # Address order, not the order of the calls.
    assert list(routines.graphs) == [0x1000, 0x2000, 0x3000]
    # Calls are not followed: the callees' blocks are not the caller's.
    assert sorted(routines.graphs[0x1000].blocks) == [0x1000, 0x1003, 0x1006]
    # A loop belongs to the routine that holds it.
    assert list(routines.loops_of[0x2000]) == [0x2000]
    assert routines.loops_of[0x1000] == {}


def test_calls_into_counts_every_jsr_and_the_run_itself():
    # $2000 is called from two places, the second one three times. Only
    # the JSR rows matter here; the rest of the run is left out.
    tiles = [tile(0x1000, 0x1003), tile(0x1003, 0x1006, 3), tile(0x2000, 0x2001, 4)]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000, 1),
        leap(0x1003, 0x1003, JSR, 0x2000, 3),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert routines.calls_into == {0x1000: 1, 0x2000: 4}


def test_a_start_that_is_also_called_is_one_routine():
    # The run enters $1000 once, and a JSR enters it twice more.
    tiles = [tile(0x1000, 0x1003, 3), tile(0x1003, 0x1006, 2)]
    transitions = [
        glide(0x1000, 0x1003, 2),
        leap(0x1003, 0x1003, JSR, 0x1000, 2),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert list(routines.graphs) == [0x1000]
    assert routines.calls_into == {0x1000: 3}


def test_routine_calls_count_the_jsrs_between_routines():
    # $1000 calls $3000 once, then $2000 three times.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006, 3), tile(0x1006, 0x1007),
        tile(0x2000, 0x2001, 3), tile(0x3000, 0x3001),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x3000),
        leap(0x3000, 0x3000, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x2000, 3),
        leap(0x2000, 0x2000, RTS, 0x1006, 3),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert routine_calls(routines, transitions) == {
        (0x1000, 0x2000): 3,
        (0x1000, 0x3000): 1,
    }


def test_a_routine_ends_at_a_jmp_into_another_routine():
    # A tail call: $3000 ends in JMP $2000. $2000 is a routine of its own,
    # so its block is not part of $3000.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2001, 2), tile(0x3000, 0x3003),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        leap(0x2000, 0x2000, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x3000),
        leap(0x3000, 0x3000, JMP_absolute, 0x2000),
        leap(0x2000, 0x2000, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert sorted(routines.graphs[0x3000].blocks) == [0x3000]
    assert routines.graphs[0x3000].edges == {}


def test_a_routine_ends_at_a_branch_into_another_routine():
    # $3000 branches straight into $2000, a routine of its own.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2001, 2), tile(0x3000, 0x3002),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        leap(0x2000, 0x2000, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x3000),
        leap(0x3000, 0x3000, BNE, 0x2000, outcome="taken"),
        leap(0x2000, 0x2000, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert sorted(routines.graphs[0x3000].blocks) == [0x3000]
    assert routines.graphs[0x3000].edges == {}


def test_a_routine_ends_where_it_runs_on_into_another_routine():
    # $2000 has no leap at its end: it glides on into $2003, which is
    # called on its own as well.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2003), tile(0x2003, 0x2004, 2),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        glide(0x2000, 0x2003),
        leap(0x2003, 0x2003, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x2003),
        leap(0x2003, 0x2003, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert sorted(routines.graphs[0x2000].blocks) == [0x2000]
    assert sorted(routines.graphs[0x2003].blocks) == [0x2003]


def test_a_branch_back_to_the_routines_own_entry_stays_a_loop():
    # $2000 branches back to its own start twice: its entry is no stop.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1004),
        tile(0x2000, 0x2002, 3), tile(0x2002, 0x2003),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        leap(0x2000, 0x2000, BNE, 0x2000, 2, outcome="taken"),
        leap(0x2000, 0x2000, BNE, 0x2002, 1, outcome="fall_through"),
        leap(0x2002, 0x2002, RTS, 0x1003),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert sorted(routines.graphs[0x2000].blocks) == [0x2000, 0x2002]
    assert list(routines.loops_of[0x2000]) == [0x2000]


def test_a_jmp_into_a_routine_gives_no_call():
    # A tail call: $3000 ends in JMP $2000, so $2000's RTS returns to
    # $1006, behind the JSR into $3000. Only the two JSRs give calls.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2001, 2), tile(0x3000, 0x3003),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        leap(0x2000, 0x2000, RTS, 0x1003),
        leap(0x1003, 0x1003, JSR, 0x3000),
        leap(0x3000, 0x3000, JMP_absolute, 0x2000),
        leap(0x2000, 0x2000, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert routine_calls(routines, transitions) == {
        (0x1000, 0x2000): 1,
        (0x1000, 0x3000): 1,
    }


def test_a_jsr_in_shared_code_is_a_call_from_every_routine_holding_it():
    # $2000 and $3000 both JMP into $4000, whose JSR calls $5000. The run
    # doesn't record through which routine $4000 was reached, so each one
    # gets the site's whole count.
    tiles = [
        tile(0x1000, 0x1003), tile(0x1003, 0x1006), tile(0x1006, 0x1007),
        tile(0x2000, 0x2003), tile(0x3000, 0x3003),
        tile(0x4000, 0x4003, 2), tile(0x4003, 0x4004, 2),
        tile(0x5000, 0x5001, 2),
    ]
    transitions = [
        leap(0x1000, 0x1000, JSR, 0x2000),
        leap(0x1003, 0x1003, JSR, 0x3000),
        leap(0x2000, 0x2000, JMP_absolute, 0x4000),
        leap(0x3000, 0x3000, JMP_absolute, 0x4000),
        leap(0x4000, 0x4000, JSR, 0x5000, 2),
        leap(0x5000, 0x5000, RTS, 0x4003, 2),
        leap(0x4003, 0x4003, RTS, 0x1003),
        leap(0x4003, 0x4003, RTS, 0x1006),
    ]
    routines = find_routines(tiles, transitions, start=0x1000)

    assert routine_calls(routines, transitions) == {
        (0x1000, 0x2000): 1,
        (0x1000, 0x3000): 1,
        (0x2000, 0x5000): 2,
        (0x3000, 0x5000): 2,
    }


# --- Loop reports -------------------------------------------------------------


def write_reports_of_nested_loops(folder: Path) -> None:
    graph = graph_from_edges(NESTED_LOOPS, E)
    write_loop_reports(folder, graph, natural_loops(graph, immediate_dominators(graph)))


def test_loops_report(tmp_path: Path):
    write_reports_of_nested_loops(tmp_path)

    # The file name carries the graph's entry, E = $1000.
    assert (tmp_path / "lr_loops_1000.csv").read_text(encoding="utf-8").splitlines() == [
        "loop_id,header_block,back_edge_source_block,back_edge_count,"
        "nesting_depth,outer_loop_id,member_blocks",
        "L01,1010,1040,1,0,-,1010 1020 1030 1040",
        "L02,1020,1030,1,1,L01,1020 1030",
    ]


def test_loop_members_report(tmp_path: Path):
    write_reports_of_nested_loops(tmp_path)

    assert (tmp_path / "lr_loop_members_1000.csv").read_text(encoding="utf-8").splitlines() == [
        "block_start_PC,block_end_PC,executions,innermost_loop,depth",
        "1000,1003,1,-,0",  # E: before the loops
        "1010,1013,1,L01,1",  # H1: outer header
        "1020,1023,1,L02,2",  # H2: inner header
        "1030,1033,1,L02,2",  # B
        "1040,1043,1,L01,1",  # L: in the outer loop only
        "1050,1053,1,-,0",  # X: after the loops
    ]
