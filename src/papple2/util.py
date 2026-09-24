#!/usr/bin/env python

import itertools
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


def pairwise[T](iterable: Iterable[T]) -> Iterator[tuple[T, T]]:
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def hex2int(text: str) -> int:
    text = text if text[:1] != "$" else text[1:]
    return int(text, 16)


def hexaddr(address: int | None, show_dollar: bool = True, lower: bool = True) -> str:
    res = "-" if address is None else ("$" if show_dollar else "") + hex(address)[2:].zfill(4)
    return res.lower() if lower else res.upper()


def hexbyte(byte: int | None, lower: bool = True) -> str:
    res = "-" if byte is None else hex(byte)[2:].zfill(2)
    return res if lower else res.upper()

def hexbytes(values: Iterable[int]) -> list[str]:
    return list(map(lambda b: hexbyte(b), values))

def dot_RGB( R: int, G: int, B: int ) -> str:
    # https://www.graphviz.org/doc/info/attrs.html#k:color
    return '"#%02x%02x%02x"' % (R, G, B)

def Ascii2Apple2Ascii(char: str | int) -> int:
    if isinstance(char, str): char = ord(char)
    return 0x80 + (char & 0x7F)

def Apple2Ascii2Ascii(char: int) -> int:
    return char & 0x7F

def lerp_rgb(
    a: tuple[float, float, float], b: tuple[float, float, float], t: float
) -> tuple[float, float, float]:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )

def load_data_dir() -> str:
    """Return data_dir from papple2.toml, or the project default "data".

    papple2.toml is read relative to the current working directory -- the
    repo root, when run via make. See README.md's "Settled decisions".
    """
    config_path = Path("papple2.toml")
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}
    return config.get("data_dir", "data")
