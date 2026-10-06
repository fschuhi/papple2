#!/usr/bin/env python3

from collections.abc import Callable, Iterable
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

        # One hook list per kind of access, called after the access, in list
        # order. A read hook gets (address, value), a write hook gets
        # (address, value, old_value). See docs/instrumentation-design.md,
        # section 3.
        self.after_read_opcode: list[Callable[[int, int], None]] = []
        self.after_read_operand: list[Callable[[int, int], None]] = []
        self.after_read_pointer: list[Callable[[int, int], None]] = []
        self.after_read_data: list[Callable[[int, int], None]] = []
        self.after_read_immediate: list[Callable[[int, int], None]] = []
        self.after_read_stack: list[Callable[[int, int], None]] = []
        self.after_read_vector: list[Callable[[int, int], None]] = []
        self.after_write_data: list[Callable[[int, int, int], None]] = []
        self.after_write_stack: list[Callable[[int, int, int], None]] = []

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
            or 0x2000 <= address < 0x6000
        ):
            if self.use_apple_display:
                self.apple2.display.update(address, value)

    # The CPU reads and writes through these methods, one per kind of access.
    # The name says why the CPU accesses a byte, not where the byte is:
    # LDA $0100,X touches the stack page, but it is a data read. See
    # docs/instrumentation-design.md, section 3. Each one passes the access on
    # to read_byte or write_byte, then calls the hooks in its own list. The
    # list is checked before the loop, so an empty list costs one truth test.

    def read_opcode(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_opcode:
            for hook in self.after_read_opcode:
                hook(address, value)
        return value

    def read_operand(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_operand:
            for hook in self.after_read_operand:
                hook(address, value)
        return value

    def read_pointer(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_pointer:
            for hook in self.after_read_pointer:
                hook(address, value)
        return value

    def read_data(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_data:
            for hook in self.after_read_data:
                hook(address, value)
        return value

    # the operand of an immediate instruction (the $42 in LDA #$42): the
    # operation reads it where it would otherwise read data, but the byte
    # is part of the instruction, so it gets a kind of its own
    def read_immediate(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_immediate:
            for hook in self.after_read_immediate:
                hook(address, value)
        return value

    def read_stack(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_stack:
            for hook in self.after_read_stack:
                hook(address, value)
        return value

    def read_vector(self, address: int) -> int:
        value = self.read_byte(address)
        if self.after_read_vector:
            for hook in self.after_read_vector:
                hook(address, value)
        return value

    def write_data(self, address: int, value: int) -> None:
        if self.after_write_data:
            # the old value straight from the memory list: going through
            # read_byte would flip a soft switch at $C0xx
            old_value = self._mem[address]
            self.write_byte(address, value)
            for hook in self.after_write_data:
                hook(address, value, old_value)
        else:
            self.write_byte(address, value)

    def write_stack(self, address: int, value: int) -> None:
        if self.after_write_stack:
            # the old value straight from the memory list: going through
            # read_byte would flip a soft switch at $C0xx
            old_value = self._mem[address]
            self.write_byte(address, value)
            for hook in self.after_write_stack:
                hook(address, value, old_value)
        else:
            self.write_byte(address, value)

    # 16-bit reads, low byte first, as two reads of the same kind, so every
    # byte is still seen on its own.

    def read_operand_word(self, address: int) -> int:
        return self.read_operand(address) + (self.read_operand(address + 1) << 8)

    def read_pointer_word(self, address: int) -> int:
        # the 6502's page wrap: a pointer at $xxFF takes its high byte from
        # $xx00, not from the next page
        if address % 0x100 == 0xFF:
            return self.read_pointer(address) + (self.read_pointer(address & 0xFF00) << 8)
        return self.read_pointer(address) + (self.read_pointer(address + 1) << 8)

    def read_vector_word(self, address: int) -> int:
        return self.read_vector(address) + (self.read_vector(address + 1) << 8)
