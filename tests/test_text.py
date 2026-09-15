"""
Manual smoke test for Apple II text mode.

Run with:

    make run-text

Expected interaction:

1. The pygame window opens.
2. The Apple II monitor prompt appears.
3. Press `B`.
4. Integer BASIC starts and displays its prompt.
5. Optionally enter a small Integer BASIC program, for example:

       10 PRINT 2+2
       RUN

6. Confirm that the output appears in the text display.
7. Close the window to end the test.

This test deliberately has no automated assertion about rendered pixels. Its
purpose is to exercise the complete windowed path: ROM reset, text-mode
switches, keyboard input, memory writes to the text page, character rendering,
and pygame presentation.
"""

from pathlib import Path
import tomllib

import pytest

from papple2.core.emulator import Emulator


def load_data_dir() -> str:
    """Return the configured data directory, or the project default."""
    config_path = Path("papple2.toml")

    if config_path.exists():
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)
    else:
        config = {}

    return config.get("data_dir", "data")


@pytest.mark.manual
def test_integer_basic_starts_in_text_mode() -> None:
    data_dir = load_data_dir()
    rom_path = Path(data_dir) / "bin" / "A2ROM.BIN"

    if not rom_path.exists():
        pytest.skip(
            f"{rom_path} not found -- A2ROM.BIN is required for this manual "
            "test; configure its location with papple2.toml"
        )

    emulator = Emulator(no_display=False, data_dir=data_dir)

    # The ROM is loaded by Apple2.__init__. The reset vector at $FFFC/$FFFD
    # determines the first address executed, which should enter the monitor.
    emulator.cpu.reset()

    # No `until` condition: the test ends when the user closes the window.
    emulator.run()
