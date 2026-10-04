"""Tests for papple2.workbench.shell: the arrows in the gutter, the
comments behind the instructions, the labels in the print_* views, the
reports folder, the current dossier, and the current run.

The arrows are given as rows, not addresses: row 0 is the listing's first
line. A span is (first row, last row); an arrow is (source row, target
row). Lane 0 lies next to the code.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from papple2.debug.disassembler import STANDARD_LABELS
from papple2.workbench import shell
from papple2.workbench.annotations import Annotations
from papple2.workbench.basic_blocks_analysis import (
    build_graph,
    immediate_dominators,
    natural_loops,
    read_split_reports,
)
from papple2.workbench.shell import (
    assign_lanes,
    comment,
    dis,
    draw_gutter,
    label,
    listing,
    loop_reports,
    print_blocks,
    print_routines,
    run,
    set_current_run,
    show_blocks,
    show_routines,
    uncomment,
    unlabel,
    use_dossier,
    use_reports_folder,
    write_report,
)


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


def test_print_blocks_shows_the_labels_of_the_blocks(walkthrough, capsys) -> None:
    # A block whose first address has a label shows it at the end; the
    # loop column is padded so the labels line up.
    print_blocks(walkthrough.graph, walkthrough.loops, walkthrough.labels)

    assert capsys.readouterr().out.splitlines() == [
        "block        runs  loop  label",
        "6000-6002       1  -",
        "6002-6004       2  L01   OUTER",
        "6004-6007       6  L02   INNER",
        "6007-600a       6  L02",
        "600a-600d       2  L01",
        "600d-6010       1  -",
        "6013-6014       1  -     DONE",
    ]


def test_print_routines_lists_every_routine_with_its_label(
    walkthrough, capsys
) -> None:
    # The walkthrough has two routines: the program from 6000, and SUB,
    # the target of the JSR, called six times (two rounds of OUTER, three
    # of INNER each).
    tiles, transitions = read_split_reports(walkthrough.folder)
    sub = build_graph(tiles, transitions, entry=0x6010)
    graphs = {0x6000: walkthrough.graph, 0x6010: sub}
    loops_of = {
        0x6000: walkthrough.loops,
        0x6010: natural_loops(sub, immediate_dominators(sub)),
    }

    print_routines(graphs, loops_of, {0x6000: 1, 0x6010: 6}, walkthrough.labels)

    assert capsys.readouterr().out.splitlines() == [
        "routine  blocks  bytes  called  loops  label",
        "6000          7     17       1      2",
        "6010          1      3       6      0  SUB",
    ]


@pytest.fixture
def no_reports_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start without a reports folder, and restore the module's after the
    test, so the tests don't see each other's folder."""
    monkeypatch.setattr(shell, "reports_folder", None)


def test_write_report_writes_into_the_reports_folder(
    tmp_path: Path, no_reports_folder: None
) -> None:
    # The folder doesn't exist yet: write_report() creates it.
    use_reports_folder(tmp_path / "lr_overview")
    write_report("lr_overview.txt", "WHOLE RUN\n")
    written = tmp_path / "lr_overview" / "lr_overview.txt"
    assert written.read_text(encoding="utf-8") == "WHOLE RUN\n"


def test_write_report_without_a_reports_folder_stops(no_reports_folder: None) -> None:
    with pytest.raises(RuntimeError, match="use_reports_folder"):
        write_report("lr_overview.txt", "WHOLE RUN\n")


@pytest.fixture
def no_dossier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start without a current dossier, and restore the module's after the
    test, so the tests don't see each other's dossier."""
    monkeypatch.setattr(shell, "dossier_folder", None)
    monkeypatch.setattr(shell, "annotations", None)


def test_a_new_dossier_starts_with_the_standard_labels(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path / "dossier")
    assert Annotations(tmp_path / "dossier").labels == STANDARD_LABELS


def test_an_existing_dossier_keeps_its_labels(
    tmp_path: Path, no_dossier: None
) -> None:
    # A dossier whose only label is one of our own: no standard labels added.
    Annotations(tmp_path).label(0x6238, "LOAD_LEVEL")
    use_dossier(tmp_path)
    assert Annotations(tmp_path).labels == {0x6238: "LOAD_LEVEL"}


def test_label_and_comment_change_the_current_dossier(
    tmp_path: Path, no_dossier: None
) -> None:
    Annotations(tmp_path).label(0xC000, "KBD")  # not new: no seeding
    use_dossier(tmp_path)
    label(0x6238, "LOAD_LEVEL")
    comment(0x627e, "two 4-bit values per byte")
    # A second Annotations reads the file: the changes were saved at once.
    saved = Annotations(tmp_path)
    assert saved.labels == {0x6238: "LOAD_LEVEL", 0xC000: "KBD"}
    assert saved.comments == {0x627e: "two 4-bit values per byte"}


@pytest.mark.parametrize(
    "command, arguments",
    [
        (label, (0x6238, "LOAD_LEVEL")),
        (unlabel, (0x6238,)),
        (comment, (0x627e, "two 4-bit values per byte")),
        (uncomment, (0x627e,)),
    ],
)
def test_the_dossier_commands_stop_without_a_dossier(
    command, arguments, no_dossier: None
) -> None:
    with pytest.raises(RuntimeError, match="use_dossier"):
        command(*arguments)


@pytest.fixture
def no_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start without a current run, and restore the module's after the
    test, so the tests don't see each other's run."""
    monkeypatch.setattr(shell, "run_emulator", None)
    monkeypatch.setattr(shell, "routines", None)
    monkeypatch.setattr(shell, "run_graph", None)
    monkeypatch.setattr(shell, "run_tiling", None)


def make_walkthrough_current(walkthrough) -> None:
    """The walkthrough's run as the current run, read from its reports."""
    set_current_run(
        walkthrough.emulator,
        0x6000,
        split_tiles=walkthrough.folder / "lr_split_tiles.csv",
        split_transitions=walkthrough.folder / "lr_split_transitions.csv",
    )


def test_show_routines_lists_the_routines_of_the_current_run(
    walkthrough, tmp_path: Path, capsys, no_run: None, no_dossier: None
) -> None:
    make_walkthrough_current(walkthrough)
    use_dossier(tmp_path / "dossier")
    label(0x6010, "SUB")
    capsys.readouterr()  # what set_current_run() printed

    show_routines()

    lines = capsys.readouterr().out.splitlines()
    # The program from 6000 and SUB, the target of its JSR.
    assert [line.split()[0] for line in lines[1:]] == ["6000", "6010"]
    assert lines[2].endswith("SUB")


def test_show_blocks_shows_a_routine_of_the_current_run(
    walkthrough, capsys, no_run: None, no_dossier: None
) -> None:
    # No dossier open: the blocks are shown without labels.
    make_walkthrough_current(walkthrough)
    capsys.readouterr()

    show_blocks(0x6000)
    shown = capsys.readouterr().out
    print_blocks(walkthrough.graph, walkthrough.loops)
    assert shown == capsys.readouterr().out


def test_show_blocks_refuses_an_address_that_is_no_routine(
    walkthrough, no_run: None
) -> None:
    make_walkthrough_current(walkthrough)
    with pytest.raises(ValueError, match="show_routines"):
        show_blocks(0x6002)


def test_listing_reads_the_memory_of_the_current_run(
    walkthrough, capsys, no_run: None, no_dossier: None
) -> None:
    make_walkthrough_current(walkthrough)
    capsys.readouterr()

    listing(0x6000, 0x6002)
    assert capsys.readouterr().out.splitlines()[0].startswith("6000")


def test_loop_reports_write_into_the_reports_folder(
    walkthrough, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    make_walkthrough_current(walkthrough)
    use_reports_folder(tmp_path / "experiment")

    loop_reports(0x6000)

    assert (tmp_path / "experiment" / "lr_loops_6000.csv").exists()
    assert (tmp_path / "experiment" / "lr_loop_members_6000.csv").exists()


@pytest.mark.parametrize(
    "command, arguments",
    [
        (show_routines, ()),
        (show_blocks, (0x6000,)),
        (listing, (0x6000, 0x6002)),
        (loop_reports, (0x6000,)),
    ],
)
def test_the_run_commands_stop_without_a_current_run(
    command, arguments, no_run: None
) -> None:
    with pytest.raises(RuntimeError, match="set_current_run"):
        command(*arguments)


# A stand-in for a program setup: an endless loop at $6000, so any number
# of instructions can run. Only lines like the walkthrough's: begun with
# INX, the program made the assembler fail (UnboundLocalError for
# operand), which is not looked into yet.
ENDLESS_PROGRAM = """
        *=$6000
LOOP    INC $10
        JMP LOOP
"""


def stand_in_program(emulator, booted: list) -> SimpleNamespace:
    """A program setup like papple2.programs.lode_runner, whose boot()
    hands out emulator and notes how it was called."""

    def boot(binary: str, headless: bool):
        booted.append((binary, headless))
        return emulator, SimpleNamespace(log=[])  # no RWTS reads

    return SimpleNamespace(
        LOAD_ADDRESS=0x6000, DEFAULT_BINARY="data/bin/STAND_IN.BIN", boot=boot
    )


def test_run_makes_the_current_run_from_its_reports(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    booted = []
    use_reports_folder(tmp_path / "experiment")

    run(stand_in_program(emulator, booted), 10)

    # Booted headless from the program's default binary.
    assert booted == [("data/bin/STAND_IN.BIN", True)]
    # The tiling reports are in the reports folder, and the current run
    # was read back from them.
    assert (tmp_path / "experiment" / "lr_split_tiles.csv").exists()
    assert (tmp_path / "experiment" / "lr_split_transitions.csv").exists()
    assert list(shell.routines.graphs) == [0x6000]
    assert shell.run_emulator is emulator
    assert shell.run_tiling is not None


def test_run_boots_from_the_binary_given(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    booted = []
    use_reports_folder(tmp_path)

    run(stand_in_program(emulator, booted), 10, "data/bin/OTHER.BIN")

    assert booted == [("data/bin/OTHER.BIN", True)]


def test_run_without_a_reports_folder_stops_before_booting(
    make_emulator, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    booted = []
    with pytest.raises(RuntimeError, match="use_reports_folder"):
        run(stand_in_program(emulator, booted), 10)
    assert booted == []
