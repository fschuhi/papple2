"""Tests for papple2.programs: each boot() gives a ready machine."""

from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.programs import nested_loops

# nested_loops.PROGRAM, assembled by hand:
#   6000 LDY #$02   6002 LDX #$03   6004 JSR $6010   6007 DEX
#   6008 BNE $6004  600a DEY        600b BNE $6002   600d JMP $6013
#   6010 INC $10    6012 RTS        6013 NOP
NESTED_LOOPS_BYTES = [
    0xA0, 0x02, 0xA2, 0x03, 0x20, 0x10, 0x60, 0xCA, 0xD0, 0xFA,
    0x88, 0xD0, 0xF5, 0x4C, 0x13, 0x60, 0xE6, 0x10, 0x60, 0xEA,
]


def test_nested_loops_boots_with_the_program_at_6000_and_pc_there() -> None:
    emulator = nested_loops.boot()

    assert [emulator.mem[a] for a in range(0x6000, 0x6014)] == NESTED_LOOPS_BYTES
    assert emulator.cpu.PC == 0x6000


def test_nested_loops_runs_to_its_end_in_39_instructions() -> None:
    # LDY once, LDX twice, and per inner pass JSR, INC, RTS, DEX, BNE:
    # 1 + 2 + 6 * 5 = 33; DEY and BNE twice, JMP and NOP once: 39.
    emulator = nested_loops.boot()

    emulator.run(until=instruction_count_reaches(39))

    assert emulator.cpu.PC == 0x6014
