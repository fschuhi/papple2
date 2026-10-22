"""Tests for papple2.workbench.shell: the arrows in the gutter, the
comments after the instructions, the labels in the print_* views, the
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
    BasicBlock,
    BlockGraph,
    build_graph,
    immediate_dominators,
    natural_loops,
    read_split_reports,
    routine_calls,
)
from papple2.workbench.listing_editor import PickerItem
from papple2.workbench.overview import LISTING_FILE, OVERVIEW_FILE, ROUTINES_FILE
from papple2.workbench.shell import (
    assign_lanes,
    clip,
    comment,
    contiguous_ranges,
    draw_gutter,
    hexdump,
    label,
    listing,
    listing_rows,
    loop_reports,
    overview_reports,
    print_blocks,
    print_listing,
    print_routines,
    routine_graph,
    run,
    save_edit,
    set_current_run,
    show_blocks,
    show_routine_graph,
    show_routines,
    show_ways_in,
    show_xrefs,
    stack_tracking_reports,
    tiling_reports,
    uncomment,
    unlabel,
    use_dossier,
    use_reports_folder,
    way_in_items,
    write_report,
)
from papple2.workbench.stack_tracking import StackTracking
from papple2.workbench.tiling import Tiling


def test_an_arrow_inside_another_gets_the_lane_nearer_the_code() -> None:
    # Like nested_loops' inner loop inside the outer one.
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


def test_listing_rows_carry_the_address_each_operand_names(make_emulator) -> None:
    # Loaded as bytes, not assembled, so that every addressing mode is sure:
    #   6000 LDA $1a85,Y   6003 STA ($1b),Y   6005 LDA #$0b
    #   6007 BNE $6000     6009 JMP ($0036)   600c ASL   600d RTS
    _asm, emulator = make_emulator(ENDLESS_PROGRAM)
    emulator.apple2.memory.load_test_data(
        0x6000,
        [0xB9, 0x85, 0x1A, 0x91, 0x1B, 0xA9, 0x0B, 0xD0, 0xF7,
         0x6C, 0x36, 0x00, 0x0A, 0x60],
    )

    rows = listing_rows(emulator, 0x6000, 0x600E)

    assert [row.target for row in rows] == [
        0x1A85,  # indexed: the table's start
        0x1B,  # indirect: the pointer, not where it points
        None,  # immediate: a value, no address
        0x6000,  # branch: its target
        0x0036,  # JMP (): the pointer
        None,  # accumulator
        None,  # implied
    ]


# A branch over code that never ran, loaded as bytes:
#   6000 LDA #$00   6002 BEQ $6006   6004 LDA #$01 (jumped over)   6006 RTS
NEVER_RAN_BYTES = [0xA9, 0x00, 0xF0, 0x02, 0xA9, 0x01, 0x60]


def never_ran_graph() -> BlockGraph:
    """The run of NEVER_RAN_BYTES: two blocks, and the branch between."""
    return BlockGraph(
        entry=0x6000,
        blocks={
            0x6000: BasicBlock(0x6000, 0x6004, 1),
            0x6006: BasicBlock(0x6006, 0x6007, 1),
        },
        edges={(0x6000, 0x6006): 1},
        successors={0x6000: [0x6006], 0x6006: []},
        predecessors={0x6000: [], 0x6006: [0x6000]},
    )


def test_listing_rows_show_each_gap_that_never_ran_as_one_row(make_emulator) -> None:
    # One gap between the blocks, and one after the last: 6007 never ran.
    _asm, emulator = make_emulator(ENDLESS_PROGRAM)
    emulator.apple2.memory.load_test_data(0x6000, NEVER_RAN_BYTES)

    rows = listing_rows(emulator, 0x6000, 0x6008, graph=never_ran_graph(), only_ran=True)

    assert [row.address for row in rows] == [0x6000, 0x6002, None, 0x6006, None]
    assert rows[2].instruction == "... 6004-6006: 2 bytes never ran ..."
    assert rows[4].instruction == "... 6007-6008: 1 byte never ran ..."


def test_listing_rows_without_a_graph_show_every_instruction(make_emulator) -> None:
    _asm, emulator = make_emulator(ENDLESS_PROGRAM)
    emulator.apple2.memory.load_test_data(0x6000, NEVER_RAN_BYTES)

    rows = listing_rows(emulator, 0x6000, 0x6007)

    assert [row.address for row in rows] == [0x6000, 0x6002, 0x6004, 0x6006]


def test_print_listing_draws_the_arrow_past_a_gap(make_emulator, capsys) -> None:
    _asm, emulator = make_emulator(ENDLESS_PROGRAM)
    emulator.apple2.memory.load_test_data(0x6000, NEVER_RAN_BYTES)

    print_listing(listing_rows(emulator, 0x6000, 0x6007, graph=never_ran_graph(), only_ran=True))

    assert capsys.readouterr().out.splitlines() == [
        "    6000  a9 00     LDA #$00",
        "+-- 6002  f0 02     BEQ $6006",
        "|   ... 6004-6006: 2 bytes never ran ...",
        "+-> 6006  60        RTS",
    ]


# main's loop at 6002, and a JMP into it from sub at 6008. The label LOOP
# sits on an instruction with an operand, as in ENDLESS_PROGRAM below.
LOCAL_LABELS_PROGRAM = """
        *=$6000
        LDX #$03
LOOP    INC $10
        DEX
        BNE LOOP
        RTS
        JMP LOOP
"""


def test_listing_rows_show_local_labels_short_within_their_scope(
    make_emulator, capsys
) -> None:
    # main.loop shows as .loop in its own line and in the BNE inside main;
    # the JMP from sub leads into another scope, so it shows the full name.
    _asm, emulator = make_emulator(LOCAL_LABELS_PROGRAM)
    labels = {0x6000: "main", 0x6002: "main.loop", 0x6008: "sub"}

    print_listing(listing_rows(emulator, 0x6000, 0x600B, labels))

    assert capsys.readouterr().out.splitlines() == [
        "6000  a2 03     main   LDX #$03",
        "6002  e6 10     .loop  INC $10",
        "6004  ca               DEX",
        "6005  d0 fb            BNE .loop",
        "6007  60               RTS",
        "6008  4c 02 60  sub    JMP main.loop",
    ]


def test_print_blocks_shows_the_labels_of_the_blocks(nested_loops_run, capsys) -> None:
    # A block whose first address has a label shows it at the end; the
    # loop column is padded so the labels line up.
    print_blocks(nested_loops_run.graph, nested_loops_run.loops, nested_loops_run.labels)

    assert capsys.readouterr().out.splitlines() == [
        "block        runs  loop  label",
        "6000-6002       1  -",
        "6002-6004       2  L01   outer",
        "6004-6007       6  L02   inner",
        "6007-600a       6  L02",
        "600a-600d       2  L01",
        "600d-6010       1  -",
        "6013-6014       1  -     done",
    ]


def test_print_routines_lists_every_routine_with_its_label(
    nested_loops_run, capsys
) -> None:
    # nested_loops has two routines: the program from 6000, and sub,
    # the target of the JSR, called six times (two rounds of outer, three
    # of inner each).
    tiles, transitions = read_split_reports(nested_loops_run.folder)
    sub = build_graph(tiles, transitions, entry=0x6010)
    graphs = {0x6000: nested_loops_run.graph, 0x6010: sub}
    loops_of = {
        0x6000: nested_loops_run.loops,
        0x6010: natural_loops(sub, immediate_dominators(sub)),
    }

    print_routines(graphs, loops_of, {0x6000: 1, 0x6010: 6}, nested_loops_run.labels)

    assert capsys.readouterr().out.splitlines() == [
        "routine  blocks  bytes  called  loops  label",
        "6000          7     17       1      2",
        "6010          1      3       6      0  sub",
    ]


@pytest.fixture
def no_reports_folder(fresh_session: None) -> None:
    """Start without a reports folder: a fresh session has none, and the
    shell's own is back after the test."""


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
def no_dossier(fresh_session: None) -> None:
    """Start without a current dossier: a fresh session has none, and the
    shell's own is back after the test."""


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


def test_the_dossier_commands_take_a_label_for_an_address(
    tmp_path: Path, no_dossier: None
) -> None:
    # As in the run commands, a label stands for its address. Given a label,
    # label() renames it.
    Annotations(tmp_path).label(0x6238, "load_level")  # not new: no seeding
    use_dossier(tmp_path)

    comment("load_level", "two 4-bit values per byte")
    label("load_level", "unpack_level")
    saved = Annotations(tmp_path)
    assert saved.labels == {0x6238: "unpack_level"}
    assert saved.comments == {0x6238: "two 4-bit values per byte"}

    uncomment("unpack_level")
    unlabel("unpack_level")
    saved = Annotations(tmp_path)
    assert saved.labels == {}
    assert saved.comments == {}


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


def test_save_edit_gives_a_dotted_label_the_nearest_global_label_above(
    tmp_path: Path, no_dossier: None
) -> None:
    # 6252 is nearer to 6250 than to 6238, but 6250's label is local, so
    # it is skipped; 6300 lies below 6252 in the listing, not above.
    annotations = Annotations(tmp_path)
    annotations.label(0x6238, "routine_001")
    annotations.label(0x6250, "routine_001.start")
    annotations.label(0x6300, "routine_002")
    use_dossier(tmp_path)

    assert save_edit(0x6252, "label", ".loop1") is None

    assert Annotations(tmp_path).labels[0x6252] == "routine_001.loop1"


def test_save_edit_refuses_a_dotted_label_without_a_global_label_above(
    tmp_path: Path, no_dossier: None
) -> None:
    Annotations(tmp_path).label(0x6300, "routine_002")
    use_dossier(tmp_path)

    assert save_edit(0x6252, "label", ".loop1") == (
        ".loop1: no global label above $6252 to belong to"
    )
    assert Annotations(tmp_path).labels == {0x6300: "routine_002"}


@pytest.fixture
def no_run(fresh_session: None) -> None:
    """Start without a current run: a fresh session has none, and the
    shell's own is back after the test."""


def make_nested_loops_current(nested_loops_run) -> None:
    """nested_loops' run as the current run, read from its reports."""
    set_current_run(
        nested_loops_run.emulator,
        0x6000,
        split_tiles=nested_loops_run.folder / "lr_split_tiles.csv",
        split_transitions=nested_loops_run.folder / "lr_split_transitions.csv",
    )


def test_show_routines_lists_the_routines_of_the_current_run(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    label(0x6010, "sub")

    lines = show_routines().splitlines()
    # The program from 6000 and sub, the target of its JSR.
    assert [line.split()[0] for line in lines[1:]] == ["6000", "6010"]
    assert lines[2].endswith("sub")


def test_set_current_run_labels_the_routine_entries_without_a_label(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    # nested_loops' routines start at 6000 and 6010. 6010 has a label
    # given by hand, which stays; 6000 gets the default name.
    Annotations(tmp_path).label(0x6010, "sub")  # not new: no seeding
    use_dossier(tmp_path)

    make_nested_loops_current(nested_loops_run)

    assert Annotations(tmp_path).labels == {0x6000: "routine_6000", 0x6010: "sub"}


def test_show_blocks_shows_a_routine_of_the_current_run(
    nested_loops_run, capsys, no_run: None, no_dossier: None
) -> None:
    # No dossier open: the blocks are shown without labels.
    make_nested_loops_current(nested_loops_run)
    capsys.readouterr()

    shown = show_blocks(0x6000)
    print_blocks(nested_loops_run.graph, nested_loops_run.loops)
    assert shown == capsys.readouterr().out.rstrip("\n")


def test_show_blocks_refuses_an_address_that_is_no_routine(
    nested_loops_run, no_run: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    with pytest.raises(ValueError, match="show_routines"):
        show_blocks(0x6002)


def test_routine_of_names_the_routine_whose_block_holds_the_address(
    nested_loops_run, no_run: None
) -> None:
    # Anywhere in a block, not only at its start: 6011 lies in sub's one
    # block, 6010-6013, and 6005 in 6004-6007 of the routine from 6000.
    # No block of the run holds 7000.
    make_nested_loops_current(nested_loops_run)

    assert shell.session.routine_of(0x6011) == 0x6010
    assert shell.session.routine_of(0x6005) == 0x6000
    assert shell.session.routine_of(0x7000) is None


def test_show_ways_in_lists_the_sites_with_the_routines_holding_them(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    # sub has one caller: the JSR in inner, taken six times, in the
    # routine from 6000.
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    label(0x6000, "main")
    label(0x6010, "sub")

    assert show_ways_in("sub").splitlines() == [
        "site  kind     count  routines",
        "6004  JSR          6  6000 main",
    ]


def test_way_in_items_lead_to_the_site_in_the_routine_holding_it(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    # sub's one caller: the JSR at 6004, taken six times, in main.
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    label(0x6000, "main")

    assert way_in_items(0x6010) == [
        PickerItem("6004  JSR     main (6)", 0x6000, 0x6004)
    ]


def test_show_ways_in_of_a_routine_nothing_leaps_into(
    nested_loops_run, no_run: None, no_dossier: None
) -> None:
    # The run starts at 6000; nothing leads there.
    make_nested_loops_current(nested_loops_run)

    assert show_ways_in(0x6000).splitlines() == [
        "nothing leads into 6000"
    ]


def test_routine_graph_has_a_box_per_routine_and_an_arrow_per_call(
    nested_loops_run, no_run: None
) -> None:
    # Two routines: the program from 6000, without a label, and sub. One
    # arrow: the JSR in inner, taken six times.
    make_nested_loops_current(nested_loops_run)
    calls = routine_calls(shell.session.routines, shell.session.run_transitions)

    graph = routine_graph(shell.session.routines, calls, {0x6010: "sub"})

    assert graph.body == [
        "\tnode [fontname=Menlo shape=box]\n",
        "\t6000 [label=6000]\n",
        '\t6010 [label="sub\\n6010"]\n',
        "\t6000 -> 6010 [label=6]\n",
    ]


def test_routine_graph_draws_an_exit_in_the_look_of_its_kind(
    nested_loops_run, no_run: None
) -> None:
    # nested_loops has no exits, so one is made up: a JMP from 6000
    # into sub, taken twice. It is drawn dashed and blue, its kind named.
    make_nested_loops_current(nested_loops_run)

    graph = routine_graph(shell.session.routines, {}, exits={(0x6000, 0x6010, "jmp"): 2})

    assert graph.body[-1] == (
        '\t6000 -> 6010 [label="JMP 2" color=blue style=dashed]\n'
    )


def test_routine_graph_draws_a_routine_with_a_shade_with_a_thick_border(
    nested_loops_run, no_run: None
) -> None:
    # sub has a shade, blue; the routine from 6000 has none, and stays
    # plain.
    make_nested_loops_current(nested_loops_run)

    graph = routine_graph(
        shell.session.routines, {}, {0x6010: "sub"}, shades={0x6010: "blue"}
    )

    assert graph.body[1:3] == [
        "\t6000 [label=6000]\n",
        '\t6010 [label="sub\\n6010" color=blue penwidth=3]\n',
    ]


def test_listing_reads_the_memory_of_the_current_run(
    nested_loops_run, no_run: None, no_dossier: None
) -> None:
    make_nested_loops_current(nested_loops_run)

    assert listing(0x6000, 0x6002).splitlines()[0].startswith("6000")


def test_a_command_returns_its_text_for_ipython_to_show(
    nested_loops_run, no_run: None, no_dossier: None
) -> None:
    # IPython shows the returned text as it is, as Out[n]: no quotes, no \n.
    from IPython.lib.pretty import pretty

    make_nested_loops_current(nested_loops_run)

    shown = listing(0x6000, 0x6004)

    assert pretty(shown) == str(shown)
    assert len(shown.splitlines()) == 2


def test_loop_reports_write_into_the_reports_folder(
    nested_loops_run, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    use_reports_folder(tmp_path / "experiment")

    loop_reports(0x6000)

    assert (tmp_path / "experiment" / "lr_loops_6000.csv").exists()
    assert (tmp_path / "experiment" / "lr_loop_members_6000.csv").exists()


def test_listing_shows_a_label_given_in_another_session(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    # Two terminals on one dossier: the label comes from the other one,
    # after this session opened the dossier.
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    Annotations(tmp_path / "dossier").label(0x6010, "sub")

    assert "sub" in listing(0x6010).splitlines()[0]


def test_listing_of_a_routine_alone_lists_its_whole_range(
    nested_loops_run, no_run: None, no_dossier: None
) -> None:
    make_nested_loops_current(nested_loops_run)

    # sub is one block, $6010-$6013.
    assert listing(0x6010) == listing(0x6010, 0x6013)


def test_listing_of_a_routine_alone_shows_the_gaps_between_its_blocks(
    nested_loops_run, no_run: None, no_dossier: None
) -> None:
    # The start routine runs from $6000 to done's NOP, $6013-$6014; sub's
    # code lies between its blocks, not in it, and shows all the same.
    make_nested_loops_current(nested_loops_run)

    assert listing(0x6000) == listing(0x6000, 0x6014)


def test_the_run_commands_take_a_label_for_an_address(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    label(0x6010, "sub")

    assert listing("sub") == listing(0x6010)
    assert show_blocks("sub") == show_blocks(0x6010)


def test_an_unknown_label_stops(
    nested_loops_run, tmp_path: Path, no_run: None, no_dossier: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    use_dossier(tmp_path / "dossier")
    with pytest.raises(ValueError, match="NOWHERE"):
        show_blocks("NOWHERE")


def test_listing_of_an_address_alone_that_is_no_routine_stops(
    nested_loops_run, no_run: None
) -> None:
    make_nested_loops_current(nested_loops_run)
    with pytest.raises(ValueError, match="show_routines"):
        listing(0x6002)


@pytest.mark.parametrize(
    "command, arguments",
    [
        (show_routines, ()),
        (show_blocks, (0x6000,)),
        (show_ways_in, (0x6010,)),
        (show_routine_graph, ()),
        (listing, (0x6000, 0x6002)),
        (loop_reports, (0x6000,)),
        (hexdump, (0x6000,)),
    ],
)
def test_the_run_commands_stop_without_a_current_run(
    command, arguments, no_run: None
) -> None:
    with pytest.raises(RuntimeError, match="set_current_run"):
        command(*arguments)


# An endless loop at $6000, so any number of instructions can run. Only
# lines like nested_loops': begun with INX, the program made the
# assembler fail (UnboundLocalError for operand), which is not looked into
# yet.
ENDLESS_PROGRAM = """
        *=$6000
LOOP    INC $10
        JMP LOOP
"""


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
    use_reports_folder(tmp_path)

    run(emulator, 10, CountInstructions, Tiling)

    # Both attached, in the order given, and each saw every instruction.
    counter, tiling = shell.session.run_instrumentations
    assert isinstance(counter, CountInstructions)
    assert isinstance(tiling, Tiling)
    assert counter.count == emulator.instructions
    assert shell.session.run_emulator is emulator
    # run() writes nothing, and there are no routines until the reports.
    assert list(tmp_path.iterdir()) == []
    assert shell.session.routines is None


def test_tiling_reports_write_the_reports_and_find_the_routines(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, Tiling)
    use_reports_folder(tmp_path / "experiment")

    tiling_reports()

    assert (tmp_path / "experiment" / "lr_split_tiles.csv").exists()
    assert (tmp_path / "experiment" / "lr_split_transitions.csv").exists()
    assert list(shell.session.routines.graphs) == [0x6000]


def test_tiling_reports_without_a_run_stop(no_run: None) -> None:
    with pytest.raises(RuntimeError, match="run\\(\\) first"):
        tiling_reports()


def test_tiling_reports_without_tiling_stop(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, CountInstructions)
    use_reports_folder(tmp_path)
    with pytest.raises(RuntimeError, match="no Tiling"):
        tiling_reports()


def test_tiling_reports_without_a_reports_folder_stop(
    make_emulator, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, Tiling)
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


def test_show_ways_in_counts_a_jmp_into_a_routine(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # The JMP at 600b leads into SUB at 600e, from the routine TAIL at 6009.
    _, emulator = make_emulator(TAIL_CALL_PROGRAM)
    run(emulator, 12, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()

    assert show_ways_in(0x600e).splitlines() == [
        "site  kind     count  routines",
        "6000  JSR          1  6000",
        "600b  JMP          1  6009",
    ]


def test_show_ways_in_leaves_out_the_routines_own_loop(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # The JMP at 6002 leads back to 6000 from inside the routine: a loop,
    # not a way in.
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()

    assert show_ways_in(0x6000).splitlines() == ["nothing leads into 6000"]


# Like PUT_STATUS_LIVES and PUT_STATUS_LEVEL: LIVES runs on into BYTE,
# and LEVEL branches back into it. BYTE becomes a routine of its own.
#   6000 JSR LIVES   6003 JSR LEVEL   6006 JMP DONE
#   6009 LDA #$01    600b STA $10     600d RTS
#   600e LDA #$02    6010 BNE BYTE
GLIDE_AND_BRANCH_PROGRAM = """
        *=$6000
        JSR LIVES
        JSR LEVEL
DONE    JMP DONE
LIVES   LDA #$01
BYTE    STA $10
        RTS
LEVEL   LDA #$02
        BNE BYTE
"""


def test_show_ways_in_lists_a_glide_and_a_branch(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # A glide has no leap: its site is the start of the block that glides.
    _, emulator = make_emulator(GLIDE_AND_BRANCH_PROGRAM)
    run(emulator, 12, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()

    assert show_ways_in(0x600b).splitlines() == [
        "site  kind     count  routines",
        "6009  glide        1  6009",
        "6010  branch       1  600e",
    ]


def test_the_listing_of_a_routine_that_runs_on_says_where(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # LIVES ends without a leap: it runs on into BYTE, a routine of its own.
    _, emulator = make_emulator(GLIDE_AND_BRANCH_PROGRAM)
    run(emulator, 12, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()

    assert listing(0x6009).splitlines()[-1] == "... runs on into 600b ..."
    # A range is no routine: it ends with its last instruction.
    assert listing(0x6009, 0x600b).splitlines()[-1].startswith("6009")
    # The listing editor shows the same row, leading to BYTE.
    last = shell.routine_place(0x6009).load_rows()[-1]
    assert (last.instruction, last.target) == ("... runs on into 600b ...", 0x600B)


# Like the JMP at the end of TRY_GUARD_MOVE_DOWN into the tail of
# TRY_GUARD_MOVE_UP: DOWN jumps backward to DOOR, which lies inside UP, where
# the call to SUB returns. DOOR is no routine of its own, but a door into UP.
# SUB lies between DOOR and DOWN: were DOWN directly after DOOR, DOOR's block
# would be the exit at DOWN's door (stops_before()), and a routine of its own.
#   6000 JSR UP      6003 JSR DOWN    6006 JMP DONE
#   6009 JSR SUB     600c INC $10     600e RTS
#   600f INC $11     6011 RTS
#   6012 LDA #$02    6014 JMP DOOR
DOOR_PROGRAM = """
        *=$6000
        JSR UP
        JSR DOWN
DONE    JMP DONE
UP      JSR SUB
DOOR    INC $10
        RTS
SUB     INC $11
        RTS
DOWN    LDA #$02
        JMP DOOR
"""


def test_show_ways_in_lists_a_jmp_through_a_door(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    _, emulator = make_emulator(DOOR_PROGRAM)
    run(emulator, 12, Tiling)
    use_reports_folder(tmp_path)
    tiling_reports()

    assert show_ways_in(0x6009).splitlines() == [
        "site  kind     count  routines",
        "6000  JSR          1  6000",
        "6014  JMP          1  6012",
    ]



def test_stack_tracking_reports_write_the_report(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, StackTracking)
    use_reports_folder(tmp_path / "experiment")

    stack_tracking_reports()

    assert (tmp_path / "experiment" / "lr_returns.csv").exists()


# A dispatcher: DISPATCH pushes $600c (high byte first) and "returns"
# with RTS to $600d, TARGET, which no JSR calls. TARGET's own RTS then
# returns directly after the JSR at 6000. Then the program loops at DONE.
#   6000 JSR DISPATCH   6003 JMP DONE      6006 LDA #$60   6008 PHA
#   6009 LDA #$0C       600b PHA           600c RTS
#   600d INC $10        600f RTS
STACK_JUMP_PROGRAM = """
        *=$6000
        JSR DISPATCH
DONE    JMP DONE
DISPATCH LDA #$60
        PHA
        LDA #$0C
        PHA
        RTS
TARGET  INC $10
        RTS
"""


def test_stack_tracking_reports_make_stack_jump_targets_routines(
    make_emulator, tmp_path: Path, capsys, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(STACK_JUMP_PROGRAM)
    run(emulator, 12, Tiling, StackTracking)
    use_reports_folder(tmp_path)

    tiling_reports()
    # Before the returns: TARGET belongs to no routine.
    assert list(shell.session.routines.graphs) == [0x6000, 0x6006]

    stack_tracking_reports()
    # After: the RTS at 600c is a stack jump, and TARGET a routine.
    assert shell.session.run_stack_jumps == {(0x600C, 0x600D): 1}
    assert list(shell.session.routines.graphs) == [0x6000, 0x6006, 0x600D]


def test_show_ways_in_lists_a_stack_jump(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None,
    no_dossier: None
) -> None:
    # TARGET's only way in is DISPATCH's RTS at 600c.
    _, emulator = make_emulator(STACK_JUMP_PROGRAM)
    run(emulator, 12, Tiling, StackTracking)
    use_reports_folder(tmp_path)
    tiling_reports()
    stack_tracking_reports()

    assert show_ways_in(0x600D).splitlines() == [
        "site  kind     count  routines",
        "600c  RTS          1  6006",
    ]


def test_stack_tracking_reports_without_a_run_stop(no_run: None) -> None:
    with pytest.raises(RuntimeError, match="run\\(\\) first"):
        stack_tracking_reports()


def test_stack_tracking_reports_without_stack_tracking_stop(
    make_emulator, tmp_path: Path, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, Tiling)
    use_reports_folder(tmp_path)
    with pytest.raises(RuntimeError, match="no StackTracking"):
        stack_tracking_reports()


def test_stack_tracking_reports_without_a_reports_folder_stop(
    make_emulator, no_run: None, no_reports_folder: None
) -> None:
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10, StackTracking)
    with pytest.raises(RuntimeError, match="use_reports_folder"):
        stack_tracking_reports()


def test_overview_reports_write_the_three_files_into_the_reports_folder(
    nested_loops_run,
) -> None:
    overview_reports()

    assert (nested_loops_run.folder / OVERVIEW_FILE).exists()
    assert (nested_loops_run.folder / ROUTINES_FILE).exists()
    assert (nested_loops_run.folder / LISTING_FILE).exists()


def test_cross_referencing_reports_keep_the_rows_until_the_next_run(
    memory_tour_run, make_emulator
) -> None:
    # memory_tour_run has called cross_referencing_reports(): the rows the
    # run counted are kept, read back from the file.
    _, cross_referencing = shell.session.run_instrumentations
    assert shell.session.run_xrefs == cross_referencing.tallies

    # A new run forgets them, as it forgets the routines.
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10)
    assert shell.session.run_xrefs is None


def test_set_current_run_reads_the_xrefs_given(
    memory_tour_run, make_emulator
) -> None:
    # As lr_current does: a run without instrumentations, then the current
    # run from the reports, the cross reference's included.
    _, cross_referencing = shell.session.run_instrumentations
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    run(emulator, 10)

    set_current_run(
        emulator,
        0x6000,
        split_tiles=memory_tour_run.folder / "lr_split_tiles.csv",
        split_transitions=memory_tour_run.folder / "lr_split_transitions.csv",
        xrefs=memory_tour_run.folder / "lr_xrefs.csv",
    )

    assert shell.session.run_xrefs == cross_referencing.tallies


def test_set_current_run_without_xrefs_keeps_the_xrefs(memory_tour_run) -> None:
    # tiling_reports() calls set_current_run() without xrefs: rows read
    # before must stay.
    kept = shell.session.run_xrefs

    set_current_run(
        memory_tour_run.emulator,
        0x6000,
        split_tiles=memory_tour_run.folder / "lr_split_tiles.csv",
        split_transitions=memory_tour_run.folder / "lr_split_transitions.csv",
    )

    assert shell.session.run_xrefs is kept


def test_contiguous_ranges_are_half_open_and_split_at_gaps() -> None:
    assert contiguous_ranges({5, 0, 2, 1}) == [(0, 3), (5, 6)]
    assert contiguous_ranges(set()) == []


def test_show_xrefs_merges_a_table_read_into_one_line(
    memory_tour_run, tmp_path: Path, no_dossier: None
) -> None:
    # LDA table,X read the table's three bytes, X 2, 1, 0, once each
    # (chapter 19): one line, its effective addresses and indexes as
    # half-open ranges.
    use_dossier(tmp_path / "dossier")
    label(0x602F, "table")

    assert show_xrefs("table").splitlines() == [
        "instruction_address  code         kind       effective_address  bytes    count  indexes",
        "6002                 LDA table,X  read_data  602f-6032              3        3  00-03",
    ]


def test_show_xrefs_of_a_pointer_shows_each_kind_on_a_line_of_its_own(
    memory_tour_run, no_dossier: None
) -> None:
    # $06 is named by the STA that builds the pointer, and by LDA ($06),Y,
    # which reads the pointer's two bytes, then the byte it points at plus
    # Y (chapter 20). That byte is far from $06, but its row has the target
    # $06 too.
    assert show_xrefs(0x0006).splitlines() == [
        "instruction_address  code         kind          effective_address  bytes    count  indexes",
        "600d                 STA $06      write_data    0006-0007              1        1  -",
        "6015                 LDA ($06),Y  read_pointer  0006-0008              2        2  -",
        "6015                 LDA ($06),Y  read_data     0301-0302              1        1  01-02",
    ]


def test_show_xrefs_without_xrefs_stops(no_run: None) -> None:
    with pytest.raises(RuntimeError, match="cross_referencing_reports"):
        show_xrefs(0x0006)


# The hexdump. Sixteen bytes at $6000, over the stand-in program: H and I
# in Apple's normal text (bit 7 set), a carriage return, and a plain A.
HEXDUMP_BYTES = [0xC8, 0xC9, 0x8D, 0x41] + [0x00] * 12


@pytest.fixture
def hexdump_run(make_emulator, monkeypatch: pytest.MonkeyPatch, no_run: None):
    """A current run whose memory holds HEXDUMP_BYTES at $6000."""
    _, emulator = make_emulator(ENDLESS_PROGRAM)
    emulator.apple2.memory.load_test_data(0x6000, HEXDUMP_BYTES)
    monkeypatch.setattr(shell.session, "run_emulator", emulator)
    return emulator


def test_hexdump_starts_on_a_full_line(hexdump_run) -> None:
    # 6005 lies in the line from 6000; 6010 ends it.
    assert hexdump(0x6005, 0x6010).splitlines() == [
        "6000  c8 c9 8d 41 00 00 00 00  00 00 00 00 00 00 00 00  |HI.A............|",
    ]


def test_hexdump_rounds_its_end_up_to_a_full_line(hexdump_run) -> None:
    lines = hexdump(0x6000, 0x6011).splitlines()
    assert [line[:4] for line in lines] == ["6000", "6010"]


def test_hexdump_without_end_shows_one_page(hexdump_run) -> None:
    lines = hexdump(0x6008).splitlines()
    assert len(lines) == 16
    assert lines[-1].startswith("60f0")


def test_hexdump_stops_at_the_end_of_memory(hexdump_run) -> None:
    lines = hexdump(0xFFF8).splitlines()
    assert [line[:4] for line in lines] == ["fff0"]


def test_hexdump_takes_a_label_for_an_address(
    hexdump_run, tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path / "dossier")
    label(0x6000, "TABLE")

    assert hexdump("TABLE", 0x6010) == hexdump(0x6000, 0x6010)


# The clipboard. pbcopy and IPython are replaced by stand-ins: the tests
# run on any machine, and outside IPython.


@pytest.fixture
def clipboard(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """What clip() hands to pbcopy, one entry per call."""
    copied: list[str] = []

    def pbcopy(command, input, text, check):
        assert command == ["pbcopy"]
        copied.append(input)

    monkeypatch.setattr(shell.subprocess, "run", pbcopy)
    return copied


def test_clip_copies_the_text_given(clipboard: list[str], capsys) -> None:
    clip(shell.Text("6000  a9 00     LDA #$00\n6002  60        RTS"))

    assert clipboard == ["6000  a9 00     LDA #$00\n6002  60        RTS"]
    assert capsys.readouterr().out == "copied 2 lines\n"


def test_clip_without_text_copies_the_last_output(
    clipboard: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # IPython keeps the last output in _.
    ipython = SimpleNamespace(user_ns={"_": shell.Text("6000  60  RTS")})
    monkeypatch.setattr(shell, "get_ipython", lambda: ipython)

    clip()

    assert clipboard == ["6000  60  RTS"]


def test_clip_with_no_output_yet_copies_nothing(
    clipboard: list[str], monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # Before the first output, IPython's _ is empty.
    monkeypatch.setattr(shell, "get_ipython", lambda: SimpleNamespace(user_ns={"_": ""}))

    clip()

    assert clipboard == []
    assert capsys.readouterr().out == "nothing to copy\n"


def test_clip_without_text_outside_ipython_stops(
    clipboard: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shell, "get_ipython", lambda: None)

    with pytest.raises(RuntimeError, match="give clip"):
        clip()

