import json
from pathlib import Path

import pytest

from papple2.workbench.annotations import Annotations


def read_file(folder: Path) -> dict:
    return json.loads((folder / "annotations.json").read_text())


def test_a_new_dossier_has_no_labels_and_writes_no_file(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path / "lode_runner")

    assert annotations.labels == {}
    assert not (tmp_path / "lode_runner").exists()


def test_label_writes_the_file_at_once(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)

    annotations.label(0x6238, "LOAD_LEVEL")

    assert read_file(tmp_path)["labels"] == {"6238": "LOAD_LEVEL"}


def test_a_second_annotations_sees_the_labels(tmp_path: Path) -> None:
    # Quitting IPython and coming back: the labels come from the file.
    Annotations(tmp_path).label(0x6238, "LOAD_LEVEL")

    annotations = Annotations(tmp_path)

    assert annotations.labels == {0x6238: "LOAD_LEVEL"}


def test_labelling_an_address_again_replaces_its_label(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x627E, "COL_LOOP")

    annotations.label(0x627E, "NIBBLE_LOOP")

    assert annotations.labels == {0x627E: "NIBBLE_LOOP"}
    assert read_file(tmp_path)["labels"] == {"627e": "NIBBLE_LOOP"}


def test_label_refuses_a_text_used_at_another_address(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x6238, "LOAD_LEVEL")

    with pytest.raises(ValueError, match=r"\$6238"):
        annotations.label(0x627E, "LOAD_LEVEL")

    assert annotations.labels == {0x6238: "LOAD_LEVEL"}


def test_unlabel_removes_the_label_from_the_file(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x6238, "LOAD_LEVEL")

    annotations.unlabel(0x6238)

    assert annotations.labels == {}
    assert read_file(tmp_path)["labels"] == {}


def test_unlabel_refuses_an_address_without_a_label(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)

    with pytest.raises(ValueError, match=r"\$6238"):
        annotations.unlabel(0x6238)


def test_add_labels_skips_labelled_addresses_and_texts_in_use(
    tmp_path: Path,
) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0xC000, "KEYBOARD")
    annotations.label(0x6238, "SPKR")

    annotations.add_labels({0xC000: "KBD", 0xC030: "SPKR", 0xC010: "KBDSTRB"})

    assert annotations.labels == {
        0xC000: "KEYBOARD",  # already labelled: keeps its label
        0x6238: "SPKR",  # the text was in use: 0xC030 stays without one
        0xC010: "KBDSTRB",
    }
    assert Annotations(tmp_path).labels == annotations.labels


def test_the_file_has_both_sections_sorted_by_address(tmp_path: Path) -> None:
    annotations = Annotations(tmp_path)
    annotations.label(0x627E, "COL_LOOP")
    annotations.label(0x0300, "START")
    annotations.label(0x6238, "LOAD_LEVEL")

    text = (tmp_path / "annotations.json").read_text()

    assert text == (
        "{\n"
        '  "labels": {\n'
        '    "0300": "START",\n'
        '    "6238": "LOAD_LEVEL",\n'
        '    "627e": "COL_LOOP"\n'
        "  },\n"
        '  "comments": {}\n'
        "}\n"
    )
