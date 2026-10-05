"""The walkthrough, told as tests.

Twenty bytes go through the whole pipeline: the run with Tiling attached,
the reports, the graph of basic blocks, the dominators, the loops, and the
views at the IPython prompt. Each test is one chapter, in the order the
pipeline goes. The `walkthrough` fixture in conftest.py does what
scripts/walkthrough.py does.

The program, with its addresses:

    6000  a0 02            LDY #$02   ; outer loop: 2 passes
    6002  a2 03     OUTER  LDX #$03   ; inner loop: 3 passes per outer pass
    6004  20 10 60  INNER  JSR SUB
    6007  ca               DEX
    6008  d0 fa            BNE INNER
    600a  88               DEY
    600b  d0 f5            BNE OUTER
    600d  4c 13 60         JMP DONE   ; jump over SUB
    6010  e6 10     SUB    INC $10
    6012  60               RTS
    6013  ea        DONE   NOP
"""

import csv
from pathlib import Path

from papple2.workbench.basic_blocks_analysis import (
    Loop,
    back_edges,
    immediate_dominators,
)
from papple2.workbench.shell import (
    listing_rows,
    print_blocks,
    print_edges,
    print_listing,
    print_loops,
)
from papple2.workbench.tiling import SPLIT_TILES_FILE, SPLIT_TRANSITIONS_FILE


def read_rows(filename: Path) -> list[dict[str, str]]:
    with filename.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_chapter_1_the_run(walkthrough) -> None:
    # 1 LDY, then 2 outer passes of (LDX + 3 inner passes of JSR, INC, RTS,
    # DEX, BNE) + DEY + BNE, then JMP and NOP: 1 + 2 * (1 + 3 * 5 + 2) + 2.
    assert walkthrough.emulator.instructions == 39

    first_tile = next(
        tile for tile in walkthrough.tiling.tiles.values() if tile.initial_entries
    )
    assert first_tile.start_pc == 0x6000
    assert walkthrough.tiling.current_tile.start_pc == 0x6013


def test_chapter_2_split_tiles(walkthrough) -> None:
    # The tile from $6000 ran straight through $6002 and $6004, which later
    # became entry points (the targets of the two BNEs). So it is cut there:
    # every split tile starts at an entry point and ends where the next
    # begins, or at its leap.
    rows = read_rows(walkthrough.folder / SPLIT_TILES_FILE)
    assert [
        (row["tile_start_PC"], row["tile_end_PC"], row["executions"]) for row in rows
    ] == [
        ("6000", "6002", "1"),
        ("6002", "6004", "2"),  # OUTER: 2 passes
        ("6004", "6007", "6"),  # INNER: 3 passes per outer pass
        ("6007", "600a", "6"),
        ("600a", "600d", "2"),
        ("600d", "6010", "1"),
        ("6010", "6013", "6"),  # SUB: once per inner pass
        ("6013", "6014", "1"),  # DONE
    ]


def test_chapter_3_transitions(walkthrough) -> None:
    # Every kind of transition occurs: glides across the two cuts, both
    # outcomes of each BNE, and the plain leaps JSR ($20), RTS ($60) and
    # JMP ($4C), which have no outcome.
    rows = read_rows(walkthrough.folder / SPLIT_TRANSITIONS_FILE)
    assert [
        (
            row["source_tile"],
            row["leap_from_PC"],
            row["opcode"],
            row["outcome"],
            row["target_tile"],
            row["count"],
        )
        for row in rows
    ] == [
        ("6000", "", "", "glide", "6002", "1"),
        ("6002", "", "", "glide", "6004", "2"),
        ("6004", "6004", "$20", "", "6010", "6"),
        ("6007", "6008", "$D0", "fall_through", "600a", "2"),
        ("6007", "6008", "$D0", "taken", "6004", "4"),
        ("600a", "600b", "$D0", "fall_through", "600d", "1"),
        ("600a", "600b", "$D0", "taken", "6002", "1"),
        ("600d", "600d", "$4C", "", "6013", "1"),
        ("6010", "6012", "$60", "", "6007", "6"),
    ]


def test_chapter_4_the_graph(walkthrough) -> None:
    graph = walkthrough.graph

    # SUB ($6010) is not reachable from $6000 without following the call,
    # so it is no block of this graph: it is a routine of its own.
    assert list(graph.blocks) == [
        0x6000, 0x6002, 0x6004, 0x6007, 0x600A, 0x600D, 0x6013,
    ]

    # The JSR's edge into SUB is replaced by the call fall-through edge
    # 6004 -> 6007, with the JSR's count. The RTS gives no edge.
    assert graph.edges == {
        (0x6000, 0x6002): 1,  # glide
        (0x6002, 0x6004): 2,  # glide
        (0x6004, 0x6007): 6,  # call fall-through
        (0x6007, 0x6004): 4,  # BNE INNER, taken
        (0x6007, 0x600A): 2,  # BNE INNER, fall through
        (0x600A, 0x6002): 1,  # BNE OUTER, taken
        (0x600A, 0x600D): 1,  # BNE OUTER, fall through
        (0x600D, 0x6013): 1,  # JMP DONE
    }


def test_chapter_5_dominators(walkthrough) -> None:
    # A block's immediate dominator is the closest block that every path
    # from the entry to it must pass. $6002 has two predecessors, $6000 and
    # $600a (the jump back); only $6000 lies on every path.
    assert immediate_dominators(walkthrough.graph) == {
        0x6000: 0x6000,  # the entry maps to itself
        0x6002: 0x6000,
        0x6004: 0x6002,
        0x6007: 0x6004,
        0x600A: 0x6007,
        0x600D: 0x600A,
        0x6013: 0x600D,
    }


def test_chapter_6_loops(walkthrough) -> None:
    graph = walkthrough.graph

    # An edge is a back edge if its target dominates its source. Here the
    # two jumps back of the BNEs.
    assert back_edges(graph, immediate_dominators(graph)) == [
        (0x6007, 0x6004),
        (0x600A, 0x6002),
    ]

    # Each back edge closes a natural loop: its header, plus every block
    # that reaches the back edge's source without passing the header.
    # L02's body lies inside L01's, so L02 is nested in L01.
    assert walkthrough.loops == {
        0x6002: Loop(
            header=0x6002,
            back_edges=((0x600A, 0x6002),),
            body=frozenset({0x6002, 0x6004, 0x6007, 0x600A}),
            parent=None,
            depth=0,
        ),
        0x6004: Loop(
            header=0x6004,
            back_edges=((0x6007, 0x6004),),
            body=frozenset({0x6004, 0x6007}),
            parent=0x6002,
            depth=1,
        ),
    }


def test_chapter_7_the_views_at_the_prompt(walkthrough, capsys) -> None:
    # What print_blocks, print_edges and print_loops print, line by line.
    print_blocks(walkthrough.graph, walkthrough.loops)
    print_edges(walkthrough.graph, walkthrough.loops)
    print_loops(walkthrough.loops)

    assert capsys.readouterr().out.splitlines() == [
        "block        runs  loop",
        "6000-6002       1  -",
        "6002-6004       2  L01",
        "6004-6007       6  L02",
        "6007-600a       6  L02",
        "600a-600d       2  L01",
        "600d-6010       1  -",
        "6013-6014       1  -",
        "edge           count",
        "6000 -> 6002       1",
        "6002 -> 6004       2",
        "6004 -> 6007       6",
        "6007 -> 6004       4  back edge of L02",
        "6007 -> 600a       2",
        "600a -> 6002       1  back edge of L01",
        "600a -> 600d       1",
        "600d -> 6013       1",
        "loop  header  depth  outer  back from  members",
        "L01   6002        0  -      600a       6002 6004 6007 600a",
        "L02   6004        1  L01    6007       6004 6007",
    ]


def test_chapter_8_one_block_disassembled(walkthrough, capsys) -> None:
    # The block 6004-6007 is one instruction: the JSR. The range is
    # half-open, so the end the block shows is the end listing_rows() takes.
    # Without names, the operand shows the address.
    print_listing(listing_rows(walkthrough.emulator, 0x6004, 0x6007))

    assert capsys.readouterr().out.splitlines() == [
        "6004  20 10 60  JSR $6010",
    ]


def test_chapter_9_the_whole_program_disassembled(walkthrough, capsys) -> None:
    # The twenty bytes, read back from memory after the run, with the names
    # given by hand. The four named addresses show their names twice: in
    # the column before their own instruction, and in the operands that
    # point at them. INC $10 keeps its address: the disassembler doesn't name
    # zero-page operands yet.
    rows = listing_rows(walkthrough.emulator, 0x6000, 0x6014, walkthrough.labels)
    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "6000  a0 02            LDY #$02",
        "6002  a2 03     OUTER  LDX #$03",
        "6004  20 10 60  INNER  JSR SUB",
        "6007  ca               DEX",
        "6008  d0 fa            BNE INNER",
        "600a  88               DEY",
        "600b  d0 f5            BNE OUTER",
        "600d  4c 13 60         JMP DONE",
        "6010  e6 10     SUB    INC $10",
        "6012  60               RTS",
        "6013  ea        DONE   NOP",
    ]


def test_chapter_10_the_jumps_as_arrows(walkthrough, capsys) -> None:
    # With the graph, listing_rows() draws the jumps the run took: the two BNEs
    # jumping back, and the JMP over SUB. The inner loop's arrow lies
    # inside the outer loop's, nearer the code. The JMP's arrow shares a
    # lane with the inner loop's, since the two don't overlap. Calls are
    # not drawn: JSR SUB already says where it goes.
    rows = listing_rows(
        walkthrough.emulator,
        0x6000,
        0x6014,
        walkthrough.labels,
        walkthrough.graph,
    )
    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "      6000  a0 02            LDY #$02",
        "+---> 6002  a2 03     OUTER  LDX #$03",
        "| +-> 6004  20 10 60  INNER  JSR SUB",
        "| |   6007  ca               DEX",
        "| +-- 6008  d0 fa            BNE INNER",
        "|     600a  88               DEY",
        "+---- 600b  d0 f5            BNE OUTER",
        "  +-- 600d  4c 13 60         JMP DONE",
        "  |   6010  e6 10     SUB    INC $10",
        "  |   6012  60               RTS",
        "  +-> 6013  ea        DONE   NOP",
    ]
