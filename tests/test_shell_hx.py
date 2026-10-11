"""Tests for hx(): hex arithmetic at the prompt, the result shown in hex."""

import pytest
from IPython.lib.pretty import pretty

from papple2.workbench import shell
from papple2.workbench.shell import Text, hx


@pytest.mark.parametrize(
    "value, shown",
    [
        (0x1D26 - 0x1C9A, "$008c"),
        (0x1C9A - 0x1D26, "-$008c"),  # a negative result keeps its sign
        (0x10000 + 0x8C, "$1008c"),  # past $ffff: all its digits
        (0, "$0000"),
        (0xC000, "$c000"),  # lowercase, as in the listings
    ],
)
def test_hx_shows_the_value_in_hex(value: int, shown: str) -> None:
    assert hx(value) == shown


def test_hx_returns_text_that_ipython_shows_without_quotes() -> None:
    shown = hx(0x8C)

    assert isinstance(shown, Text)
    assert pretty(shown) == "$008c"


def test_the_clipboard_gets_the_hex_text(monkeypatch: pytest.MonkeyPatch) -> None:
    copied: list[str] = []

    def pbcopy(command: list[str], input: str, text: bool, check: bool) -> None:
        copied.append(input)

    monkeypatch.setattr(shell.subprocess, "run", pbcopy)

    shell.clip(hx(0x1D26 - 0x1C9A))

    assert copied == ["$008c"]
