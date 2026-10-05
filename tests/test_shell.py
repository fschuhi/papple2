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
    draw_gutter,
    label,
    listing,
    listing_rows,
    loop_reports,
    print_blocks,
    print_listing,
    print_routines,
    run,
    save_edit,
    set_current_run,
    show_blocks,
    show_callers,
    show_routines,
    stack_tracking_reports,
    tiling_reports,
    uncomment,
    unlabel,
    use_dossier,
    use_reports_folder,
    write_report,
)
from papple2.workbench.stack_tracking import StackTracking
from papple2.workbench.tiling import Tiling


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


def test_print_listing_lines_comments_up_after_the_widest_commented_instruction(
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

    print_listing(
        listing_rows(
            emulator, 0x6000, 0x6006, comments={0x6000: "clear", 0x6005: "done"}
        )
    )

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


def test_save_edit_saves_a_label_and_a_comment_at_once(
    tmp_path: Path, no_dossier: None
) -> None:
    Annotations(tmp_path).label(0xC000, "KBD")  # not new: no seeding
    use_dossier(tmp_path)
    assert save_edit(0x6238, "label", "LOAD_LEVEL") is None
    assert save_edit(0x627e, "comment", "two 4-bit values per byte") is None
    # A second Annotations reads the file: the changes were saved at once.
    saved = Annotations(tmp_path)
    assert saved.labels == {0x6238: "LOAD_LEVEL", 0xC000: "KBD"}
    assert saved.comments == {0x627e: "two 4-bit values per byte"}


def test_save_edit_with_empty_text_removes_the_label_or_comment(
    tmp_path: Path, no_dossier: None
) -> None:
    Annotations(tmp_path).label(0x6238, "LOAD_LEVEL")
    Annotations(tmp_path).comment(0x627e, "two 4-bit values per byte")
    use_dossier(tmp_path)
    assert save_edit(0x6238, "label", "") is None
    assert save_edit(0x627e, "comment", "") is None
    saved = Annotations(tmp_path)
    assert saved.labels == {}
    assert saved.comments == {}


def test_save_edit_with_unchanged_text_writes_nothing(
    tmp_path: Path, no_dossier: None
) -> None:
    # Leaving a field as it was is no change, also for an empty field:
    # uncomment() would refuse an address without a comment.
    Annotations(tmp_path).label(0x6238, "LOAD_LEVEL")
    use_dossier(tmp_path)
    # Removed after opening: any write would bring the file back.
    (tmp_path / "annotations.json").unlink()
    assert save_edit(0x6238, "label", "LOAD_LEVEL") is None
    assert save_edit(0x627e, "comment", "") is None
    assert not (tmp_path / "annotations.json").exists()


def test_save_edit_returns_why_a_label_was_refused(
    tmp_path: Path, no_dossier: None
) -> None:
    # The text is already the label of another address: refused, and the
    # reason comes back for the editor's message line.
    Annotations(tmp_path).label(0x6238, "LOAD_LEVEL")
    use_dossier(tmp_path)
    assert save_edit(0x6000, "label", "LOAD_LEVEL") == (
        "LOAD_LEVEL is already the label of $6238"
    )
    assert Annotations(tmp_path).labels == {0x6238: "LOAD_LEVEL"}


@pytest.fixture
def no_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start without a current run, and restore the module's after the
    test, so the tests don't see each other's run."""
    monkeypatch.setattr(shell, "run_program", None)
    monkeypatch.setattr(shell, "run_emulator", None)
    monkeypatch.setattr(shell, "run_rwts", None)
    monkeypatch.setattr(shell, "run_instrumentations", [])
    monkeypatch.setattr(shell, "routines", None)
    monkeypatch.setattr(shell, "run_graph", None)
    monkeypatch.setattr(shell, "run_transitions", None)


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


def test_show_callers_lists_the_call_sites_with_the_routines_holding_them(
    walkthrough, tmp_path: Path, capsys, no_run: None, no_dossier: None
) -> None:
    # SUB has one caller: the JSR in INNER, taken six times, in the
    # routine from 6000.
    make_walkthrough_current(walkthrough)
    use_dossier(tmp_path / "dossier")
    label(0x6000, "MAIN")
    label(0x6010, "SUB")
    capsys.readouterr()

    show_callers("SUB")

    assert capsys.readouterr().out.splitlines() == [
        "site  leap     count  routines",
        "6004  JSR          6  6000 MAIN",
    ]


def test_show_callers_of_a_routine_nothing_leaps_into(
    walkthrough, capsys, no_run: None, no_dossier: None
) -> None:
    # The run starts at 6000; no JSR or JMP leads there.
    make_walkthrough_current(walkthrough)
    capsys.readouterr()

    show_callers(0x6000)

    assert capsys.readouterr().out.splitlines() == [
        "no JSR or JMP leads into 6000"
    ]


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


def test_listing_of_a_routine_alone_lists_its_whole_range(
    walkthrough, capsys, no_run: None, no_dossier: None
) -> None:
    make_walkthrough_current(walkthrough)
    capsys.readouterr()

    # SUB is one block, $6010-$6013.
    listing(0x6010)
    alone = capsys.readouterr().out
    listing(0x6010, 0x6013)
    assert alone == capsys.readouterr().out


def test_listing_of_a_routine_alone_shows_the_gaps_between_its_blocks(
    walkthrough, capsys, no_run: None, no_dossier: None
) -> None:
    # The start routine runs from $6000 to DONE's NOP, $6013-$6014; SUB's
    # code lies between its blocks, not in it, and shows all the same.
    make_walkthrough_current(walkthrough)
    capsys.readouterr()

    listing(0x6000)
    alone = capsys.readouterr().out
    listing(0x6000, 0x6014)
    assert alone == capsys.readouterr().out


def test_the_run_commands_take_a_label_for_an_address(
    walkthrough, tmp_path: Path, capsys, no_run: None, no_dossier: None
) -> None:
    make_walkthrough_current(walkthrough)
    use_dossier(tmp_path / "dossier")
    label(0x6010, "SUB")
    capsys.readouterr()

    listing("SUB")
    by_label = capsys.readouterr().out
    listing(0x6010)
    assert by_label == capsys.readouterr().out

    show_blocks("SUB")
    by_label = capsys.readouterr().out
    show_blocks(0x6010)
    assert by_label == capsys.readouterr().out


def test_an_unknown_label_stops(
    walkthrough, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    make_walkthrough_current(walkthrough)
    use_dossier(tmp_path / "dossier")
    with pytest.raises(ValueError, match="NOWHERE"):
        show_blocks("NOWHERE")


def test_listing_of_an_address_alone_that_is_no_routine_stops(
    walkthrough, no_run: None
) -> None:
    make_walkthrough_current(walkthrough)
    with pytest.raises(ValueError, match="show_routines"):
        listing(0x6002)


@pytest.mark.parametrize(
    "command, arguments",
    [
        (show_routines, ()),
        (show_blocks, (0x6000,)),
        (show_callers, (0x6010,)),
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


class CountInstructions:
    """An instrumentation for the tests: counts the instructions it sees."""

    def __init__(self, cpu) -> None:
        self.count = 0

    def after_instruction(self) -> None:
        self.count += 1


def test_run_attaches_the_instrumentations_and_writes_nothing(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    booted = []
    use_reports_folder(tmp_path)

    run(stand_in_program(emulator, booted), 10, CountInstructions, Tiling)

    # Booted headless from the program's default binary.
    assert booted == [("data/bin/STAND_IN.BIN", True)]
    # Both attached, in the order given, and each saw every instruction.
    counter, tiling = shell.run_instrumentations
    assert isinstance(counter, CountInstructions)
    assert isinstance(tiling, Tiling)
    assert counter.count == emulator.instructions
    assert shell.run_emulator is emulator
    # run() writes nothing, and there are no routines until the reports.
    assert list(tmp_path.iterdir()) == []
    assert shell.routines is None


def test_run_boots_from_the_binary_given(
    make_emulator, no_run: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    booted = []

    run(stand_in_program(emulator, booted), 10, binary="data/bin/OTHER.BIN")

    assert booted == [("data/bin/OTHER.BIN", True)]


def test_tiling_reports_write_the_reports_and_find_the_routines(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, Tiling)
    use_reports_folder(tmp_path / "experiment")

    tiling_reports()

    assert (tmp_path / "experiment" / "lr_split_tiles.csv").exists()
    assert (tmp_path / "experiment" / "lr_split_transitions.csv").exists()
    assert list(shell.routines.graphs) == [0x6000]


def test_tiling_reports_without_a_run_stop(no_run: None) -> None:
    with pytest.raises(RuntimeError, match="run\\(\\) first"):
        tiling_reports()


def test_tiling_reports_without_tiling_stop(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, CountInstructions)
    use_reports_folder(tmp_path)
    with pytest.raises(RuntimeError, match="no Tiling"):
        tiling_reports()


def test_tiling_reports_without_a_reports_folder_stop(
    make_emulator, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, Tiling)
    with pytest.raises(RuntimeError, match="use_reports_folder"):
        tiling_reports()


# SUB is called twice: by a JSR, and by a JMP at the end of TAIL, a tail
# call. Then the program loops at DONE, so any number of instructions
# beyond the first eight can run.
TAIL_CALL_PROGRAM = """
        *=$6000
        JSR SUB
        JSR TAIL
DONE    JMP DONE
TAIL    INC $11
        JMP SUB
SUB     INC $10
        RTS
"""


def test_show_callers_counts_a_jmp_into_a_routine(
    make_emulator, tmp_path: Path, capsys, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # The JMP at 600b leads into SUB at 600e, from the routine TAIL at 6009.
    _, emulator = make_emulator(TAIL_CALL_PROGRAM)
    run(stand_in_program(emulator, []), 12, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()
    capsys.readouterr()

    show_callers(0x600e)

    assert capsys.readouterr().out.splitlines() == [
        "site  leap     count  routines",
        "6000  JSR          1  6000",
        "600b  JMP          1  6009",
    ]



def test_stack_tracking_reports_write_the_report(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, StackTracking)
    use_reports_folder(tmp_path / "experiment")

    stack_tracking_reports()

    assert (tmp_path / "experiment" / "lr_returns.csv").exists()


def test_stack_tracking_reports_without_a_run_stop(no_run: None) -> None:
    with pytest.raises(RuntimeError, match="run\\(\\) first"):
        stack_tracking_reports()


def test_stack_tracking_reports_without_stack_tracking_stop(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, Tiling)
    use_reports_folder(tmp_path)
    with pytest.raises(RuntimeError, match="no StackTracking"):
        stack_tracking_reports()


def test_stack_tracking_reports_without_a_reports_folder_stop(
    make_emulator, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(stand_in_program(emulator, []), 10, StackTracking)
    with pytest.raises(RuntimeError, match="use_reports_folder"):
        stack_tracking_reports()
