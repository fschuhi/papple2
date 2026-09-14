import pytest
from papple2.debug.assembler import Assembler
from papple2.core.emulator import Emulator


# Three STAs to three distinct addresses -- enough to tell writes apart by
# address and value, and to have "earlier" and "later" recorded states to
# rewind between. Labels mark the PC right after the 2nd and 3rd STA, so
# CPU-state rewinds can be checked against a known address, not just memory.
THREE_WRITES_PROGRAM = """
        *=$6000
start:  LDA #$11
        STA $0300
        LDA #$22
        STA $0301
third:  LDA #$33
        STA $0302
done:   JMP done
"""


def test_no_recording_before_hook_enabled(make_emulator, run_steps):
    asm, emulator = make_emulator(THREE_WRITES_PROGRAM)

    # LDA #$11 / STA $0300, LDA #$22 / STA $0301 -- two writes happen,
    # but the hook isn't enabled yet, so nothing should be recorded.
    run_steps(emulator, 4)
    assert emulator.time_machine.write_states == []

    emulator.time_machine.enable_write_hook()

    # LDA #$33 / STA $0302 -- the third write, now with the hook enabled.
    run_steps(emulator, 2)

    assert len(emulator.time_machine.write_states) == 1
    assert emulator.time_machine.write_states[0] == (0x0302, 0x00, 0x33)


@pytest.fixture
def emulator_with_three_writes(make_emulator, run_steps) -> tuple[Assembler, Emulator]:
    asm, emulator = make_emulator(THREE_WRITES_PROGRAM)
    emulator.time_machine.enable_write_hook()

    run_steps(emulator, 6)  # all three writes now recorded

    return asm, emulator


def test_three_writes_recorded(emulator_with_three_writes):
    asm, emulator = emulator_with_three_writes
    time_machine = emulator.time_machine
    mem = emulator.mem

    assert len(time_machine.write_states) == 3
    assert mem[0x0300] == 0x11
    assert mem[0x0301] == 0x22
    assert mem[0x0302] == 0x33


def test_restore_prev_rewinds_memory_and_cpu(emulator_with_three_writes):
    asm, emulator = emulator_with_three_writes
    time_machine = emulator.time_machine
    mem = emulator.mem

    time_machine.enable_restoring()  # syncs state_index to "now"

    restored = time_machine.restore_prev_state(1)

    assert restored == 1
    assert mem[0x0302] == 0x00  # 3rd write undone
    assert mem[0x0301] == 0x22  # earlier writes untouched
    assert emulator.cpu.PC == asm.labels['THIRD']  # CPU rewound too


def test_restore_prev_state_stops_at_the_earliest_undoable_write(emulator_with_three_writes):
    asm, emulator = emulator_with_three_writes
    time_machine = emulator.time_machine
    mem = emulator.mem

    time_machine.enable_restoring()
    time_machine.restore_prev_state(1)  # undoes the 3rd write

    # A second rewind hits restore_prev_state's own loop guard and is a
    # no-op: as coded, the very first recorded write can never be undone
    # through this method (see the note below the test file).
    restored = time_machine.restore_prev_state(1)

    assert restored == 0
    assert mem[0x0301] == 0x22  # unchanged, nothing crashed


def test_restore_next_redoes_and_stops_at_the_end(emulator_with_three_writes):
    asm, emulator = emulator_with_three_writes
    time_machine = emulator.time_machine
    mem = emulator.mem

    time_machine.enable_restoring()
    time_machine.restore_prev_state(1)  # undo the 3rd write
    assert mem[0x0302] == 0x00

    restored = time_machine.restore_next_state(1)
    assert restored == 1
    assert mem[0x0302] == 0x33  # redone

    restored_again = time_machine.restore_next_state(1)
    assert restored_again == 0  # nothing further to redo, no crash


def test_disable_restoring_truncates_the_abandoned_future(emulator_with_three_writes):
    asm, emulator = emulator_with_three_writes
    time_machine = emulator.time_machine
    mem = emulator.mem

    time_machine.enable_restoring()
    time_machine.restore_prev_state(1)  # rewinds past the 3rd write

    time_machine.disable_restoring()

    assert len(time_machine.write_states) == 1
    assert len(time_machine.cpu_states) == 1
    assert time_machine.write_states[0] == (0x0300, 0x00, 0x11)
