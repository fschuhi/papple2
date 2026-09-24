#!/usr/bin/env python3

from collections.abc import Iterable
from pickle import Pickler, Unpickler
from typing import TYPE_CHECKING

from papple2.util import hexaddr

if TYPE_CHECKING:
    from papple2.core.apple import Apple2


class Memory:
    def __init__(self, apple2: "Apple2 | None" = None) -> None:
        self.apple2 = apple2
        self.use_apple_softswitches = apple2 is not None
        self.use_apple_display = apple2 is not None
        self._mem = [0x00] * 0x10000

    def load_image(self, first_address: int, fn: str) -> None:
        with open(fn, "rb") as f:
            content = f.read()
            # A slice assignment past the end would silently grow _mem beyond
            # 64K instead of failing, so refuse images that do not fit.
            if first_address + len(content) > len(self._mem):
                raise ValueError(f"image {fn} does not fit at {hexaddr(first_address)}")
            self._mem[first_address : first_address + len(content)] = content

    def save_image(self, first_address: int, last_address: int, fn: str) -> None:
        import struct

        mem = self._mem[first_address : last_address + 1]
        bytes_data = struct.pack("{}B".format(len(mem)), *mem)

        with open(fn, "wb") as f:
            f.write(bytes_data)

    def load_test_data(self, address: int, data: Iterable[int]) -> None:
        for offset, datum in enumerate(data):
            self._mem[address + offset] = datum

    def pickle(self, pickler: Pickler) -> None:
        pickler.dump(self._mem)
        pickler.dump(self.use_apple_display)
        pickler.dump(self.use_apple_softswitches)

    def unpickle(self, unpickler: Unpickler) -> None:
        self._mem = unpickler.load()
        self.use_apple_display = unpickler.load()
        self.use_apple_softswitches = unpickler.load()

    def read_byte(self, address: int) -> int:
        # Access to the $C0xx pages with soft switches might be masked by
        # the soft-switch mechanism.
        if 0xC000 <= address <= 0xCFFF:
            return (
                self.apple2.softswitches.read_byte(address)
                if self.use_apple_softswitches
                else self._mem[address]
            )

        return self._mem[address]

    def read_word(self, address: int) -> int:
        return self.read_byte(address) + (self.read_byte(address + 1) << 8)

    def read_word_bug(self, address: int) -> int:
        if address % 0x100 == 0xFF:
            return self.read_byte(address) + (self.read_byte(address & 0xFF00) << 8)
        else:
            return self.read_word(address)

    def write_byte(self, address: int, value: int) -> None:
        # We do not restrict access to the soft-switch page $C0.
        # Note that we will never be able to access a value on $C0 if it is
        # masked by the soft switches.
        self._mem[address] = value

        # Special handling for Apple II hardware.
        if 0xC000 <= address <= 0xCFFF:
            if self.use_apple_softswitches:
                self.apple2.softswitches.write_byte(address, value)

        elif (
            0x0400 <= address < 0x0C00
            or 0x2000 <= address < 0x5FFF
        ):
            if self.use_apple_display:
                self.apple2.display.update(address, value)
