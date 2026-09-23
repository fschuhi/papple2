from pathlib import Path

import pytest

from papple2.util import load_data_dir


# load_data_dir() reads papple2.toml from the current working directory, so
# each test switches into its own empty temporary folder (monkeypatch.chdir);
# the repo's real papple2.toml never takes part.


def test_load_data_dir_reads_data_dir_from_papple2_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "papple2.toml").write_text('data_dir = "/somewhere/else"\n')
    monkeypatch.chdir(tmp_path)

    assert load_data_dir() == "/somewhere/else"


def test_load_data_dir_defaults_to_data_without_papple2_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert load_data_dir() == "data"
