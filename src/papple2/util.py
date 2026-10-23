#!/usr/bin/env python

"""Small helpers: hex formatting, Apple II ASCII, and data_dir from
papple2.toml."""

import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path

def chunks[T](l: list[T], n: int) -> Iterator[list[T]]:
    """Yield successive n-sized chunks from l."""
    # https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    for i in range(0, len(l), n):
        yield l[i:i + n]

def signed(x: int) -> int:
    if x > 0x7F:
        x -= 0x100
    return x


def hexaddr(address: int | None, show_dollar: bool = True, lower: bool = True) -> str:
    res = "-" if address is None else ("$" if show_dollar else "") + hex(address)[2:].zfill(4)
    return res.lower() if lower else res.upper()


def hexbyte(byte: int | None, show_dollar: bool = False, lower: bool = True) -> str:
    res = "-" if byte is None else ("$" if show_dollar else "") + hex(byte)[2:].zfill(2)
    return res if lower else res.upper()

def hexbytes(values: Iterable[int]) -> list[str]:
    return list(map(lambda b: hexbyte(b), values))

def Ascii2Apple2Ascii(char: str | int) -> int:
    if isinstance(char, str): char = ord(char)
    return 0x80 + (char & 0x7F)

def Apple2Ascii2Ascii(char: int) -> int:
    return char & 0x7F

def load_data_dir() -> str:
    """Return data_dir from papple2.toml, or the project default "data".

    papple2.toml is read relative to the current working directory -- the
    repo root, when run via make.
    """
    config_path = Path("papple2.toml")
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}
    return config.get("data_dir", "data")
