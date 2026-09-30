# Ready-made `until` conditions for Emulator.run(), and ready-made
# breakpoints for Emulator.add_breakpoint(). They live outside core: the
# core only knows the shape of a condition (the type Until) and of a
# breakpoint (the type Breakpoint), not which ones an experiment or a test
# brings along.

from papple2.core.emulator import Emulator, Until


def after_instructions(n: int) -> Until:
    def until(emulator: Emulator) -> bool:
        return emulator.instructions >= n
    return until


def at_address(address: int) -> Until:
    def until(emulator: Emulator) -> bool:
        return emulator.cpu.PC == address
    return until


class AddressBreakpoint:
    """Stops before the instruction at `address`."""

    def __init__(self, address: int) -> None:
        self.address = address

    def should_break(self, pc: int) -> bool:
        return pc == self.address


def break_at(address: int) -> AddressBreakpoint:
    """For emulator.add_breakpoint(break_at(0xB7B5))."""
    return AddressBreakpoint(address)
