"""Tests for persistent color ranges and their shared lookup."""

import json
from pathlib import Path

import pytest

from papple2.workbench.colors import MIX_COLOR, SHADES, ColorRange, Colors


def read_file(folder: Path) -> dict:
    return json.loads((folder / "colors.json").read_text(encoding="utf-8"))


def test_opening_a_new_store_writes_nothing(tmp_path: Path) -> None:
    colors = Colors(tmp_path / "dossier")

    assert colors.ranges == {}
    assert not (tmp_path / "dossier").exists()


def test_a_definition_is_saved_at_once_and_read_by_another_store(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)

    colors.color("sprites", 0x8336, 0x8438, "blue")

    assert read_file(tmp_path) == {
        "sprites": {"start": "8336", "end": "8438", "shade": "blue"}
    }
    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }


def test_reusing_a_name_replaces_its_bounds_and_shade(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x83A7, "blue")

    colors.color("sprites", 0x8336, 0x8438, "cyan")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "cyan")
    }


def test_an_unchanged_definition_leaves_file_formatting_alone(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    compact = json.dumps(read_file(tmp_path))
    (tmp_path / "colors.json").write_text(compact, encoding="utf-8")

    colors.color("sprites", 0x8336, 0x8438, "blue")

    assert (tmp_path / "colors.json").read_text(encoding="utf-8") == compact


def test_an_unchanged_definition_does_not_recreate_a_missing_file(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    (tmp_path / "colors.json").unlink()

    colors.color("sprites", 0x8336, 0x8438, "blue")

    assert not (tmp_path / "colors.json").exists()


@pytest.mark.parametrize("name", ["", "   "])
def test_an_empty_name_is_refused(tmp_path: Path, name: str) -> None:
    colors = Colors(tmp_path)

    with pytest.raises(ValueError, match="needs a name"):
        colors.color(name, 0x8336, 0x8438, "blue")

    assert colors.ranges == {}
    assert not (tmp_path / "colors.json").exists()


@pytest.mark.parametrize(
    "start, end",
    [
        (-1, 0x0014),
        (0x0010, 0x0010),
        (0x0014, 0x0010),
        (0xFFFF, 0x10001),
    ],
)
def test_invalid_bounds_are_refused(
    tmp_path: Path, start: int, end: int
) -> None:
    colors = Colors(tmp_path)

    with pytest.raises(ValueError, match="start < end"):
        colors.color("scores", start, end, "red")

    assert colors.ranges == {}
    assert not (tmp_path / "colors.json").exists()


@pytest.mark.parametrize("shade", sorted(SHADES))
def test_each_supported_shade_can_be_saved(
    tmp_path: Path, shade: str
) -> None:
    colors = Colors(tmp_path)

    colors.color("scores", 0x0010, 0x0014, shade)

    assert Colors(tmp_path).ranges["scores"].shade == shade


def test_an_unknown_shade_is_refused_without_changing_the_file(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("scores", 0x0010, 0x0014, "red")
    before = (tmp_path / "colors.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="unknown shade"):
        colors.color("scores", 0x0010, 0x0014, "orange")

    assert colors.ranges["scores"].shade == "red"
    assert (tmp_path / "colors.json").read_text(encoding="utf-8") == before


def test_a_single_byte_range_has_half_open_bounds(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("score_byte", 0x0010, 0x0011, "red")

    assert colors.color_at(0x000F) is None
    assert colors.color_at(0x0010) == "red"
    assert colors.color_at(0x0011) is None


def test_the_last_byte_of_memory_can_be_colored(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("last_byte", 0xFFFF, 0x10000, "white")

    assert colors.color_at(0xFFFF) == "white"
    assert read_file(tmp_path)["last_byte"]["end"] == "10000"


def test_overlapping_different_shades_return_the_mix_color(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("scores", 0x0010, 0x0014, "red")
    colors.color("stats", 0x0012, 0x0016, "blue")

    assert colors.color_at(0x0011) == "red"
    assert colors.color_at(0x0012) == MIX_COLOR
    assert colors.color_at(0x0014) == "blue"
    assert len(Colors(tmp_path).ranges) == 2


def test_overlapping_equal_shades_keep_their_color(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("scores", 0x0010, 0x0014, "red")
    colors.color("stats", 0x0012, 0x0016, "red")

    assert colors.color_at(0x0012) == "red"


def test_adjacent_ranges_do_not_mix(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("scores", 0x0010, 0x0014, "red")
    colors.color("stats", 0x0014, 0x0018, "blue")

    assert colors.color_at(0x0013) == "red"
    assert colors.color_at(0x0014) == "blue"


def test_a_whole_range_gets_the_color_of_a_containing_definition(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")

    assert colors.color_for_range(0x8336, 0x8438) == "blue"
    assert colors.color_for_range(0x8336, 0x83A7) == "blue"
    assert colors.color_for_range(0x8350, 0x8376) == "blue"


def test_partial_coverage_does_not_color_the_whole_range(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")

    assert colors.color_for_range(0x8335, 0x8438) is None
    assert colors.color_for_range(0x8336, 0x8439) is None
    assert colors.color_for_range(0x8438, 0x8455) is None


def test_different_containing_shades_mix_for_a_whole_range(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    colors.color("drawing", 0x8300, 0x8500, "green")

    assert colors.color_for_range(0x8336, 0x83A7) == MIX_COLOR


def test_partial_overlap_does_not_override_a_containing_definition(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    colors.color("detail", 0x8350, 0x8376, "red")

    assert colors.color_at(0x8352) == MIX_COLOR
    assert colors.color_for_range(0x8336, 0x83A7) == "blue"


def test_equal_containing_shades_keep_their_color(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    colors.color("drawing", 0x8300, 0x8500, "blue")

    assert colors.color_for_range(0x8336, 0x83A7) == "blue"


def test_uncolor_removes_the_saved_definition(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")

    colors.uncolor("sprites")

    assert colors.ranges == {}
    assert read_file(tmp_path) == {}
    assert colors.color_at(0x8336) is None


def test_uncolor_refuses_an_unknown_name_without_writing(
    tmp_path: Path,
) -> None:
    colors = Colors(tmp_path)

    with pytest.raises(ValueError, match="no color range missing"):
        colors.uncolor("missing")

    assert not (tmp_path / "colors.json").exists()


def test_definitions_are_saved_in_address_order(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("sprites", 0x8336, 0x8438, "blue")
    colors.color("scores", 0x0010, 0x0014, "red")

    assert list(read_file(tmp_path)) == ["scores", "sprites"]


def test_a_change_preserves_another_sessions_definition(
    tmp_path: Path,
) -> None:
    first = Colors(tmp_path)
    second = Colors(tmp_path)

    first.color("scores", 0x0010, 0x0014, "red")
    second.color("sprites", 0x8336, 0x8438, "blue")

    assert Colors(tmp_path).ranges == {
        "scores": ColorRange(0x0010, 0x0014, "red"),
        "sprites": ColorRange(0x8336, 0x8438, "blue"),
    }
    assert second.ranges == Colors(tmp_path).ranges


def test_removal_preserves_another_sessions_definition(
    tmp_path: Path,
) -> None:
    first = Colors(tmp_path)
    first.color("scores", 0x0010, 0x0014, "red")
    second = Colors(tmp_path)
    second.color("sprites", 0x8336, 0x8438, "blue")

    first.uncolor("scores")

    assert Colors(tmp_path).ranges == {
        "sprites": ColorRange(0x8336, 0x8438, "blue")
    }


def test_reload_updates_the_lookup_from_another_session(
    tmp_path: Path,
) -> None:
    first = Colors(tmp_path)
    second = Colors(tmp_path)
    second.color("scores", 0x0010, 0x0014, "red")
    assert first.color_at(0x0010) is None

    first.reload()

    assert first.color_at(0x0010) == "red"


def test_coloring_leaves_other_dossier_files_untouched(
    tmp_path: Path,
) -> None:
    originals = {
        "annotations.json": '{"labels": {}, "comments": {}}\n',
        "hidden.json": "{}\n",
    }
    for name, text in originals.items():
        (tmp_path / name).write_text(text, encoding="utf-8")

    Colors(tmp_path).color("sprites", 0x8336, 0x8438, "blue")

    for name, text in originals.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == text


def test_the_mix_color_is_no_shade_a_range_can_have(tmp_path: Path) -> None:
    assert MIX_COLOR not in SHADES
    assert "magenta" in SHADES

    with pytest.raises(ValueError, match="unknown shade"):
        Colors(tmp_path).color("scores", 0x0010, 0x0014, MIX_COLOR)


# color_of_bytes(): the color of a memory map's cell. Lode Runner's dossier
# as the example: green 1c9a-1d26, cyan 1d26-1db2.


@pytest.fixture
def tables(tmp_path: Path) -> Colors:
    colors = Colors(tmp_path)
    colors.color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")
    colors.color("halfscr_col_shift", 0x1D26, 0x1DB2, "cyan")
    return colors


def test_bytes_without_a_definition_have_no_color(tables: Colors) -> None:
    assert tables.color_of_bytes(0x1B00, 0x1C00) is None


def test_partial_coverage_colors_the_bytes(tables: Colors) -> None:
    # Green covers only 1c9a-1cff of the page.
    assert tables.color_of_bytes(0x1C00, 0x1D00) == "green"
    assert tables.color_for_range(0x1C00, 0x1D00) is None


def test_different_shades_in_separate_bytes_mix(tables: Colors) -> None:
    # Green ends at 1d26, cyan starts there: no byte has both.
    assert tables.color_of_bytes(0x1D00, 0x1E00) == MIX_COLOR
    assert tables.color_of_bytes(0x1D20, 0x1D30) == MIX_COLOR


def test_one_shade_in_part_of_the_bytes_keeps_it(tables: Colors) -> None:
    assert tables.color_of_bytes(0x1D30, 0x1D40) == "cyan"


def test_equal_shades_in_one_span_keep_their_color(tmp_path: Path) -> None:
    colors = Colors(tmp_path)
    colors.color("scores", 0x0010, 0x0014, "red")
    colors.color("stats", 0x0018, 0x001C, "red")

    assert colors.color_of_bytes(0x0000, 0x0100) == "red"


def test_spans_that_only_touch_do_not_count(tables: Colors) -> None:
    # Half-open: green ends at 1d26, so 1d26 onwards has no green byte.
    assert tables.color_of_bytes(0x1D26, 0x1D30) == "cyan"
    assert tables.color_of_bytes(0x1C90, 0x1C9A) is None
    assert tables.color_of_bytes(0x1DB2, 0x1DC0) is None


def test_the_whole_memory_is_one_span(tables: Colors) -> None:
    assert tables.color_of_bytes(0x0000, 0x10000) == MIX_COLOR


@pytest.mark.parametrize(
    "start, end",
    [(-1, 0x0010), (0x0010, 0x0010), (0x0014, 0x0010), (0xFFFF, 0x10001)],
)
def test_color_of_bytes_refuses_invalid_bounds(
    tables: Colors, start: int, end: int
) -> None:
    with pytest.raises(ValueError, match="start < end"):
        tables.color_of_bytes(start, end)
