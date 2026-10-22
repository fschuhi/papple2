"""The walkthrough, told as tests.

Twenty bytes go through the whole pipeline: the run with Tiling attached,
the unbroken and the split reports, the graph of basic blocks, the
routines, the dominators, the loops and their reports, and the views at
the IPython prompt. Each test is one chapter, in the order the
pipeline goes; its name says which program it uses. The fixture named
after the program, e.g. `nested_loops_run` in conftest.py, runs the
program's recipe from scripts/walkthrough.py.

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

The second program, rts_dispatch (papple2.programs.rts_dispatch), from
chapter 14 on. It calls two routines through a jump table, with RTS:

    6000  a9 00              LDA #$00
    6002  20 0d 60           JSR dispatch   ; routine 0
    6005  a9 01              LDA #$01
    6007  20 0d 60           JSR dispatch   ; routine 1
    600a  4c 22 60           JMP done
    600d  0a        dispatch ASL            ; A * 2: index into table
    600e  aa                 TAX
    600f  bd 1f 60           LDA table+1,X  ; high byte of address - 1
    6012  48                 PHA
    6013  bd 1e 60           LDA table,X    ; low byte
    6016  48                 PHA
    6017  60                 RTS            ; "returns" into the routine
    6018  e6 10     inc_10   INC $10
    601a  60                 RTS            ; a real return: after the JSR
    601b  e6 11     inc_11   INC $11
    601d  60                 RTS
    601e  17 60     table    .WORD inc_10-1
    6020  1a 60              .WORD inc_11-1
    6022  ea        done     NOP

The third program, memory_tour (papple2.programs.memory_tour), from
chapter 18 on. It touches memory in every way the cross reference counts:
a table, a pointer, and code that writes code:

    6000  a2 02            LDX #$02
    6002  bd 2f 60  copy   LDA table,X    ; a table read
    6005  9d 00 03         STA $0300,X    ; and a table write, into page 3
    6008  ca               DEX
    6009  10 f7            BPL copy
    600b  a9 00            LDA #$00
    600d  85 06            STA $06        ; the pointer, low byte
    600f  a9 03            LDA #$03
    6011  85 07            STA $07        ; high byte: it points at $0300
    6013  a0 01            LDY #$01
    6015  b1 06            LDA ($06),Y    ; reads the pointer, then $0301
    6017  a2 01            LDX #$01
    6019  bd 32 60  again  LDA lows,X     ; a low byte for patch's operand
    601c  8d 23 60         STA patch+1    ; writes into patch's operand
    601f  8e 26 60         STX imm+1      ; writes into imm's operand
    6022  ad 00 03  patch  LDA $0300      ; reads $0301, then $0300
    6025  a0 00     imm    LDY #$00       ; holds $01, then $00
    6027  e6 08            INC $08        ; a read and a write at $08
    6029  ca               DEX
    602a  10 ed            BPL again
    602c  4c 34 60         JMP done       ; jump over the data
    602f  11 22 33  table  .BYTE $11,$22,$33
    6032  00 01     lows   .BYTE $00,$01
    6034  ea        done   NOP

Two words come back in every chapter. A *leap* is an instruction that
can send the run somewhere other than the next instruction: JSR, RTS,
RTI, JMP, BRK, and a branch, whether it is taken or falls through. A
*glide* is the run passing from one piece of code into the next without
a leap.
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
from papple2.workbench import shell
from papple2.workbench.cross_referencing import XREFS_FILE
from papple2.workbench.shell import (
    listing_rows,
    loop_reports,
    print_blocks,
    print_edges,
    print_listing,
    print_loops,
    show_routines,
    stack_tracking_reports,
)
from papple2.workbench.stack_tracking import RETURNS_FILE
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    TILES_FILE,
    TRANSITIONS_FILE,
)


def read_rows(filename: Path) -> list[dict[str, str]]:
    with filename.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def xref_rows(folder: Path, start: int, end: int) -> list[tuple[str, ...]]:
    """The rows of the cross reference report whose instruction lies in
    start-end, half-open, as tuples of the report's columns."""
    return [
        tuple(row.values())
        for row in read_rows(folder / XREFS_FILE)
        if start <= int(row["instruction_address"], 16) < end
    ]


def test_chapter_1_nested_loops_the_run(nested_loops_run) -> None:
    # The recipe ran 39 instructions. That is the whole program: 1 LDY,
    # then 2 outer passes of (LDX + 3 inner passes of JSR, INC, RTS, DEX,
    # BNE) + DEY + BNE, then JMP and NOP: 1 + 2 * (1 + 3 * 5 + 2) + 2.
    # So PC stands after done's NOP, on the first byte that never ran.
    assert nested_loops_run.emulator.cpu.PC == 0x6014

    # Tiling cuts the run into tiles: a tile starts where the run arrives,
    # and ends at the next leap (chapter 2). The run arrived first at
    # $6000, without a leap: that is the tile with an initial entry. It
    # stopped inside the tile at done, $6013.
    first_tile = next(
        tile for tile in nested_loops_run.tiling.tiles.values() if tile.initial_entries
    )
    assert first_tile.start_pc == 0x6000
    assert nested_loops_run.tiling.current_tile.start_pc == 0x6013


def test_chapter_2_nested_loops_unbroken_tiles(nested_loops_run) -> None:
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
    tiles = read_rows(nested_loops_run.folder / TILES_FILE)
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
        # After the JSR, entered 6 times by sub's RTS. DEX and BNE inner,
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
    transitions = read_rows(nested_loops_run.folder / TRANSITIONS_FILE)
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
        # sub's RTS ($60), back directly after the JSR, once per call.
        ("6010", "6012", "$60", "", "6007", "6"),
    ]


def test_chapter_3_nested_loops_split_tiles(nested_loops_run) -> None:
    # The tile from $6000 ran straight through $6002 and $6004, which later
    # became entry points (the targets of the two BNEs). So it is cut there:
    # every split tile starts at an entry point and ends where the next
    # begins, or at its leap. Split tiles don't overlap; they are the basic
    # blocks.
    #
    # The columns: where the split tile starts; where it ends, half-open,
    # so the end is the first byte after it; and how often the run went
    # through it, whether by a leap or by a glide.
    rows = read_rows(nested_loops_run.folder / SPLIT_TILES_FILE)
    assert [
        (row["tile_start_PC"], row["tile_end_PC"], row["executions"]) for row in rows
    ] == [
        ("6000", "6002", "1"),  # LDY, once: cut off directly before outer
        ("6002", "6004", "2"),  # outer's LDX: 2 passes, a glide and a BNE
        ("6004", "6007", "6"),  # inner's JSR: 3 passes per outer pass
        ("6007", "600a", "6"),  # DEX, BNE inner: once per return from sub
        ("600a", "600d", "2"),  # DEY, BNE outer: once per outer pass
        ("600d", "6010", "1"),  # JMP done: once, at the end
        ("6010", "6013", "6"),  # sub: INC, RTS, once per inner pass
        ("6013", "6014", "1"),  # done's NOP
    ]


def test_chapter_4_nested_loops_transitions(nested_loops_run) -> None:
    # The transitions of chapter 2, between split tiles now. Two kinds of
    # row are new: a glide, where the run passed a cut without a leap, has
    # no leap address and no opcode. And the JSR has one row only: the
    # three tiles it lay in are one split tile now, so its counts merge.
    rows = read_rows(nested_loops_run.folder / SPLIT_TRANSITIONS_FILE)
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
        # sub's RTS, back directly after the JSR.
        ("6010", "6012", "$60", "", "6007", "6"),
    ]


def test_chapter_5_nested_loops_the_graph(nested_loops_run) -> None:
    # The graph of the routine at $6000: its blocks are the split tiles,
    # its edges the transitions between them, each with its count.
    graph = nested_loops_run.graph

    # sub ($6010) is not reachable from $6000 without following the call,
    # so it is no block of this graph: it is a routine of its own
    # (chapter 6).
    assert list(graph.blocks) == [
        0x6000, 0x6002, 0x6004, 0x6007, 0x600A, 0x600D, 0x6013,
    ]

    # The JSR's edge into sub is replaced by the call fall-through edge
    # 6004 -> 6007, with the JSR's count: seen from this routine, the call
    # is one step that comes back directly after itself. The RTS gives no edge:
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


def test_chapter_6_nested_loops_routines(nested_loops_run) -> None:
    # A routine starts at the run's start and at every JSR target. The
    # program has two: the routine at $6000, entered once by the run itself,
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


def test_chapter_7_nested_loops_dominators(nested_loops_run) -> None:
    # A block's immediate dominator is the closest block that every path
    # from the entry to it must pass. Dominators are what makes a loop
    # findable (chapter 8).
    assert immediate_dominators(nested_loops_run.graph) == {
        0x6000: 0x6000,  # the entry maps to itself
        # outer has two predecessors, $6000 (the glide) and $600a (BNE
        # outer, taken). Every path from the entry passes $6000 first.
        0x6002: 0x6000,
        # inner is reached from outer (the glide) or from $6007 (BNE inner,
        # taken). $6007 itself lies after inner, so every path into inner
        # comes through outer.
        0x6004: 0x6002,
        # Each of the rest has one way in: directly after the call,
        # directly after BNE inner, directly after BNE outer, and the
        # JMP's target.
        0x6007: 0x6004,
        0x600A: 0x6007,
        0x600D: 0x600A,
        0x6013: 0x600D,
    }


def test_chapter_8_nested_loops_loops(nested_loops_run) -> None:
    graph = nested_loops_run.graph

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
    assert nested_loops_run.loops == {
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


def test_chapter_9_nested_loops_loop_reports(nested_loops_run) -> None:
    # loop_reports() writes chapter 8's loops into the reports folder, with
    # the routine's entry in the file names: one row per loop, and one row
    # per block, with the innermost loop holding it. The loops are named
    # L01, L02, ... in the order of their headers.
    loop_reports(0x6000)

    # The columns: the loop's name; its header block; where its back edge
    # starts, and how often it was taken; how many loops lie around it;
    # the loop it lies in; and its blocks.
    loops = read_rows(nested_loops_run.folder / LOOPS_FILE.format(entry=0x6000))
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
    members = read_rows(nested_loops_run.folder / LOOP_MEMBERS_FILE.format(entry=0x6000))
    assert [list(row.values()) for row in members] == [
        ["6000", "6002", "1", "-", "0"],  # LDY: before the loops
        ["6002", "6004", "2", "L01", "1"],  # outer's LDX
        ["6004", "6007", "6", "L02", "2"],  # inner's JSR
        ["6007", "600a", "6", "L02", "2"],  # DEX, BNE inner
        ["600a", "600d", "2", "L01", "1"],  # DEY, BNE outer
        ["600d", "6010", "1", "-", "0"],  # JMP done: after the loops
        ["6013", "6014", "1", "-", "0"],  # done's NOP
    ]


def test_chapter_10_nested_loops_the_views_at_the_prompt(nested_loops_run, capsys) -> None:
    # The same graph and loops, as print_blocks, print_edges and
    # print_loops show them at the prompt.
    print_blocks(nested_loops_run.graph, nested_loops_run.loops)
    print_edges(nested_loops_run.graph, nested_loops_run.loops)
    print_loops(nested_loops_run.loops)

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


def test_chapter_11_nested_loops_one_block_disassembled(nested_loops_run, capsys) -> None:
    # The block 6004-6007 is one instruction: the JSR. The range is
    # half-open, so the end the block shows is the end listing_rows() takes.
    # Without names, the operand shows the address.
    print_listing(listing_rows(nested_loops_run.emulator, 0x6004, 0x6007))

    assert capsys.readouterr().out.splitlines() == [
        # address, the three bytes of the JSR, the instruction
        "6004  20 10 60  JSR $6010",
    ]


def test_chapter_12_nested_loops_the_whole_program_disassembled(nested_loops_run, capsys) -> None:
    # The twenty bytes, read back from memory after the run, with the names
    # given by hand. The four named addresses show their names twice: in
    # the column before their own instruction, and in the operands that
    # point at them. INC $10 keeps its address: $10 has no name.
    rows = listing_rows(nested_loops_run.emulator, 0x6000, 0x6014, nested_loops_run.labels)
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


def test_chapter_13_nested_loops_the_jumps_as_arrows(nested_loops_run, capsys) -> None:
    # With the graph, listing_rows() draws the jumps the run took: the two
    # BNEs jumping back, and the JMP over sub. An arrow starts with +-- at
    # its leap and ends with +-> at its target. The inner loop's arrow lies
    # inside the outer loop's, nearer the code. The JMP's arrow shares a
    # lane with the inner loop's, since the two don't overlap. Calls are
    # not drawn: JSR sub already says where it goes. Falling through is
    # not drawn either: it goes to the next line anyway.
    rows = listing_rows(
        nested_loops_run.emulator,
        0x6000,
        0x6014,
        nested_loops_run.labels,
        nested_loops_run.graph,
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


def test_chapter_14_rts_dispatch_the_run(rts_dispatch_run) -> None:
    # The recipe ran 24 instructions. That is the whole program: the main
    # line, LDA, JSR, LDA, JSR, JMP and NOP, is 6; each of the two routines
    # takes 9, dispatch's 7 (ASL, TAX, LDA, PHA, LDA, PHA, RTS) and its own
    # INC and RTS. 6 + 2 * 9. So PC stands after done's NOP.
    assert rts_dispatch_run.emulator.cpu.PC == 0x6023

    # The run stopped inside the tile at done, $6022, which the JMP led
    # into. The table at $601e-$6021 is no tile: it never ran.
    assert rts_dispatch_run.tiling.current_tile.start_pc == 0x6022
    assert 0x601E not in rts_dispatch_run.tiling.tiles


def test_chapter_15_rts_dispatch_returns(rts_dispatch_run) -> None:
    # The 6502 knows no calls. JSR pushes the address of its own last byte
    # and jumps; RTS pulls two bytes, adds one and jumps there. StackTracking
    # keeps a second stack beside the real one: each JSR opens a frame
    # there, and each RTS looks for the frame it should close.
    #
    # dispatch pushes two bytes itself, so its RTS finds no frame: it is
    # unmatched. It jumps into the routine. The routine's own RTS then
    # finds the frame that dispatch's JSR opened, and returns where that
    # frame expected, directly after the JSR: matched. The frame was opened for
    # dispatch, but closed in the routine's code.
    stack_tracking_reports()

    # The columns: the JSR that opened the frame and where it jumped; the
    # RTS that ended it and where that RTS went; the outcome; how often.
    # The unmatched returns come first, then the matched ones.
    rows = read_rows(rts_dispatch_run.folder / RETURNS_FILE)
    assert [
        (
            row["call_site"],
            row["entry"],
            row["return_site"],
            row["return_target"],
            row["outcome"],
            row["count"],
        )
        for row in rows
    ] == [
        # dispatch's RTS, no frame to close: into inc_10, then into inc_11.
        ("", "", "6017", "6018", "unmatched", "1"),
        ("", "", "6017", "601b", "unmatched", "1"),
        # inc_10's RTS closes the frame of the JSR at $6002: back to $6005.
        ("6002", "600d", "601a", "6005", "matched", "1"),
        # inc_11's RTS closes the frame of the JSR at $6007: back to $600a.
        ("6007", "600d", "601d", "600a", "matched", "1"),
    ]

    # An unmatched RTS whose target lies directly after no JSR is a stack
    # jump: a jump made with RTS. Both of dispatch's are.
    assert shell.session.run_stack_jumps == {
        (0x6017, 0x6018): 1,
        (0x6017, 0x601B): 1,
    }


def test_chapter_16_rts_dispatch_routines_before_and_after(rts_dispatch_run) -> None:
    # The routines from the tiling reports alone: the run's start, and
    # every JSR target. No JSR leads into inc_10 or inc_11, only dispatch's
    # RTS, so they are not routines yet. The columns as in chapter 6.
    assert show_routines().splitlines() == [
        "routine  blocks  bytes  called  loops",
        # $6000-$6005, $6005-$600a, $600a-$600d, and done's $6022-$6023:
        # 5 + 5 + 3 + 1 bytes. The two JSRs come back directly after themselves.
        "6000          4     14       1      0",
        # dispatch: one block, ASL to RTS, called by both JSRs.
        "600d          1     11       2      0",
    ]

    # With the stack tracking report, the targets of the stack jumps of
    # chapter 15 become routines too, each entered once.
    stack_tracking_reports()

    assert show_routines().splitlines() == [
        "routine  blocks  bytes  called  loops",
        "6000          4     14       1      0",
        "600d          1     11       2      0",
        "6018          1      3       1      0",  # inc_10: INC $10, RTS
        "601b          1      3       1      0",  # inc_11: INC $11, RTS
    ]


def test_chapter_17_rts_dispatch_the_listing(rts_dispatch_run, capsys) -> None:
    # The whole program, with the labels and the arrows of the whole run,
    # as listing() shows a range. The only arrow is the JMP over dispatch,
    # the two routines and the table. Calls are not drawn, and neither are
    # dispatch's stack jumps: an RTS gives no edge. The table never ran,
    # so it shows as one row of bytes, not as instructions.
    rows = listing_rows(
        rts_dispatch_run.emulator,
        0x6000,
        0x6023,
        rts_dispatch_run.labels,
        shell.session.run_graph,
        only_ran=True,
    )
    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "    6000  a9 00               LDA #$00",
        "    6002  20 0d 60            JSR dispatch",
        "    6005  a9 01               LDA #$01",
        "    6007  20 0d 60            JSR dispatch",
        "+-- 600a  4c 22 60            JMP done",  # the arrow starts here
        "|   600d  0a        dispatch  ASL",
        "|   600e  aa                  TAX",
        # table+1 has no label of its own, and table never ran, so the
        # operand shows the address. The next LDA hits table itself.
        "|   600f  bd 1f 60            LDA $601f,X",
        "|   6012  48                  PHA",
        "|   6013  bd 1e 60            LDA table,X",
        "|   6016  48                  PHA",
        "|   6017  60                  RTS",  # the stack jump
        "|   6018  e6 10     inc_10    INC $10",
        "|   601a  60                  RTS",  # a real return
        "|   601b  e6 11     inc_11    INC $11",
        "|   601d  60                  RTS",
        "|   ... 601e-6022: 4 bytes never ran ...",  # the table
        "+-> 6022  ea        done      NOP",  # the arrow ends here
    ]


def test_chapter_18_memory_tour_the_run(memory_tour_run) -> None:
    # This program is about the bytes the code touches, not about the
    # code: the cross reference. Tiling runs along, as in every recipe,
    # and CrossReferencing beside it. It listens to four of the memory's
    # hook lists, and counts every access by the instruction that made it.
    #
    # The recipe ran 38 instructions. That is the whole program: LDX, then
    # 3 passes of copy (LDA, STA, DEX, BPL), the 7 instructions that build
    # the pointer and read through it, then 2 passes of again (LDA, STA,
    # STX, LDA, LDY, INC, DEX, BPL), and JMP and NOP: 1 + 3 * 4 + 7 + 2 * 8
    # + 2. So PC stands after done's NOP. The data between JMP and done
    # never ran.
    assert memory_tour_run.emulator.cpu.PC == 0x6035


def test_chapter_19_memory_tour_a_table(memory_tour_run) -> None:
    # The report has one row per instruction, kind of access, target and
    # effective address. The kinds are the names of the hook lists: an
    # immediate operand, a byte of a pointer, a byte read or written as
    # data. The target is the address the operand names; the effective
    # address is the byte actually touched.
    #
    # The columns: the instruction; the kind; the target; the effective
    # address; how often; and three sets, as hex bytes: the indexes, the
    # value of X or Y the addressing mode added; the values read or
    # written; and for a write, the old values it overwrote.
    #
    # LDA table,X names one address, the table, but reaches three: X is 2,
    # then 1, then 0. So one target, three effective addresses, each with
    # the X that reached it. This is how a table looks in the report: the
    # range one instruction sweeps over.
    assert xref_rows(memory_tour_run.folder, 0x6000, 0x600B) == [
        # LDX #$02: an immediate names no address, so no target. Its byte
        # sits in the instruction, after the opcode, and is the value.
        ("6000", "read_immediate", "", "6001", "1", "", "02", ""),
        # LDA table,X: three bytes of the table, with the X for each.
        ("6002", "read_data", "602f", "602f", "1", "00", "11", ""),
        ("6002", "read_data", "602f", "6030", "1", "01", "22", ""),
        ("6002", "read_data", "602f", "6031", "1", "02", "33", ""),
        # STA $0300,X: the same three values into page 3, over zeros.
        ("6005", "write_data", "0300", "0300", "1", "00", "11", "00"),
        ("6005", "write_data", "0300", "0301", "1", "01", "22", "00"),
        ("6005", "write_data", "0300", "0302", "1", "02", "33", "00"),
    ]


def test_chapter_20_memory_tour_a_pointer(memory_tour_run) -> None:
    # Two stores build a pointer in zero page, $06 and $07, low byte first:
    # $0300. LDA ($06),Y names the pointer, $06, so all three of its rows
    # have that target: it reads the pointer's two bytes, then the byte the
    # pointer points at, plus Y. The values of the pointer rows say where
    # it pointed. Y is the index of the data row only: the pointer itself
    # is read without it.
    assert xref_rows(memory_tour_run.folder, 0x600B, 0x6017) == [
        ("600b", "read_immediate", "", "600c", "1", "", "00", ""),
        # STA $06 writes $00 over $00: a write that changed nothing.
        ("600d", "write_data", "0006", "0006", "1", "", "00", "00"),
        ("600f", "read_immediate", "", "6010", "1", "", "03", ""),
        ("6011", "write_data", "0007", "0007", "1", "", "03", "00"),
        ("6013", "read_immediate", "", "6014", "1", "", "01", ""),
        # LDA ($06),Y: the pointer, $00 and $03, so $0300; then $0300 + Y,
        # which is 1: the $22 the copy loop put there.
        ("6015", "read_pointer", "0006", "0006", "1", "", "00", ""),
        ("6015", "read_pointer", "0006", "0007", "1", "", "03", ""),
        ("6015", "read_data", "0006", "0301", "1", "01", "22", ""),
    ]


def test_chapter_21_memory_tour_code_that_writes_code(memory_tour_run) -> None:
    # The loop at again runs twice, X 1 then 0. Each pass writes into the
    # operands of two instructions further on: a low byte from lows into
    # patch's address, and X into imm's immediate. The target is read
    # from the instruction's bytes at the moment it runs, so the report
    # sees each pass as it ran.
    assert xref_rows(memory_tour_run.folder, 0x6017, 0x602F) == [
        ("6017", "read_immediate", "", "6018", "1", "", "01", ""),
        ("6019", "read_data", "6032", "6032", "1", "00", "00", ""),
        ("6019", "read_data", "6032", "6033", "1", "01", "01", ""),
        # STA patch+1 and STX imm+1: writes into code. Each wrote $01 over
        # $00 on the first pass, and $00 back over $01 on the second.
        ("601c", "write_data", "6023", "6023", "2", "", "00 01", "00 01"),
        ("601f", "write_data", "6026", "6026", "2", "", "00 01", "00 01"),
        # patch: one instruction, two targets. $0301 on the first pass,
        # $0300 on the second; each target a row of its own.
        ("6022", "read_data", "0300", "0300", "1", "", "11", ""),
        ("6022", "read_data", "0301", "0301", "1", "", "22", ""),
        # imm: one immediate, two values. An immediate seen with more than
        # one value has been written by the program: an in-code variable.
        ("6025", "read_immediate", "", "6026", "2", "", "00 01", ""),
        # INC $08 reads and writes the same byte: two kinds, one address.
        # It read $00 and $01, and wrote $01 and $02 over them: a counter.
        ("6027", "read_data", "0008", "0008", "2", "", "00 01", ""),
        ("6027", "write_data", "0008", "0008", "2", "", "01 02", "00 01"),
    ]


def test_chapter_22_memory_tour_the_listing_after_the_run(
    memory_tour_run, capsys
) -> None:
    # The listing reads the bytes as the run left them. The second pass
    # wrote back what the assembler had put there, so patch reads $0300
    # and imm holds $00, exactly as in the source. Nothing in the listing
    # shows that patch once read $0301, or that imm once held $01: only
    # the report of chapter 21 does. STA patch+1 and STX imm+1 name their
    # targets by the label of the instruction they write into.
    rows = listing_rows(
        memory_tour_run.emulator,
        0x6019,
        0x602C,
        memory_tour_run.labels,
        shell.session.run_graph,
    )
    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "+-> 6019  bd 32 60  again  LDA lows,X",
        "|   601c  8d 23 60         STA patch+1",
        "|   601f  8e 26 60         STX imm+1",
        "|   6022  ad 00 03  patch  LDA $0300",  # as the source says
        "|   6025  a0 00     imm    LDY #$00",  # as the source says
        "|   6027  e6 08            INC $08",
        "|   6029  ca               DEX",
        "+-- 602a  10 ed            BPL again",
    ]
