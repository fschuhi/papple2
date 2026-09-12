import unittest
from papple2.debug.assembler import Assembler
from papple2.core.emulator import Emulator


def run_steps(emulator, count):
    """
    Drives the CPU directly, one instruction at a time, the same way
    Emulator.run() does per step -- but without going through the state
    machine / checkpoints / window layer. That's deliberate: EmulatorStoppedState
    calls time_machine.enable_restoring() on its own (see emulator.py,
    on_enter), so driving execution through the full run() loop would trigger
    restoring as a side effect of any breakpoint/ctrlx transition. These tests
    want to control exactly when TimeMachine gets involved.
    """
    for _ in range(count):
        emulator.cpu.do_next_step()
        emulator.post_op()


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


def assemble(program):
    asm = Assembler()
    tokens = asm.tokenize(program)
    code = asm.generate_code(tokens)
    return asm, asm.to_byte_array(code)


class TestTimeMachineRecording(unittest.TestCase):

    def setUp(self):
        self.asm, program = assemble(THREE_WRITES_PROGRAM)
        self.emulator = Emulator(no_display=True)
        self.emulator.apple2.memory.load_test_data(0x6000, program)
        self.emulator.cpu.PC = 0x6000

    def test_no_recording_before_hook_enabled(self):
        # LDA #$11 / STA $0300, LDA #$22 / STA $0301 -- two writes happen,
        # but the hook isn't enabled yet, so nothing should be recorded.
        run_steps(self.emulator, 4)
        self.assertEqual(self.emulator.time_machine.write_states, [])

        self.emulator.time_machine.enable_write_hook()

        # LDA #$33 / STA $0302 -- the third write, now with the hook enabled.
        run_steps(self.emulator, 2)

        self.assertEqual(len(self.emulator.time_machine.write_states), 1)
        self.assertEqual(self.emulator.time_machine.write_states[0], (0x0302, 0x00, 0x33))


class TestTimeMachineRestore(unittest.TestCase):

    def setUp(self):
        self.asm, program = assemble(THREE_WRITES_PROGRAM)
        self.emulator = Emulator(no_display=True)
        self.emulator.apple2.memory.load_test_data(0x6000, program)
        self.emulator.cpu.PC = 0x6000
        self.emulator.time_machine.enable_write_hook()

        run_steps(self.emulator, 6)  # all three writes now recorded

        self.time_machine = self.emulator.time_machine
        self.mem = self.emulator.mem

    def test_three_writes_recorded(self):
        self.assertEqual(len(self.time_machine.write_states), 3)
        self.assertEqual(self.mem[0x0300], 0x11)
        self.assertEqual(self.mem[0x0301], 0x22)
        self.assertEqual(self.mem[0x0302], 0x33)

    def test_restore_prev_rewinds_memory_and_cpu(self):
        self.time_machine.enable_restoring()  # syncs state_index to "now"

        restored = self.time_machine.restore_prev_state(1)

        self.assertEqual(restored, 1)
        self.assertEqual(self.mem[0x0302], 0x00)  # 3rd write undone
        self.assertEqual(self.mem[0x0301], 0x22)  # earlier writes untouched
        self.assertEqual(self.emulator.cpu.PC, self.asm.labels['THIRD'])  # CPU rewound too

    def test_restore_prev_state_stops_at_the_earliest_undoable_write(self):
        self.time_machine.enable_restoring()
        self.time_machine.restore_prev_state(1)  # undoes the 3rd write

        # A second rewind hits restore_prev_state's own loop guard and is a
        # no-op: as coded, the very first recorded write can never be undone
        # through this method (see the note below the test file).
        restored = self.time_machine.restore_prev_state(1)

        self.assertEqual(restored, 0)
        self.assertEqual(self.mem[0x0301], 0x22)  # unchanged, nothing crashed

    def test_restore_next_redoes_and_stops_at_the_end(self):
        self.time_machine.enable_restoring()
        self.time_machine.restore_prev_state(1)  # undo the 3rd write
        self.assertEqual(self.mem[0x0302], 0x00)

        restored = self.time_machine.restore_next_state(1)
        self.assertEqual(restored, 1)
        self.assertEqual(self.mem[0x0302], 0x33)  # redone

        restored_again = self.time_machine.restore_next_state(1)
        self.assertEqual(restored_again, 0)  # nothing further to redo, no crash

    def test_disable_restoring_truncates_the_abandoned_future(self):
        self.time_machine.enable_restoring()
        self.time_machine.restore_prev_state(1)  # rewinds past the 3rd write

        self.time_machine.disable_restoring()

        self.assertEqual(len(self.time_machine.write_states), 1)
        self.assertEqual(len(self.time_machine.cpu_states), 1)
        self.assertEqual(self.time_machine.write_states[0], (0x0300, 0x00, 0x11))


if __name__ == "__main__":
    unittest.main()
