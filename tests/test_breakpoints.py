"""Breakpoints: Emulator.add_breakpoint() puts a breakpoint's should_break
method into the breakpoint list, and run() asks every breakpoint before
each instruction, before the traps.

Each run() here also gets until=after_instructions(10), as a safety net: if
a breakpoint never fires, the run ends there instead of hanging the test."""

import pytest

from papple2.core.emulator import Emulator
from papple2.debug.stop_conditions import after_instructions, break_at

NOP = 0xEA


class AskedAt:
    """A breakpoint that remembers every PC it was asked about, and stops at
    `address`."""

    def __init__(self, address: int) -> None:
        self.address = address
        self.asked: list[int] = []

    def should_break(self, pc: int) -> bool:
        self.asked.append(pc)
        return pc == self.address


@pytest.fixture
def emulator() -> Emulator:
    # four NOPs at $1000-$1003, PC at $1000
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(0x1000, [NOP] * 4)
    emulator.cpu.PC = 0x1000
    return emulator


def test_break_at_stops_before_the_instruction(emulator: Emulator) -> None:
    emulator.add_breakpoint(break_at(0x1002))

    emulator.run(until=after_instructions(10))

    # the NOPs at $1000 and $1001 ran, the one at $1002 did not
    assert emulator.cpu.PC == 0x1002
    assert emulator.instructions == 2


def test_a_breakpoint_stops_before_the_trap_at_its_address(emulator: Emulator) -> None:
    trap_calls: list[int] = []

    def trap(emu: Emulator) -> bool:
        trap_calls.append(emu.cpu.PC)
        return True

    emulator.add_trap(0x1002, trap)
    emulator.add_breakpoint(break_at(0x1002))

    emulator.run(until=after_instructions(10))

    assert emulator.cpu.PC == 0x1002
    assert trap_calls == []


def test_every_breakpoint_is_asked(emulator: Emulator) -> None:
    first = AskedAt(0x1001)
    second = AskedAt(0x1001)
    emulator.add_breakpoint(first)
    emulator.add_breakpoint(second)

    emulator.run(until=after_instructions(10))

    # the second was asked at $1001 too, although the first already said stop
    assert first.asked == [0x1000, 0x1001]
    assert second.asked == [0x1000, 0x1001]
    assert emulator.cpu.PC == 0x1001
