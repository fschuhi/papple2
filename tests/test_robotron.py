"""
Manual test: boots the real Robotron binary with the pygame window open --
the with-window path the headless suite structurally can't exercise (see
README.md's "Testing strategy"). Not part of `make test`; run it
deliberately with `make run`, or directly:

    pytest tests/test_robotron.py -m manual -s -v

ROBOTRON.BIN itself isn't distributed with papple2 (still under copyright).
Point papple2.toml's data_dir at wherever your own copy lives -- see
README.md for how to get one.
"""

import tomllib
from pathlib import Path

import pytest
from papple2.core.emulator import Emulator


def load_data_dir() -> str:
    # Same convention as examples/Robotron/Robotron.py's load_config():
    # papple2.toml is read relative to the current working directory
    # (the repo root, when run via `make run` or plain `pytest`).
    config_path = Path("papple2.toml")
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}
    return config.get("data_dir", "data")


@pytest.mark.manual
def test_robotron_boots_and_responds_to_ctrlx():
    data_dir = load_data_dir()
    rom_path = Path(data_dir) / "bin" / "ROBOTRON.BIN"

    if not rom_path.exists():
        pytest.skip(
            f"{rom_path} not found -- ROBOTRON.BIN isn't distributed with "
            f"papple2, see README.md for how to get a copy and point "
            f"papple2.toml's data_dir at it"
        )

    emulator = Emulator(no_display=False, data_dir=data_dir)
    emulator.load_image(0x2dfd, str(rom_path))

    # No `until` -- this only returns once the window is closed or Ctrl-X'd
    # to a halt, same as `make run` did before. Nothing to assert here: the
    # point of this test is a human watching the window, not a pass/fail
    # check the headless suite could already do.
    emulator.run()
