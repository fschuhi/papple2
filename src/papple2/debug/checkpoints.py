#!/usr/bin/env python3

from collections.abc import Iterable
from typing import TYPE_CHECKING

from papple2.util import hexbyte, Apple2Ascii2Ascii, Ascii2Apple2Ascii

if TYPE_CHECKING:
    from papple2.core.emulator import Emulator


class RecordedKeys:
    def __init__( self ) -> None:
        self.keys = [
            (5026414, ' ', 'switch to choose controls'),
            (5347664, 0x1b, 'switch back to intro noise'),
            (5769011, 0x00, 'exit'),
        ]

    def press_keys( self, emulator: "Emulator" ) -> tuple[bool, bool]:  # (active, execute)
        active = True
        execute = True

        (cycles, key, comment) = self.keys[0]
        if emulator.cpu.cycles < cycles:
            pass
        else:
            del self.keys[0]
            if key == 0x00:
                print( "signal break at breakpoint" )
                execute = False
            else:
                apple2key = Ascii2Apple2Ascii( key )
                emulator.apple2.softswitches.kbd = apple2key
                print( emulator.cpu.cycles, "pressed (recorded)", hexbyte( Apple2Ascii2Ascii( apple2key ) ), comment )
                emulator.display.save_hires_bytes( str( cycles ) + '.dat' )

        return active, execute


class PrintCharTester:
    def __init__( self ) -> None:
        self.mem09_1 = None

    def LDA_indirect( self, emulator: "Emulator" ) -> tuple[bool, bool]:  # (active, execute)
        cpu = emulator.apple2.cpu
        if cpu.PC == 0x5118:
            print( "yes_1" )
            self.mem09_1 = emulator.mem[0x09]
        if cpu.PC == 0x5126:
            print( "yes_2" )
            mem08_2 = emulator.mem[0x08]
            mem09_2 = emulator.mem[0x09]
            print( hexbyte( self.mem09_1 ), hexbyte( mem08_2 ), hexbyte( mem09_2 ) )
        if cpu.PC == 0x512e:
            return False, False
        return True, True


class RandomTesterCheckpoint:
    def __init__( self, emulator: "Emulator" ) -> None:
        self.emulator = emulator
        self.cpu = self.emulator.cpu

    def checkpoint( self, emulator: "Emulator" ) -> tuple[bool, bool]:
        if self.cpu.PC == 0x4c36:
            # in/out: 0x4e, 0x4f
            # in: 0xfc, 0x150a
            pass
        elif self.cpu.PC == 0x4c4a:
            print( ';'.join( [
                str( self.cpu.cycles ),
                hexbyte( self.emulator.mem[0x4e] ),
                hexbyte( self.emulator.mem[0x4f] ),
                hexbyte( self.emulator.mem[0xfc] ),
                hexbyte( self.emulator.mem[0x150a] ),
            ] ) )
            # self.emulator.mem[0x4e] = 1
            # self.emulator.mem[0x4f] = 1
            pass
        return True, True


class KeyScript:
    """Press a scripted sequence of keys at specific instruction counts.

    Unlike `RecordedKeys` (cycle-based, tied to a specific Robotron run),
    `KeyScript` is driven by `emulator.instructions`, so it works with any
    program: assemble a small test program, add a `KeyScript`, and press
    keys from code instead of a pygame window.

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
