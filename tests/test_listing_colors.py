"""Tests for listing location colors and plain clipboard text."""

from pathlib import Path

import pytest
from IPython.lib.pretty import pretty

from papple2.workbench import shell
from papple2.workbench.colors import Colors
from papple2.workbench.listing_editor import ListingRow
from papple2.workbench.shell import Text, listing, print_listing


ROWS = [
    ListingRow(
        0x6000, "|   ", "a9 00", "main", "LDA #$00", "clear"
    ),
    ListingRow(
        0x6002, "+-- ", "8d 10 00", "", "STA $0010", ""
    ),
    ListingRow(
        None, "|   ", "", "", "... 6005-6006 hidden ...", ""
    ),
    ListingRow(
        0x6006, "+-> ", "60", "", "RTS", "done"
    ),
]


@pytest.fixture
def colored_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Colors:
    """Supply fixed rows, leaving run analysis outside these tests."""
    store = Colors(tmp_path)
    store.color("first", 0x6000, 0x6002, "blue")
    monkeypatch.setattr(shell, "dossier_folder", tmp_path)
    monkeypatch.setattr(shell, "color_store", store)

    def current_rows(
        start: int | str, end: int | str | None = None
    ) -> list[ListingRow]:
        return ROWS

    monkeypatch.setattr(shell, "current_listing_rows", current_rows)
    return store


def test_plain_print_listing_keeps_its_existing_layout(capsys) -> None:
    print_listing(ROWS)

    assert capsys.readouterr().out.splitlines() == [
        "|   6000  a9 00     main  LDA #$00  ; clear",
        "+-- 6002  8d 10 00        STA $0010",
        "|   ... 6005-6006 hidden ...",
        "+-> 6006  60              RTS       ; done",
    ]


def test_location_color_covers_code_but_not_gutter_or_comment(capsys) -> None:
    print_listing(
        ROWS, color_of=lambda address: "blue" if address == 0x6000 else None
    )

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == (
        "|   \x1b[34m6000  a9 00     main  LDA #$00\x1b[0m  ; clear"
    )
    assert "\x1b" not in lines[1]
    assert "\x1b" not in lines[2]
    assert "\x1b" not in lines[3]


def test_alignment_padding_stays_before_the_uncolored_comment(capsys) -> None:
    print_listing(ROWS, color_of=lambda address: "red")

    lines = capsys.readouterr().out.splitlines()
    assert lines[3] == (
        "+-> \x1b[31m6006  60              RTS\x1b[0m       ; done"
    )


def test_byte_contents_receive_location_color(capsys) -> None:
    rows = [
        ListingRow(0x6000, "", "", "", ".byte a9 00 60", "")
    ]

    print_listing(rows, color_of=lambda address: "cyan")

    assert capsys.readouterr().out == (
        "\x1b[36m6000            .byte a9 00 60\x1b[0m\n"
    )


def test_listing_returns_plain_text_but_ipython_shows_color(
    colored_listing: Colors, capsys,
) -> None:
    shown = listing(0x6000, 0x6007)
    print_listing(ROWS)

    assert isinstance(shown, Text)
    assert str(shown) == capsys.readouterr().out.rstrip("\n")
    assert "\x1b" not in str(shown)
    assert "\x1b[34m" in pretty(shown)
    assert shown.splitlines()[0].startswith("|   6000")


def test_the_clipboard_receives_plain_listing_text(
    colored_listing: Colors, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied: list[str] = []

    def pbcopy(
        command: list[str], input: str, text: bool, check: bool
    ) -> None:
        assert command == ["pbcopy"]
        copied.append(input)

    monkeypatch.setattr(shell.subprocess, "run", pbcopy)
    shown = listing(0x6000, 0x6007)

    shell.clip(shown)

    assert copied == [str(shown)]
    assert "\x1b" not in copied[0]


def test_listing_reloads_colors_changed_in_another_session(
    colored_listing: Colors, tmp_path: Path,
) -> None:
    Colors(tmp_path).color("second", 0x6002, 0x6005, "red")

    shown = listing(0x6000, 0x6007)

    assert "\x1b[31m6002" in pretty(shown)


def test_listing_without_a_color_store_displays_plain_text(
    colored_listing: Colors, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shell, "color_store", None)

    shown = listing(0x6000, 0x6007)

    assert pretty(shown) == str(shown)


def test_existing_text_objects_keep_their_plain_display() -> None:
    shown = Text("6000  RTS")

    assert pretty(shown) == "6000  RTS"
    assert repr(shown) == "6000  RTS"
