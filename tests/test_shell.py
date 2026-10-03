"""Tests for papple2.workbench.shell: the arrows in the gutter, and the
comments behind the instructions.

The arrows are given as rows, not addresses: row 0 is the listing's first
line. A span is (first row, last row); an arrow is (source row, target
row). Lane 0 lies next to the code.
"""

from papple2.workbench.shell import assign_lanes, dis, draw_gutter


def test_an_arrow_inside_another_gets_the_lane_nearer_the_code() -> None:
    # Like the walkthrough's inner loop inside the outer one.
    assert assign_lanes([(0, 4), (1, 3)]) == [1, 0]


def test_arrows_that_do_not_overlap_share_a_lane() -> None:
    assert assign_lanes([(0, 2), (3, 5)]) == [0, 0]


def test_arrows_that_meet_in_one_row_do_not_share_a_lane() -> None:
    # Their corners would be drawn into the same cell.
    assert assign_lanes([(0, 2), (2, 4)]) == [0, 1]


def test_of_two_crossing_arrows_the_shorter_one_is_placed_first() -> None:
    # Neither lies inside the other. The shorter one gets lane 0.
    assert assign_lanes([(0, 5), (3, 6)]) == [1, 0]


def test_a_forward_jump() -> None:
    assert draw_gutter(4, [(0, 3)], [0]) == [
        "+-- ",
        "|   ",
        "|   ",
        "+-> ",
    ]


def test_a_backward_jump() -> None:
    assert draw_gutter(3, [(2, 0)], [0]) == [
        "+-> ",
        "|   ",
        "+-- ",
    ]


def test_a_loop_inside_a_loop() -> None:
    # The outer arrow's line runs past the inner arrow's corners.
    assert draw_gutter(5, [(4, 0), (3, 1)], [1, 0]) == [
        "+---> ",
        "| +-> ",
        "| |   ",
        "| +-- ",
        "+---- ",
    ]


def test_no_arrows_no_gutter() -> None:
    assert draw_gutter(2, [], []) == ["", ""]


def test_dis_lines_comments_up_after_the_widest_commented_instruction(
    make_emulator, capsys
) -> None:
    # Two spaces after the widest commented instruction, then "; ".
    # STA $0300 has no comment: its line ends with the instruction, and
    # being the widest instruction, it doesn't push the comments out.
    _asm, emulator = make_emulator("""
            *=$6000
            LDA #$00
            STA $0300
            RTS
    """)

    dis(emulator, 0x6000, 0x6006, comments={0x6000: "clear", 0x6005: "done"})

    assert capsys.readouterr().out.splitlines() == [
        "6000  a9 00     LDA #$00  ; clear",
        "6002  8d 00 03  STA $0300",
        "6005  60        RTS       ; done",
    ]
