"""Tests for the shell's color commands and range resolution."""

from pathlib import Path

import pytest

from papple2.workbench import shell
from papple2.workbench.annotations import Annotations
from papple2.workbench.basic_blocks_analysis import (
    BasicBlock,
    BlockGraph,
    Routines,
)
from papple2.workbench.colors import ColorRange, Colors
from papple2.workbench.shell import (
    color,
    colors,
    to_range,
    uncolor,
    use_dossier,
)


@pytest.fixture
def no_dossier(fresh_session: None) -> None:
    """Isolate the dossier state changed by use_dossier()."""


def test_opening_a_dossier_opens_colors_without_writing(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    assert shell.session.color_store is not None
    assert shell.session.color_store.ranges == {}
    assert not (tmp_path / "colors.json").exists()


def test_opening_a_dossier_reads_saved_colors(
    tmp_path: Path, no_dossier: None
) -> None:
    Colors(tmp_path).color("sprites", 0x8336, 0x8438, "blue")

    use_dossier(tmp_path)

    assert shell.session.color_store.ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }


def test_color_saves_bounds_without_a_current_run(
    tmp_path: Path,
    no_dossier: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shell.session, "routines", None)
    use_dossier(tmp_path)

    color("scores", 0x0010, 0x0014, "red")

    assert Colors(tmp_path).ranges == {
        "scores": ColorRange(0x0010, 0x0014, "red")
    }


def test_color_resolves_labels_for_both_bounds(
    tmp_path: Path, no_dossier: None
) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x8336, "sprites_start")
    annotations.label(0x8438, "sprites_end")
    use_dossier(tmp_path)

    color("sprites", "sprites_start", "sprites_end", "blue")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }


def test_color_resolves_labels_added_in_another_session(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    Annotations(tmp_path).label(0x8336, "sprites_start")

    color("sprites", "sprites_start", 0x8438, "blue")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }


def test_an_unknown_label_is_refused_without_saving(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    with pytest.raises(ValueError, match="no label missing"):
        color("sprites", "missing", 0x8438, "blue")

    assert not (tmp_path / "colors.json").exists()


def test_color_replaces_a_named_definition(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    color("sprites", 0x8336, 0x83A7, "blue")

    color("sprites", 0x8336, 0x8438, "cyan")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "cyan")
    }


def test_color_allows_overlaps(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    color("scores", 0x0010, 0x0014, "red")

    color("stats", 0x0012, 0x0016, "blue")

    assert shell.session.color_store.color_at(0x0012) == "magenta"
    assert len(Colors(tmp_path).ranges) == 2


def test_uncolor_removes_a_saved_definition(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    color("scores", 0x0010, 0x0014, "red")

    uncolor("scores")

    assert Colors(tmp_path).ranges == {}


def test_uncolor_refuses_an_unknown_name(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    with pytest.raises(ValueError, match="no color range missing"):
        uncolor("missing")

    assert not (tmp_path / "colors.json").exists()


@pytest.mark.parametrize("command", ["color", "uncolor", "colors"])
def test_color_commands_stop_without_a_dossier(
    command: str, no_dossier: None
) -> None:
    with pytest.raises(RuntimeError, match="use_dossier"):
        if command == "color":
            color("scores", 0x0010, 0x0014, "red")
        elif command == "uncolor":
            uncolor("scores")
        else:
            colors()


def test_colors_shows_definitions_in_address_order(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    color("sprites", 0x8336, 0x8438, "blue")
    color("scores", 0x0010, 0x0014, "red")

    assert colors().splitlines() == [
        "range      color    name",
        "0010-0014  red      scores",
        "8336-8438  blue     sprites",
    ]


def test_colors_reports_an_empty_store(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    assert colors() == "no color ranges"
    assert not (tmp_path / "colors.json").exists()


def test_colors_reloads_definitions_from_another_session(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    Colors(tmp_path).color("scores", 0x0010, 0x0014, "red")

    assert "0010-0014  red      scores" in colors()


def test_switching_dossiers_does_not_carry_colors_across(
    tmp_path: Path, no_dossier: None
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    use_dossier(first)
    color("sprites", 0x8336, 0x8438, "blue")

    use_dossier(second)

    assert shell.session.color_store.ranges == {}
    assert not (second / "colors.json").exists()

    color("scores", 0x0010, 0x0014, "red")
    assert Colors(first).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }
    assert Colors(second).ranges == {
        "scores": ColorRange(0x0010, 0x0014, "red")
    }

    use_dossier(first)

    assert shell.session.color_store.ranges == Colors(first).ranges


def test_to_range_resolves_explicit_bounds_without_a_run(
    tmp_path: Path,
    no_dossier: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shell.session, "routines", None)
    use_dossier(tmp_path)
    Annotations(tmp_path).label(0x8336, "sprites_start")

    assert to_range("sprites_start", 0x8438) == (0x8336, 0x8438)


def test_to_range_takes_integer_bounds_without_a_dossier(
    no_dossier: None,
) -> None:
    assert to_range(0x0010, 0x0014) == (0x0010, 0x0014)


def test_to_range_of_a_routine_requires_a_current_run(
    no_dossier: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shell.session, "routines", None)

    with pytest.raises(RuntimeError, match="set_current_run"):
        to_range(0x8336)


def test_a_routines_range_unpacks_into_color(
    tmp_path: Path,
    no_dossier: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Two separated blocks: the existing listing span includes the gap.
    graph = BlockGraph(
        entry=0x8336,
        blocks={
            0x8336: BasicBlock(0x8336, 0x833D, 1),
            0x8344: BasicBlock(0x8344, 0x8350, 1),
        },
        edges={(0x8336, 0x8344): 1},
        successors={0x8336: [0x8344], 0x8344: []},
        predecessors={0x8336: [], 0x8344: [0x8336]},
    )
    monkeypatch.setattr(
        shell.session,
        "routines",
        Routines(
            graphs={0x8336: graph},
            loops_of={0x8336: {}},
            calls_into={0x8336: 1},
        ),
    )
    use_dossier(tmp_path)
    Annotations(tmp_path).label(0x8336, "r_11x2_1")

    color("sprites", *to_range("r_11x2_1"), "blue")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8350, "blue")
    }


def test_color_commands_leave_other_dossier_files_untouched(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    shell.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    paths = [tmp_path / "annotations.json", tmp_path / "hidden.json"]
    before = {path: path.read_text(encoding="utf-8") for path in paths}

    color("sprites", 0x8336, 0x8438, "blue")
    uncolor("sprites")

    for path, text in before.items():
        assert path.read_text(encoding="utf-8") == text
