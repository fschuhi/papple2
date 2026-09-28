#!/usr/bin/env python3

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from papple2.core.emulator import Emulator


class KeyScript:
    """Press a scripted sequence of keys at specific instruction counts.

    `KeyScript` is driven by `emulator.instructions`, not by cycles, so it
    works with any program: assemble a small test program, add a
    `KeyScript`, and press keys from code instead of a pygame window.

    Example:
        keys = KeyScript([(300, 'A'), (500, 0x0d)])
        emulator.add_checkpoint(keys.press_keys)
    """

    def __init__( self, key_schedule: Iterable[tuple[int, str | int]] ) -> None:
        # key_schedule: list of (instruction_count, ascii_code) pairs, in order
        self.key_schedule = list( key_schedule )

    def press_keys( self, emulator: "Emulator" ) -> tuple[bool, bool]:  # (active, execute)
        execute = True

        if self.key_schedule:
            instruction_count, ascii_code = self.key_schedule[0]
            if emulator.instructions >= instruction_count:
                emulator.press_key( ascii_code )
                del self.key_schedule[0]

        active = bool( self.key_schedule )
        return active, execute
