"""Tests for colors and position in the editor's breadcrumb path."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from prompt_toolkit.formatted_text import FormattedText

from papple2.workbench import shell
from papple2.workbench.basic_blocks_analysis import (
    BasicBlock,
    BlockGraph,
    Routines,
)
from papple2.workbench.colors import Colors
from papple2.workbench.listing_editor import (
    CRUMB_SEPARATOR,
    breadcrumb_text,
)


NAMES = {
    0x6238: "load_level",
    0x8336: "sprites",
    0x7A3E: "lookup_hgr",
}
SHADES = {0x6238: "green", 0x8336: "blue", 0x7A3E: "cyan"}


def path(
    entries: list[int],
    ahead: list[int],
    width: int = 80,
    shades: dict[int, str] | None = None,
) -> FormattedText:
    return breadcrumb_text(
        entries,
        ahead,
        lambda entry: NAMES.get(entry, ""),
        (SHADES if shades is None else shades).get,
        width,
    )


def test_past_current_and_future_names_use_their_assigned_colors() -> None:
    fragments = path([0x6238, 0x8336], [0x7A3E])

    assert ("ansigreen", "load_level") in fragments
    assert ("ansiblue bold", "sprites") in fragments
    assert ("ansicyan", "lookup_hgr") in fragments


def test_only_the_current_name_is_bold() -> None:
    fragments = path([0x6238, 0x8336], [0x7A3E])

    assert [
        text for style, text in fragments if "bold" in style.split()
    ] == ["sprites"]


def test_all_uncolored_names_are_gray_and_current_is_bold() -> None:
    fragments = path([0x6238, 0x8336], [0x7A3E], shades={})

    assert ("class:crumb", "load_level") in fragments
    assert ("class:crumb bold", "sprites") in fragments
    assert ("class:crumb", "lookup_hgr") in fragments


def test_separators_stay_gray() -> None:
    fragments = path([0x6238, 0x8336], [0x7A3E])

    assert [
        style for style, text in fragments if text == CRUMB_SEPARATOR
    ] == ["class:crumb", "class:crumb"]


def test_an_unlabelled_place_uses_its_address_and_color() -> None:
    fragments = path([0x9000], [], shades={0x9000: "red"})

    assert ("ansired bold", "9000") in fragments


def test_truncating_the_past_keeps_colors_attached_to_visible_places() -> None:
    fragments = path([0x6238, 0x8336, 0x7A3E], [], width=26)

    assert ("class:crumb", "...") in fragments
    assert ("ansiblue", "sprites") in fragments
    assert ("ansicyan bold", "lookup_hgr") in fragments
    assert not any(text == "load_level" for _style, text in fragments)


def test_the_current_name_stays_when_the_border_is_too_narrow() -> None:
    fragments = path([0x6238, 0x8336, 0x7A3E], [], width=5)

    assert ("class:crumb", "...") in fragments
    assert ("ansicyan bold", "lookup_hgr") in fragments
    assert not any(text == "sprites" for _style, text in fragments)


def test_truncating_the_future_keeps_its_abbreviation_gray() -> None:
    fragments = path([0x6238], [0x8336, 0x7A3E], width=26)

    assert ("ansiblue", "sprites") in fragments
    assert ("class:crumb", "...") in fragments
    assert not any(text == "lookup_hgr" for _style, text in fragments)


def test_colors_are_looked_up_by_address_not_by_label_text() -> None:
    fragments = breadcrumb_text(
        [0x6000, 0x7000],
        [0x8000],
        lambda entry: "same",
        {0x6000: "red", 0x7000: "blue", 0x8000: "green"}.get,
        80,
    )

    assert ("ansired", "same") in fragments
    assert ("ansiblue bold", "same") in fragments
    assert ("ansigreen", "same") in fragments


def test_the_shell_supplies_a_live_routine_color_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_session: None,
) -> None:
    graph = BlockGraph(
        entry=0x8336,
        blocks={0x8336: BasicBlock(0x8336, 0x83A7, 1)},
        edges={},
        successors={0x8336: []},
        predecessors={0x8336: []},
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
    monkeypatch.setattr(
        shell.session, "annotations", SimpleNamespace(labels={})
    )
    monkeypatch.setattr(shell.session, "color_store", Colors(tmp_path))
    captured = {}

    def capture(*args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(shell, "edit_rows", capture)

    shell.edit(0x8336)

    lookup = captured["color_of"]
    assert callable(lookup)
    assert lookup(0x8336) is None

    # A definition saved after the editor opens is read by the callback.
    Colors(tmp_path).color("sprites", 0x8336, 0x83A7, "blue")
    assert lookup(0x8336) == "blue"

    Colors(tmp_path).color("sprites", 0x8336, 0x8350, "blue")
    assert lookup(0x8336) is None
