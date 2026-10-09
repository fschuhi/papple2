"""Tests for the dossier's named hidden ranges and their persistence."""

import json
from pathlib import Path

import pytest

from papple2.workbench.hidden import Hidden, HiddenRange


def read_file(folder: Path) -> dict:
    return json.loads((folder / "hidden.json").read_text(encoding="utf-8"))


def test_a_new_store_has_no_ranges_and_writes_nothing(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path / "lode_runner")

    assert hidden.ranges == {}
    assert not (tmp_path / "lode_runner").exists()


def test_hide_writes_the_definition_at_once(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)

    hidden.hide(
        "relocation_bytes", 0x2800, 0x2832, "overwritten after it ran"
    )

    assert hidden.ranges == {
        "relocation_bytes": HiddenRange(
            0x2800, 0x2832, "overwritten after it ran"
        )
    }
    assert read_file(tmp_path) == {
        "relocation_bytes": {
            "start": "2800",
            "end": "2832",
            "note": "overwritten after it ran",
        }
    }


def test_a_second_store_reads_the_saved_definitions(tmp_path: Path) -> None:
    Hidden(tmp_path).hide(
        "relocation_bytes", 0x2800, 0x2832, "overwritten"
    )

    hidden = Hidden(tmp_path)

    assert hidden.ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_reusing_a_name_replaces_its_definition(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2830, "first bounds")

    hidden.hide("relocation_bytes", 0x2800, 0x2832, "whole loop")

    assert hidden.ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "whole loop")
    }
    assert Hidden(tmp_path).ranges == hidden.ranges


def test_repeating_a_definition_leaves_the_file_untouched(
    tmp_path: Path,
) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    # Different formatting exposes an unnecessary save.
    compact = json.dumps(read_file(tmp_path))
    (tmp_path / "hidden.json").write_text(compact, encoding="utf-8")

    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    assert (tmp_path / "hidden.json").read_text(encoding="utf-8") == compact


def test_repeating_a_definition_does_not_recreate_a_missing_file(
    tmp_path: Path,
) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    (tmp_path / "hidden.json").unlink()

    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    assert not (tmp_path / "hidden.json").exists()


@pytest.mark.parametrize("name", ["", "   "])
def test_an_empty_name_is_refused(tmp_path: Path, name: str) -> None:
    hidden = Hidden(tmp_path)

    with pytest.raises(ValueError, match="needs a name"):
        hidden.hide(name, 0x2800, 0x2832, "")

    assert hidden.ranges == {}
    assert not (tmp_path / "hidden.json").exists()


@pytest.mark.parametrize(
    "start, end",
    [
        (-1, 0x2832),
        (0x2800, 0x2800),
        (0x2832, 0x2800),
        (0xFFFF, 0x10001),
    ],
)
def test_invalid_bounds_are_refused(
    tmp_path: Path, start: int, end: int
) -> None:
    hidden = Hidden(tmp_path)

    with pytest.raises(ValueError, match="start < end"):
        hidden.hide("relocation_bytes", start, end, "")

    assert hidden.ranges == {}
    assert not (tmp_path / "hidden.json").exists()


def test_the_last_byte_of_memory_can_be_hidden(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)

    hidden.hide("last_byte", 0xFFFF, 0x10000, "")

    assert Hidden(tmp_path).ranges == {
        "last_byte": HiddenRange(0xFFFF, 0x10000, "")
    }
    assert read_file(tmp_path)["last_byte"]["end"] == "10000"


def test_adjacent_ranges_do_not_overlap(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("middle", 0x2800, 0x2832, "")

    hidden.hide("before", 0x27FF, 0x2800, "")
    hidden.hide("after", 0x2832, 0x2833, "")

    assert Hidden(tmp_path).ranges == hidden.ranges
    assert len(hidden.ranges) == 3


@pytest.mark.parametrize(
    "start, end",
    [
        (0x27FF, 0x2801),  # overlaps the beginning
        (0x2831, 0x2833),  # overlaps the end
        (0x2801, 0x2831),  # lies inside
        (0x27FF, 0x2833),  # contains the existing range
        (0x2800, 0x2832),  # identical bounds under another name
    ],
)
def test_overlapping_ranges_are_refused_without_changing_the_file(
    tmp_path: Path, start: int, end: int
) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    before = (tmp_path / "hidden.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="overlaps relocation_bytes"):
        hidden.hide("other", start, end, "")

    assert hidden.ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }
    assert (tmp_path / "hidden.json").read_text(encoding="utf-8") == before


def test_a_replacement_cannot_overlap_another_range(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("first", 0x2800, 0x2810, "")
    hidden.hide("second", 0x2820, 0x2832, "")
    before = dict(hidden.ranges)

    with pytest.raises(ValueError, match="overlaps second"):
        hidden.hide("first", 0x2800, 0x2821, "expanded")

    assert hidden.ranges == before
    assert Hidden(tmp_path).ranges == before


def test_unhide_removes_the_definition_at_once(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    hidden.unhide("relocation_bytes")

    assert hidden.ranges == {}
    assert read_file(tmp_path) == {}


def test_unhide_refuses_an_unknown_name_without_writing(
    tmp_path: Path,
) -> None:
    hidden = Hidden(tmp_path)

    with pytest.raises(ValueError, match="no hidden range relocation_bytes"):
        hidden.unhide("relocation_bytes")

    assert not (tmp_path / "hidden.json").exists()


def test_definitions_are_saved_in_address_order(tmp_path: Path) -> None:
    hidden = Hidden(tmp_path)
    hidden.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")
    hidden.hide("startup", 0x0800, 0x0803, "overwritten")

    assert list(read_file(tmp_path)) == ["startup", "relocation_bytes"]


def test_a_change_keeps_a_definition_from_another_session(
    tmp_path: Path,
) -> None:
    first = Hidden(tmp_path)
    second = Hidden(tmp_path)

    first.hide("startup", 0x0800, 0x0803, "overwritten")
    second.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    assert Hidden(tmp_path).ranges == {
        "startup": HiddenRange(0x0800, 0x0803, "overwritten"),
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten"),
    }
    assert second.ranges == Hidden(tmp_path).ranges


def test_overlap_with_a_definition_from_another_session_is_refused(
    tmp_path: Path,
) -> None:
    first = Hidden(tmp_path)
    second = Hidden(tmp_path)
    first.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    with pytest.raises(ValueError, match="overlaps relocation_bytes"):
        second.hide("other", 0x2810, 0x2820, "")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_unhide_keeps_other_definitions_from_another_session(
    tmp_path: Path,
) -> None:
    first = Hidden(tmp_path)
    first.hide("startup", 0x0800, 0x0803, "overwritten")
    second = Hidden(tmp_path)
    second.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    first.unhide("startup")

    assert Hidden(tmp_path).ranges == {
        "relocation_bytes": HiddenRange(0x2800, 0x2832, "overwritten")
    }


def test_reload_sees_a_change_from_another_session(tmp_path: Path) -> None:
    first = Hidden(tmp_path)
    second = Hidden(tmp_path)
    second.hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    first.reload()

    assert first.ranges == second.ranges


def test_hiding_does_not_touch_annotations(tmp_path: Path) -> None:
    path = tmp_path / "annotations.json"
    original = '{"labels": {"2800": "relocation_loop"}, "comments": {}}\n'
    path.write_text(original, encoding="utf-8")

    Hidden(tmp_path).hide("relocation_bytes", 0x2800, 0x2832, "overwritten")

    assert path.read_text(encoding="utf-8") == original
