"""Tests for hidden spans in shared listing and editor rows."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.workbench import shell
from papple2.workbench.basic_blocks_analysis import BasicBlock, BlockGraph, Routines
from papple2.workbench.hidden import Hidden, HiddenRange
from papple2.workbench.listing_editor import column_widths, format_row, move
from papple2.workbench.shell import (
    hide,
    listing,
    listing_rows,
    print_listing,
    routine_place,
    unhide,
    use_dossier,
)


@pytest.fixture
def machine() -> SimpleNamespace:
    """Memory for a listing, not an executed program.

    6000 LDA #$00
    6002 BEQ $6006
    6004 LDA #$01
    6006 RTS
    """
    memory = Memory()
    memory.load_test_data(
        0x6000, [0xA9, 0x00, 0xF0, 0x02, 0xA9, 0x01, 0x60]
    )
    return SimpleNamespace(cpu=CPU(memory, 0x6000))


@pytest.fixture
def graph() -> BlockGraph:
    """Two observed blocks, with a branch across the unexecuted bytes."""
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


def test_a_hidden_span_is_one_row_without_an_address(
    machine: SimpleNamespace,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={"middle": HiddenRange(0x6002, 0x6006, "set aside")},
    )

    assert [row.address for row in rows] == [0x6000, None, 0x6006]
    hidden_row = rows[1]
    assert hidden_row.instruction == "... 6002-6006 middle: set aside ..."
    assert hidden_row.hex_bytes == ""
    assert hidden_row.label == ""
    assert hidden_row.comment == ""
    assert hidden_row.target is None


@pytest.mark.parametrize(
    "first, behind, expected",
    [
        (0x5FFF, 0x6002, "... 6000-6002 cut: note ..."),
        (0x6006, 0x6008, "... 6006-6007 cut: note ..."),
        (0x5FFF, 0x6008, "... 6000-6007 cut: note ..."),
    ],
)
def test_hidden_bounds_are_clipped_to_the_listing(
    machine: SimpleNamespace, first: int, behind: int, expected: str
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={"cut": HiddenRange(first, behind, "note")},
    )

    assert [
        row.instruction for row in rows if row.address is None
    ] == [expected]


def test_hidden_ranges_outside_the_listing_change_nothing(
    machine: SimpleNamespace,
) -> None:
    plain = listing_rows(machine, 0x6000, 0x6007)

    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={
            "before": HiddenRange(0x5FFF, 0x6000, ""),
            "after": HiddenRange(0x6007, 0x6008, ""),
        },
    )

    assert rows == plain


def test_hidden_ranges_are_displayed_in_address_order(
    machine: SimpleNamespace,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={
            "last": HiddenRange(0x6006, 0x6007, ""),
            "first": HiddenRange(0x6000, 0x6002, ""),
        },
    )

    assert [row.address for row in rows] == [None, 0x6002, 0x6004, None]
    assert rows[0].instruction == "... 6000-6002 first ..."
    assert rows[-1].instruction == "... 6006-6007 last ..."


def test_adjacent_hidden_ranges_keep_their_own_rows(
    machine: SimpleNamespace,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={
            "first": HiddenRange(0x6000, 0x6002, ""),
            "second": HiddenRange(0x6002, 0x6004, ""),
        },
    )

    assert [row.address for row in rows] == [None, None, 0x6004, 0x6006]
    assert rows[0].instruction == "... 6000-6002 first ..."
    assert rows[1].instruction == "... 6002-6004 second ..."


def test_hiding_takes_precedence_over_a_never_ran_gap(
    machine: SimpleNamespace, graph: BlockGraph,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"skipped": HiddenRange(0x6004, 0x6006, "not needed")},
    )

    assert [row.address for row in rows] == [0x6000, 0x6002, None, 0x6006]
    assert rows[2].instruction == "... 6004-6006 skipped: not needed ..."
    assert not any("never ran" in row.instruction for row in rows)


def test_a_hidden_span_can_cover_both_executed_code_and_a_gap(
    machine: SimpleNamespace, graph: BlockGraph,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"middle": HiddenRange(0x6002, 0x6006, "set aside")},
    )

    assert [row.address for row in rows] == [0x6000, None, 0x6006]
    assert rows[1].instruction == "... 6002-6006 middle: set aside ..."


def test_a_partial_hidden_gap_keeps_the_remaining_never_ran_row(
    machine: SimpleNamespace, graph: BlockGraph,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"one_byte": HiddenRange(0x6004, 0x6005, "")},
    )

    assert [row.address for row in rows] == [0x6000, 0x6002, None, None, 0x6006]
    assert rows[2].instruction == "... 6004-6005 one_byte ..."
    assert rows[3].instruction == "... 6005-6006: 1 byte never ran ..."


def test_an_arrow_passes_across_a_hidden_row(
    machine: SimpleNamespace, graph: BlockGraph, capsys,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"skipped": HiddenRange(0x6004, 0x6006, "not needed")},
    )

    print_listing(rows)

    assert capsys.readouterr().out.splitlines() == [
        "    6000  a9 00     LDA #$00",
        "+-- 6002  f0 02     BEQ $6006",
        "|   ... 6004-6006 skipped: not needed ...",
        "+-> 6006  60        RTS",
    ]


def test_a_hidden_leap_does_not_move_its_arrow_to_an_earlier_instruction(
    machine: SimpleNamespace, graph: BlockGraph,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"branch": HiddenRange(0x6002, 0x6004, "")},
    )

    assert rows[0].address == 0x6000
    assert all(row.gutter == "" for row in rows)


def test_an_arrow_into_a_hidden_target_is_dropped(
    machine: SimpleNamespace, graph: BlockGraph,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        graph=graph,
        only_ran=True,
        hidden_ranges={"return": HiddenRange(0x6006, 0x6007, "")},
    )

    assert all(row.gutter == "" for row in rows)


def test_labels_and_comments_inside_a_hidden_span_are_not_shown(
    machine: SimpleNamespace,
) -> None:
    labels = {0x6002: "branch"}
    comments = {0x6002: "choose a path"}

    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        labels=labels,
        comments=comments,
        hidden_ranges={"middle": HiddenRange(0x6002, 0x6006, "")},
    )

    assert all(not row.label and not row.comment for row in rows)
    assert labels == {0x6002: "branch"}
    assert comments == {0x6002: "choose a path"}


def test_hidden_spans_are_not_disassembled(
    machine: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = shell.Disassembler.collect_op_info

    def checked(
        self: shell.Disassembler, address: int
    ) -> tuple[shell.Disassembler.__annotations__, int]:
        assert not 0x6002 <= address < 0x6006
        return original(self, address)

    monkeypatch.setattr(shell.Disassembler, "collect_op_info", checked)

    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={"middle": HiddenRange(0x6002, 0x6006, "")},
    )

    assert [row.address for row in rows] == [0x6000, None, 0x6006]


def test_the_editor_formats_and_skips_the_hidden_row(
    machine: SimpleNamespace,
) -> None:
    rows = listing_rows(
        machine,
        0x6000,
        0x6007,
        hidden_ranges={"middle": HiddenRange(0x6002, 0x6006, "set aside")},
    )

    assert format_row(rows[1], column_widths(rows), 80) == (
        "... 6002-6006 middle: set aside ..."
    )
    assert move(rows, 0, 1) == 2
    assert move(rows, 2, -1) == 0


@pytest.fixture
def current_listing(
    machine: SimpleNamespace,
    graph: BlockGraph,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_session: None,
) -> Path:
    """A hand-made current listing, with an isolated temporary dossier."""
    monkeypatch.setattr(shell, "run_emulator", machine)
    monkeypatch.setattr(shell, "run_graph", graph)
    monkeypatch.setattr(
        shell,
        "routines",
        Routines(
            graphs={0x6000: graph},
            loops_of={0x6000: {}},
            calls_into={0x6000: 1},
        ),
    )
    use_dossier(tmp_path)
    return tmp_path


def test_listing_and_the_editor_place_load_the_same_hidden_rows(
    current_listing: Path, capsys,
) -> None:
    hide("middle", 0x6002, 0x6006, "set aside")

    shown = listing(0x6000)
    place = routine_place(0x6000)
    assert place is not None
    rows = place.load_rows()
    print_listing(rows)

    assert shown == capsys.readouterr().out.rstrip("\n")
    assert "... 6002-6006 middle: set aside ..." in shown


def test_listing_reloads_hidden_ranges_changed_in_another_session(
    current_listing: Path,
) -> None:
    Hidden(current_listing).hide("middle", 0x6002, 0x6006, "other session")

    assert "... 6002-6006 middle: other session ..." in listing(0x6000)


def test_unhide_restores_the_original_listing(
    current_listing: Path,
) -> None:
    before = listing(0x6000)
    hide("middle", 0x6002, 0x6006, "set aside")
    assert listing(0x6000) != before

    unhide("middle")

    assert listing(0x6000) == before


def test_a_listing_with_every_byte_hidden_is_one_row(
    current_listing: Path,
) -> None:
    hide("whole", 0x6000, 0x6007, "set aside")

    assert listing(0x6000) == "... 6000-6007 whole: set aside ..."
