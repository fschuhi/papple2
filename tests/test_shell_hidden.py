"""Tests for the shell's hidden-range commands and dossier selection."""

from pathlib import Path

import pytest

from papple2.workbench import shell
from papple2.workbench.annotations import Annotations
from papple2.workbench.hidden import Hidden, HiddenRange
from papple2.workbench.shell import hide, unhide, use_dossier


@pytest.fixture
def no_dossier(fresh_session: None) -> None:
    """Start without a dossier and restore the shell's state afterwards."""


def test_opening_a_dossier_opens_hidden_ranges_without_writing(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    assert shell.session.hidden is not None
    assert shell.session.hidden.ranges == {}
    assert not (tmp_path / "hidden.json").exists()


def test_opening_a_dossier_reads_its_hidden_ranges(
    tmp_path: Path, no_dossier: None
) -> None:
    Hidden(tmp_path).hide(
        "relocation_bytes", 0x2800, 0x2832, "overwritten after it ran"
    )

    use_dossier(tmp_path)

    assert shell.session.hidden.ranges == {
        "relocation_bytes": HiddenRange(
            0x2800, 0x2832, "overwritten after it ran"
        )
    }


def test_hide_saves_address_bounds_without_a_current_run(
    tmp_path: Path,
    no_dossier: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shell, "run_emulator", None)
    monkeypatch.setattr(shell, "routines", None)
    use_dossier(tmp_path)

    hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_hide_resolves_labels_for_both_bounds(
    tmp_path: Path, no_dossier: None
) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x2800, "relocation_loop")
    annotations.label(0x2832, "after_relocation")
    use_dossier(tmp_path)

    hide(
        "relocation_bytes",
        "relocation_loop",
        "after_relocation",
        "overwritten",
    )

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_hide_resolves_a_label_added_in_another_session(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    Annotations(tmp_path).label(0x2800, "relocation_loop")

    hide("relocation_bytes", "relocation_loop", 0x2832, "overwritten")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_hide_refuses_an_unknown_label_without_saving(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    with pytest.raises(ValueError, match="no label missing"):
        hide("relocation_bytes", "missing", 0x2832, "overwritten")

    assert shell.session.hidden.ranges == {}
    assert not (tmp_path / "hidden.json").exists()


def test_hide_replaces_a_definition_with_the_same_name(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    hide("relocation_bytes", 0x2800, 0x2830, "first bounds")

    hide("relocation_bytes", 0x2800, 0x2832, "whole loop")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "whole loop")
    }


def test_hide_refuses_overlap_without_changing_the_saved_definition(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    with pytest.raises(ValueError, match="overlaps relocation_bytes"):
        hide("overlap_check", 0x2810, 0x2820, "refused")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_unhide_removes_the_saved_definition(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    unhide("relocation_bytes")

    assert shell.session.hidden.ranges == {}
    assert Hidden(tmp_path).ranges == {}


def test_unhide_refuses_an_unknown_name(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)

    with pytest.raises(ValueError, match="no hidden range missing"):
        unhide("missing")

    assert not (tmp_path / "hidden.json").exists()


@pytest.mark.parametrize("command", ["hide", "unhide"])
def test_hidden_commands_stop_without_a_dossier(
    command: str, no_dossier: None
) -> None:
    with pytest.raises(RuntimeError, match="use_dossier"):
        if command == "hide":
            hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
        else:
            unhide("relocation_bytes")


def test_switching_dossiers_does_not_carry_hidden_ranges_across(
    tmp_path: Path, no_dossier: None
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    use_dossier(first)
    hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    use_dossier(second)

    assert shell.session.hidden.ranges == {}
    assert not (second / "hidden.json").exists()

    hide("startup", 0x0800, 0x0803, "overwritten")
    assert Hidden(first).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }
    assert Hidden(second).ranges == {
        "startup": HiddenRange(0x0800, 0x0803, "overwritten")
    }

    use_dossier(first)

    assert shell.session.hidden.ranges == Hidden(first).ranges


def test_hidden_commands_leave_annotations_untouched(
    tmp_path: Path, no_dossier: None
) -> None:
    use_dossier(tmp_path)
    annotations_path = tmp_path / "annotations.json"
    before = annotations_path.read_text(encoding="utf-8")

    hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    unhide("relocation_bytes")

    assert annotations_path.read_text(encoding="utf-8") == before
