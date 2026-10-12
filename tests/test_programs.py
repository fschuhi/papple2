"""Tests for papple2.programs: each boot() gives a ready machine."""

from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.programs import nested_loops, rts_dispatch

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


# rts_dispatch.PROGRAM, assembled by hand:
#   6000 LDA #$00    6002 JSR $600d   6005 LDA #$01    6007 JSR $600d
#   600a JMP $6022   600d ASL         600e TAX         600f LDA $601f,X
#   6012 PHA         6013 LDA $601e,X 6016 PHA         6017 RTS
#   6018 INC $10     601a RTS         601b INC $11     601d RTS
#   601e .WORD $6017 6020 .WORD $601a 6022 NOP
RTS_DISPATCH_BYTES = [
    0xA9, 0x00, 0x20, 0x0D, 0x60, 0xA9, 0x01, 0x20, 0x0D, 0x60,
    0x4C, 0x22, 0x60, 0x0A, 0xAA, 0xBD, 0x1F, 0x60, 0x48, 0xBD,
    0x1E, 0x60, 0x48, 0x60, 0xE6, 0x10, 0x60, 0xE6, 0x11, 0x60,
    0x17, 0x60, 0x1A, 0x60, 0xEA,
]


def test_rts_dispatch_boots_with_the_program_at_6000_and_pc_there() -> None:
    emulator = rts_dispatch.boot()

    assert [emulator.mem[a] for a in range(0x6000, 0x6023)] == RTS_DISPATCH_BYTES
    assert emulator.cpu.PC == 0x6000


def test_rts_dispatch_runs_both_commands_in_24_instructions() -> None:
    # The main line: LDA, JSR, LDA, JSR, JMP, NOP. Each command: dispatch's
    # 7 (ASL, TAX, LDA, PHA, LDA, PHA, RTS), then INC and RTS. 6 + 2 * 9.
    emulator = rts_dispatch.boot()
    before = emulator.mem[0x10], emulator.mem[0x11]

    emulator.run(until=instruction_count_reaches(24))

    assert emulator.cpu.PC == 0x6023
    # Each command ran once: command 0 counts up $10, command 1 $11.
    assert (emulator.mem[0x10], emulator.mem[0x11]) == (
        (before[0] + 1) & 0xFF,
        (before[1] + 1) & 0xFF,
    )
