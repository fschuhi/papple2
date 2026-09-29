# Ready-made `until` conditions for Emulator.run(). They live outside core:
# the core only knows the shape of a condition (the type Until), not which
# conditions an experiment or a test brings along.

from papple2.core.emulator import Emulator, Until


def after_instructions(n: int) -> Until:
    def until(emulator: Emulator) -> bool:
        return emulator.instructions >= n
    return until


def at_address(address: int) -> Until:
    def until(emulator: Emulator) -> bool:
        return emulator.cpu.PC == address
    return until
