"""Tests for colors in hexdump(): each hex byte in the color of its address,
the text column plain, and plain text for str() and the clipboard."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from IPython.lib.pretty import pretty

from papple2.workbench import shell
from papple2.workbench.colors import Colors
from papple2.workbench.shell import HexdumpRow, Text, hexdump, print_hexdump

# One line of memory at $1c90: "A" ($c1) at $1c9a, the start of a table.
ROW = HexdumpRow(0x1C90, [0x00] * 10 + [0xC1, 0x1C] + [0x00] * 4)
PLAIN_LINE = (
    "1c90  00 00 00 00 00 00 00 00  00 00 c1 1c 00 00 00 00"
    "  |..........A.....|"
)
GREEN = "\x1b[32m"
RESET = "\x1b[0m"


def test_without_colors_the_line_is_as_before(capsys) -> None:
    print_hexdump([ROW])

    assert capsys.readouterr().out == PLAIN_LINE + "\n"


def test_a_lookup_that_finds_nothing_changes_nothing(capsys) -> None:
    print_hexdump([ROW], color_of=lambda address: None)

    assert capsys.readouterr().out == PLAIN_LINE + "\n"


def test_each_byte_in_a_range_has_its_color(capsys) -> None:
    print_hexdump(
        [ROW], color_of=lambda address: "green" if address >= 0x1C9A else None
    )

    line = capsys.readouterr().out.rstrip("\n")
    assert line.startswith(
        "1c90  00 00 00 00 00 00 00 00  00 00 "
        f"{GREEN}c1{RESET} {GREEN}1c{RESET} {GREEN}00{RESET}"
    )
    # The spaces between the bytes stay plain.
    assert f"{RESET} {GREEN}" in line


def test_the_text_column_stays_plain(capsys) -> None:
    print_hexdump([ROW], color_of=lambda address: "green")

    line = capsys.readouterr().out.rstrip("\n")
    assert line.endswith("  |..........A.....|")
    assert "\x1b" not in line[line.index("|") :]
    assert "\x1b" not in line[:4]  # the address


@pytest.fixture
def current_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_session: None,
) -> Path:
    """A stand-in run whose memory holds ROW's bytes, and an empty dossier."""
    memory = [0x00] * 0x10000
    memory[0x1C90 : 0x1CA0] = ROW.values
    emulator = SimpleNamespace(apple2=SimpleNamespace(memory=SimpleNamespace(_mem=memory)))
    monkeypatch.setattr(shell.session, "run_emulator", emulator)
    shell.use_dossier(tmp_path)
    return tmp_path


def test_hexdump_returns_plain_text_but_ipython_shows_color(
    current_memory: Path,
) -> None:
    Colors(current_memory).color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")

    shown = hexdump(0x1C90, 0x1CA0)

    assert isinstance(shown, Text)
    assert str(shown) == PLAIN_LINE
    assert f"{GREEN}c1{RESET}" in pretty(shown)


def test_hexdump_reloads_colors_saved_in_another_session(
    current_memory: Path,
) -> None:
    assert pretty(hexdump(0x1C90, 0x1CA0)) == PLAIN_LINE

    Colors(current_memory).color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")

    assert GREEN in pretty(hexdump(0x1C90, 0x1CA0))


def test_hexdump_without_a_dossier_is_plain(
    monkeypatch: pytest.MonkeyPatch, fresh_session: None,
) -> None:
    memory = [0x00] * 0x10000
    memory[0x1C90 : 0x1CA0] = ROW.values
    emulator = SimpleNamespace(apple2=SimpleNamespace(memory=SimpleNamespace(_mem=memory)))
    monkeypatch.setattr(shell.session, "run_emulator", emulator)

    shown = hexdump(0x1C90, 0x1CA0)

    assert pretty(shown) == str(shown) == PLAIN_LINE


def test_the_clipboard_gets_plain_hexdump_text(
    current_memory: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    Colors(current_memory).color("halfscr_col_byte", 0x1C9A, 0x1D26, "green")
    copied: list[str] = []

    def pbcopy(command: list[str], input: str, text: bool, check: bool) -> None:
        copied.append(input)

    monkeypatch.setattr(shell.subprocess, "run", pbcopy)

    shell.clip(hexdump(0x1C90, 0x1CA0))

    assert copied == [PLAIN_LINE]
