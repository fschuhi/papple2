"""
Boots the real Robotron binary with the pygame window open -- the
with-window path the headless test suite structurally can't exercise (see
README.md's "Testing strategy"). Not part of `make test`; run it with
`make boot-robotron`, or directly from the repo root:

    python scripts/boot_robotron.py

ROBOTRON.BIN itself isn't distributed with papple2 (still under copyright).
Point papple2.toml's data_dir at wherever your own copy lives -- see
README.md's "Data files" for how to get one.
"""

import sys
import tomllib
from pathlib import Path

from papple2.core.emulator import Emulator


def load_data_dir() -> str:
    # papple2.toml is read relative to the current working directory
    # (the repo root, when run via `make boot-robotron`).
    config_path = Path("papple2.toml")
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}
    return config.get("data_dir", "data")


def main() -> None:
    data_dir = load_data_dir()
    rom_path = Path(data_dir) / "bin" / "ROBOTRON.BIN"

    if not rom_path.exists():
        sys.exit(
            f"{rom_path} not found -- ROBOTRON.BIN isn't distributed with "
            f"papple2, see README.md for how to get a copy and point "
            f"papple2.toml's data_dir at it"
        )

    emulator = Emulator(no_display=False, data_dir=data_dir)
    emulator.load_image(0x2dfd, str(rom_path))

    # No `until` -- this only returns once the window is closed. Ctrl-X
    # pauses and resumes execution, it doesn't end the run. Nothing to
    # assert here: the point is a human watching the window, not a pass/fail
    # check the headless suite could already do.
    emulator.run()


if __name__ == "__main__":
    main()
