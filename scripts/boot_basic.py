"""
Manual smoke run for Apple II text mode.

Run with:

    make boot-basic

Expected interaction:

1. The pygame window opens.
2. The Apple II monitor prompt appears.
3. Press `Ctrl-B`.
4. Integer BASIC starts and displays its prompt.
5. Optionally enter a small Integer BASIC program, for example:

       10 PRINT 2+2
       RUN

6. Confirm that the output appears in the text display.
7. Close the window to end the run.

This script deliberately has no automated check of rendered pixels. Its
purpose is to exercise the complete windowed path: ROM reset, text-mode
switches, keyboard input, memory writes to the text page, character rendering,
and pygame presentation.
"""

import sys
from pathlib import Path

from papple2.core.emulator import Emulator
from papple2.util import load_data_dir


def main() -> None:
    data_dir = load_data_dir()
    rom_path = Path(data_dir) / "bin" / "A2ROM.BIN"

    if not rom_path.exists():
        sys.exit(
            f"{rom_path} not found -- A2ROM.BIN is required for this manual "
            "run; configure its location with papple2.toml"
        )

    emulator = Emulator(no_display=False, data_dir=data_dir)

    # The ROM is loaded by Apple2.__init__. The reset vector at $FFFC/$FFFD
    # determines the first address executed, which should enter the monitor.
    emulator.cpu.reset()

    # No `until` condition: the run ends when the user closes the window.
    emulator.run()


if __name__ == "__main__":
    main()
