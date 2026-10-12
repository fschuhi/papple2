"""The walkthrough, told as tests.

Twenty bytes go through the whole pipeline: the run with Tiling attached,
the unbroken and the split reports, the graph of basic blocks, the
routines, the dominators, the loops and their reports, and the views at
the IPython prompt. Each test is one chapter, in the order the
pipeline goes; its name says which program it uses. The `walkthrough`
fixture in conftest.py runs the recipe of scripts/walkthrough.py.

The program, nested_loops (papple2.programs.nested_loops), with its
addresses:

    6000  a0 02            LDY #$02   ; outer loop: 2 passes
    6002  a2 03     outer  LDX #$03   ; inner loop: 3 passes per outer pass
    6004  20 10 60  inner  JSR sub
    6007  ca               DEX
    6008  d0 fa            BNE inner
    600a  88               DEY
    600b  d0 f5            BNE outer
    600d  4c 13 60         JMP done   ; jump over sub
    6010  e6 10     sub    INC $10
    6012  60               RTS
    6013  ea        done   NOP

Two words come back in every chapter. A *leap* is an instruction that
can send the run somewhere other than the next instruction: JSR, RTS,
JMP, and a branch, whether it is taken or falls through. A *glide* is
the run passing from one piece of code into the next without a leap.
"""

import csv
from pathlib import Path

from papple2.workbench.basic_blocks_analysis import (
    LOOP_MEMBERS_FILE,
    LOOPS_FILE,
    Loop,
    back_edges,
    immediate_dominators,
)
from papple2.workbench.shell import (
    listing_rows,
    loop_reports,
    print_blocks,
    print_edges,
    print_listing,
    print_loops,
    show_routines,
)
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    TILES_FILE,
    TRANSITIONS_FILE,
)


def read_rows(filename: Path) -> list[dict[str, str]]:
    with filename.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_chapter_1_nested_loops_the_run(walkthrough) -> None:
    # The recipe ran 39 instructions. That is the whole program: 1 LDY,
    # then 2 outer passes of (LDX + 3 inner passes of JSR, INC, RTS, DEX,
    # BNE) + DEY + BNE, then JMP and NOP: 1 + 2 * (1 + 3 * 5 + 2) + 2.
    # So PC stands behind done's NOP, on the first byte that never ran.
    assert walkthrough.emulator.cpu.PC == 0x6014

    # Tiling cuts the run into tiles: a tile starts where the run arrives,
    # and ends at the next leap (chapter 2). The run arrived first at
    # $6000, without a leap: that is the tile with an initial entry. It
    # stopped inside the tile at done, $6013.
    first_tile = next(
        tile for tile in walkthrough.tiling.tiles.values() if tile.initial_entries
    )
    assert first_tile.start_pc == 0x6000
    assert walkthrough.tiling.current_tile.start_pc == 0x6013


def test_chapter_2_nested_loops_unbroken_tiles(walkthrough) -> None:
    # Tiling starts a tile wherever the run arrives by a leap, and the tile
    # runs on until the next leap. The run starts at $6000 and runs LDY,
    # LDX and JSR before its first leap. Later the two BNEs leap back to
    # $6002 and $6004, and each starts a tile of its own, over bytes that
    # the first tile already ran. So the tiles overlap: the JSR at $6004
    # lies in three of them, and its leap into sub is counted under three
    # sources, 1 + 1 + 4 times. Chapter 3 cuts the tiles apart.
    #
    # The columns: where the tile starts; the address of the furthest
    # instruction it ran; its length in bytes, up to the end of that
    # instruction; how often a leap led into it; how often it was left by
    # a leap; and how many instructions ran in it, over all its visits.
    # The instructions add up to the 39 of chapter 1.
    tiles = read_rows(walkthrough.folder / TILES_FILE)
    assert [
        (
            row["start_PC"],
            row["furthest_PC"],
            row["length_bytes"],
            row["leaped_to"],
            row["leaped_from"],
            row["instructions"],
        )
        for row in tiles
    ] == [
        # The start. No leap led here: the run began here. LDY, LDX, JSR
        # ran once, 3 instructions in $6000-$6006, 7 bytes; the JSR left it.
        ("6000", "6004", "7", "0", "1", "3"),
        # outer, entered once by BNE outer, for the second outer pass (the
        # first pass came from $6000 without a leap). LDX and JSR, 5 bytes.
        ("6002", "6004", "5", "1", "1", "2"),
        # inner, entered 4 times by BNE inner: the second and third inner
        # passes, in each of the two outer passes. Only the JSR, 4 times.
        ("6004", "6004", "3", "4", "4", "4"),
        # Behind the JSR, entered 6 times by sub's RTS. DEX and BNE inner,
        # 6 times each: 12 instructions. The BNE leaves it every time.
        ("6007", "6008", "3", "6", "6", "12"),
        # Entered twice when BNE inner falls through, once per outer pass.
        # DEY and BNE outer, twice each.
        ("600a", "600b", "3", "2", "2", "4"),
        # Entered once when BNE outer falls through. The JMP alone.
        ("600d", "600d", "3", "1", "1", "1"),
        # sub, entered 6 times by the JSR. INC and RTS, 6 times each.
        ("6010", "6012", "3", "6", "6", "12"),
        # done, entered once by the JMP. Its NOP ran, and then the run
        # stopped inside it: no leap left it.
        ("6013", "6013", "1", "1", "0", "1"),
    ]

    # One row per kind of leap: the tile it left, the leap's address and
    # opcode, for a branch whether it was taken or fell through, the tile
    # it led into, and how often. No glides here: an unbroken tile ends
    # only at a leap. The counts add up to 21, the leaped_to above.
    transitions = read_rows(walkthrough.folder / TRANSITIONS_FILE)
    assert [
        (
            row["source_tile"],
            row["leap_from_PC"],
            row["opcode"],
            row["outcome"],
            row["target_tile"],
            row["count"],
        )
        for row in transitions
    ] == [
        # The one JSR at $6004 ($20), in three tiles: from the start's
        # tile once, from outer's once, and from inner's 4 times. 6 in all.
        ("6000", "6004", "$20", "", "6010", "1"),
        ("6002", "6004", "$20", "", "6010", "1"),
        ("6004", "6004", "$20", "", "6010", "4"),
        # BNE inner ($D0) at $6008: falls through when X reaches 0, twice;
        # taken back to inner the other 4 times.
        ("6007", "6008", "$D0", "fall_through", "600a", "2"),
        ("6007", "6008", "$D0", "taken", "6004", "4"),
        # BNE outer at $600b: falls through once, at the end; taken back
        # to outer once.
        ("600a", "600b", "$D0", "fall_through", "600d", "1"),
        ("600a", "600b", "$D0", "taken", "6002", "1"),
        # JMP done ($4C), over sub.
        ("600d", "600d", "$4C", "", "6013", "1"),
        # sub's RTS ($60), back behind the JSR, once per call.
        ("6010", "6012", "$60", "", "6007", "6"),
    ]


def test_chapter_3_nested_loops_split_tiles(walkthrough) -> None:
    # The tile from $6000 ran straight through $6002 and $6004, which later
    # became entry points (the targets of the two BNEs). So it is cut there:
    # every split tile starts at an entry point and ends where the next
    # begins, or at its leap. Split tiles don't overlap; they are the basic
    # blocks.
    #
    # The columns: where the split tile starts; where it ends, half-open,
    # so the end is the first byte behind it; and how often the run went
    # through it, whether by a leap or by a glide.
    rows = read_rows(walkthrough.folder / SPLIT_TILES_FILE)
    assert [
        (row["tile_start_PC"], row["tile_end_PC"], row["executions"]) for row in rows
    ] == [
        ("6000", "6002", "1"),  # LDY, once: cut off in front of outer
        ("6002", "6004", "2"),  # outer's LDX: 2 passes, a glide and a BNE
        ("6004", "6007", "6"),  # inner's JSR: 3 passes per outer pass
        ("6007", "600a", "6"),  # DEX, BNE inner: once per return from sub
        ("600a", "600d", "2"),  # DEY, BNE outer: once per outer pass
        ("600d", "6010", "1"),  # JMP done: once, at the end
        ("6010", "6013", "6"),  # sub: INC, RTS, once per inner pass
        ("6013", "6014", "1"),  # done's NOP
    ]


def test_chapter_4_nested_loops_transitions(walkthrough) -> None:
    # The transitions of chapter 2, between split tiles now. Two kinds of
    # row are new: a glide, where the run passed a cut without a leap, has
    # no leap address and no opcode. And the JSR has one row only: the
    # three tiles it lay in are one split tile now, so its counts merge.
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
        # The first pass: LDY glides into outer's LDX.
        ("6000", "", "", "glide", "6002", "1"),
        # Each outer pass: LDX glides into inner's JSR. Twice.
        ("6002", "", "", "glide", "6004", "2"),
        # The JSR into sub: 1 + 1 + 4 of chapter 2, now 6 in one row.
        ("6004", "6004", "$20", "", "6010", "6"),
        # BNE inner and BNE outer, both outcomes each, as in chapter 2.
        ("6007", "6008", "$D0", "fall_through", "600a", "2"),
        ("6007", "6008", "$D0", "taken", "6004", "4"),
        ("600a", "600b", "$D0", "fall_through", "600d", "1"),
        ("600a", "600b", "$D0", "taken", "6002", "1"),
        # JMP done, over sub.
        ("600d", "600d", "$4C", "", "6013", "1"),
        # sub's RTS, back behind the JSR.
        ("6010", "6012", "$60", "", "6007", "6"),
    ]


def test_chapter_5_nested_loops_the_graph(walkthrough) -> None:
    # The graph of the routine at $6000: its blocks are the split tiles,
    # its edges the transitions between them, each with its count.
    graph = walkthrough.graph

    # sub ($6010) is not reachable from $6000 without following the call,
    # so it is no block of this graph: it is a routine of its own
    # (chapter 6).
    assert list(graph.blocks) == [
        0x6000, 0x6002, 0x6004, 0x6007, 0x600A, 0x600D, 0x6013,
    ]

    # The JSR's edge into sub is replaced by the call fall-through edge
    # 6004 -> 6007, with the JSR's count: seen from this routine, the call
    # is one step that comes back behind itself. The RTS gives no edge:
    # it belongs to sub.
    assert graph.edges == {
        (0x6000, 0x6002): 1,  # glide: LDY into outer
        (0x6002, 0x6004): 2,  # glide: outer's LDX into inner
        (0x6004, 0x6007): 6,  # call fall-through: JSR sub and back
        (0x6007, 0x6004): 4,  # BNE inner, taken
        (0x6007, 0x600A): 2,  # BNE inner, fall through
        (0x600A, 0x6002): 1,  # BNE outer, taken
        (0x600A, 0x600D): 1,  # BNE outer, fall through
        (0x600D, 0x6013): 1,  # JMP done
    }


def test_chapter_6_nested_loops_routines(walkthrough) -> None:
    # A routine starts at the run's start and at every JSR target. The
    # program has two: the run from $6000, entered once by the run itself,
    # and sub at $6010, called six times. show_routines() lists them; with
    # no dossier open, there are no labels.
    #
    # The columns: the routine's entry; how many blocks it has; how many
    # bytes they hold; how often it was entered; how many loops it has.
    assert show_routines().splitlines() == [
        "routine  blocks  bytes  called  loops",
        # The 7 blocks of chapter 5: 2 + 2 + 3 + 3 + 3 + 3 + 1 bytes. sub's
        # 3 bytes lie between them, but are not counted here. 2 loops:
        # outer and inner (chapter 8).
        "6000          7     17       1      2",
        # sub: one block, INC and RTS, 3 bytes, no loop.
        "6010          1      3       6      0",
    ]


def test_chapter_7_nested_loops_dominators(walkthrough) -> None:
    # A block's immediate dominator is the closest block that every path
    # from the entry to it must pass. Dominators are what makes a loop
    # findable (chapter 8).
    assert immediate_dominators(walkthrough.graph) == {
        0x6000: 0x6000,  # the entry maps to itself
        # outer has two predecessors, $6000 (the glide) and $600a (BNE
        # outer, taken). Every path from the entry passes $6000 first.
        0x6002: 0x6000,
        # inner is reached from outer (the glide) or from $6007 (BNE inner,
        # taken). $6007 itself lies behind inner, so every path into inner
        # comes through outer.
        0x6004: 0x6002,
        # Each of the rest has one way in: behind the call, behind BNE
        # inner, behind BNE outer, and the JMP's target.
        0x6007: 0x6004,
        0x600A: 0x6007,
        0x600D: 0x600A,
        0x6013: 0x600D,
    }


def test_chapter_8_nested_loops_loops(walkthrough) -> None:
    graph = walkthrough.graph

    # An edge is a back edge if its target dominates its source: the run
    # jumps back to a place it must have passed to get here. Here the two
    # jumps back of the BNEs.
    assert back_edges(graph, immediate_dominators(graph)) == [
        (0x6007, 0x6004),  # BNE inner, back to inner
        (0x600A, 0x6002),  # BNE outer, back to outer
    ]

    # Each back edge closes a natural loop: its header, plus every block
    # that reaches the back edge's source without passing the header.
    # inner's body lies inside outer's, so inner's loop is nested in
    # outer's: its parent is outer's header, and its depth is 1.
    assert walkthrough.loops == {
        0x6002: Loop(  # outer's loop
            header=0x6002,
            back_edges=((0x600A, 0x6002),),
            body=frozenset({0x6002, 0x6004, 0x6007, 0x600A}),
            parent=None,  # the outermost loop
            depth=0,
        ),
        0x6004: Loop(  # inner's loop
            header=0x6004,
            back_edges=((0x6007, 0x6004),),
            body=frozenset({0x6004, 0x6007}),
            parent=0x6002,  # inside outer's loop
            depth=1,
        ),
    }


def test_chapter_9_nested_loops_loop_reports(walkthrough) -> None:
    # loop_reports() writes chapter 8's loops into the reports folder, with
    # the routine's entry in the file names: one row per loop, and one row
    # per block, with the innermost loop holding it. The loops are named
    # L01, L02, ... in the order of their headers.
    loop_reports(0x6000)

    # The columns: the loop's name; its header block; where its back edge
    # starts, and how often it was taken; how many loops lie around it;
    # the loop it lies in; and its blocks.
    loops = read_rows(walkthrough.folder / LOOPS_FILE.format(entry=0x6000))
    assert [list(row.values()) for row in loops] == [
        # outer's loop: BNE outer jumped back once, for the second pass.
        ["L01", "6002", "600a", "1", "0", "-", "6002 6004 6007 600a"],
        # inner's loop, inside L01: BNE inner jumped back 4 times, 2 per
        # outer pass.
        ["L02", "6004", "6007", "4", "1", "L01", "6004 6007"],
    ]

    # The columns: the block, half-open; how often it ran; the innermost
    # loop holding it; and how many loops hold it. Note the two depths
    # differ: a loop's depth counts the loops around it, a block's depth
    # counts the loops it lies in. So L01 has depth 0, its blocks depth 1.
    members = read_rows(walkthrough.folder / LOOP_MEMBERS_FILE.format(entry=0x6000))
    assert [list(row.values()) for row in members] == [
        ["6000", "6002", "1", "-", "0"],  # LDY: before the loops
        ["6002", "6004", "2", "L01", "1"],  # outer's LDX
        ["6004", "6007", "6", "L02", "2"],  # inner's JSR
        ["6007", "600a", "6", "L02", "2"],  # DEX, BNE inner
        ["600a", "600d", "2", "L01", "1"],  # DEY, BNE outer
        ["600d", "6010", "1", "-", "0"],  # JMP done: after the loops
        ["6013", "6014", "1", "-", "0"],  # done's NOP
    ]


def test_chapter_10_nested_loops_the_views_at_the_prompt(walkthrough, capsys) -> None:
    # The same graph and loops, as print_blocks, print_edges and
    # print_loops show them at the prompt.
    print_blocks(walkthrough.graph, walkthrough.loops)
    print_edges(walkthrough.graph, walkthrough.loops)
    print_loops(walkthrough.loops)

    assert capsys.readouterr().out.splitlines() == [
        # Each block, how often it ran, and the innermost loop holding it.
        "block        runs  loop",
        "6000-6002       1  -",
        "6002-6004       2  L01",
        "6004-6007       6  L02",
        "6007-600a       6  L02",
        "600a-600d       2  L01",
        "600d-6010       1  -",
        "6013-6014       1  -",
        # Each edge of chapter 5 with its count; a back edge says whose.
        "edge           count",
        "6000 -> 6002       1",
        "6002 -> 6004       2",
        "6004 -> 6007       6",
        "6007 -> 6004       4  back edge of L02",
        "6007 -> 600a       2",
        "600a -> 6002       1  back edge of L01",
        "600a -> 600d       1",
        "600d -> 6013       1",
        # Each loop of chapter 9's first report, in the same order.
        "loop  header  depth  outer  back from  members",
        "L01   6002        0  -      600a       6002 6004 6007 600a",
        "L02   6004        1  L01    6007       6004 6007",
    ]


def test_chapter_11_nested_loops_one_block_disassembled(walkthrough, capsys) -> None:
    # The block 6004-6007 is one instruction: the JSR. The range is
    # half-open, so the end the block shows is the end listing_rows() takes.
    # Without names, the operand shows the address.
    print_listing(listing_rows(walkthrough.emulator, 0x6004, 0x6007))

    assert capsys.readouterr().out.splitlines() == [
        # address, the three bytes of the JSR, the instruction
        "6004  20 10 60  JSR $6010",
    ]


def test_chapter_12_nested_loops_the_whole_program_disassembled(walkthrough, capsys) -> None:
    # The twenty bytes, read back from memory after the run, with the names
    # given by hand. The four named addresses show their names twice: in
    # the column before their own instruction, and in the operands that
    # point at them. INC $10 keeps its address: $10 has no name.
    rows = listing_rows(walkthrough.emulator, 0x6000, 0x6014, walkthrough.labels)
    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "6000  a0 02            LDY #$02",
        "6002  a2 03     outer  LDX #$03",  # named, as BNE outer's target
        "6004  20 10 60  inner  JSR sub",  # named, and calling a name
        "6007  ca               DEX",
        "6008  d0 fa            BNE inner",  # $FA: 6 bytes back, to $6004
        "600a  88               DEY",
        "600b  d0 f5            BNE outer",  # $F5: 11 bytes back, to $6002
        "600d  4c 13 60         JMP done",  # the address, low byte first
        "6010  e6 10     sub    INC $10",  # a zero-page address, unnamed
        "6012  60               RTS",
        "6013  ea        done   NOP",
    ]


def test_chapter_13_nested_loops_the_jumps_as_arrows(walkthrough, capsys) -> None:
    # With the graph, listing_rows() draws the jumps the run took: the two
    # BNEs jumping back, and the JMP over sub. An arrow starts with +-- at
    # its leap and ends with +-> at its target. The inner loop's arrow lies
    # inside the outer loop's, nearer the code. The JMP's arrow shares a
    # lane with the inner loop's, since the two don't overlap. Calls are
    # not drawn: JSR sub already says where it goes. Falling through is
    # not drawn either: it goes to the next line anyway.
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
        "+---> 6002  a2 03     outer  LDX #$03",  # outer's arrow ends here
        "| +-> 6004  20 10 60  inner  JSR sub",  # inner's arrow ends here
        "| |   6007  ca               DEX",
        "| +-- 6008  d0 fa            BNE inner",  # inner's arrow starts here
        "|     600a  88               DEY",
        "+---- 600b  d0 f5            BNE outer",  # outer's arrow starts here
        "  +-- 600d  4c 13 60         JMP done",  # the JMP's arrow, in lane 0
        "  |   6010  e6 10     sub    INC $10",
        "  |   6012  60               RTS",
        "  +-> 6013  ea        done   NOP",
    ]
