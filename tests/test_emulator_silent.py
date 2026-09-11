import unittest
from pysm import Event
from papple2.Assembler import Assembler
from papple2.Checkpoints import KeyScript
from papple2.Emulator import Emulator, after_instructions, at_address


class TestEmulatorSilent(unittest.TestCase):

    def test_create_no_display(self):
        # 2026-09-11 This results in `AttributeError: 'Display' object has no attribute 'screen'`
        # see `TODO.md` for details on M2.5
        emulator = Emulator(no_display=True)

    def test_constructs_without_window(self):
        emulator = Emulator(no_display=True)
        emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')

    def test_run_stops_after_n_instructions(self):
        emulator = Emulator(no_display=True)
        emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')
        emulator.run(until=after_instructions(1000))
        self.assertEqual(emulator.instructions, 1000)

    def test_run_stops_at_address(self):
        emulator = Emulator(no_display=True)
        emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')
        emulator.run(until=at_address(0x2dfd))
        self.assertEqual(emulator.cpu.PC, 0x2dfd)
        self.assertEqual(emulator.instructions, 0)

    def test_ctrlx_toggles_state(self):
        emulator = Emulator(no_display=True)
        self.assertEqual(emulator.states.leaf_state.name, 'Running')
        emulator.states.dispatch(Event('ctrlx'))
        self.assertEqual(emulator.states.leaf_state.name, 'Stopped')
        emulator.states.dispatch(Event('ctrlx'))
        self.assertEqual(emulator.states.leaf_state.name, 'Running')

    def test_keypress_reaches_program(self):
        """
        Walkthrough: driving papple2 purely from code, no pygame window.

        The assembled program below is a minimal Apple II key reader. It
        polls $C000 (the keyboard data line) until bit 7 is set, stores the
        raw byte at $0300, clears the keyboard strobe by touching $C010,
        then spins forever at `halt` -- a second, separate loop used as the
        known stopping point (the polling loop itself is not a safe `until`
        target, since the emulator passes through it before any key has
        been pressed).

        `KeyScript` is a checkpoint: a function `Emulator.run` calls before
        every instruction. It waits until `emulator.instructions` reaches a
        scheduled count, then calls `emulator.press_key`, the same call the
        pygame window makes on a real keypress. The CPU never learns this
        happened directly; it only sees the effect on its next read of
        $C000, wherever in the polling loop that happens to land.
        """
        asm = Assembler()
        tokens = asm.tokenize("""
                *=$6000

        loop:   LDA $C000       ; read the keyboard data line: bit 7 set = key waiting
                BPL loop        ; bit 7 clear -> keep polling
                STA $0300       ; store the raw byte (high bit still on)
                LDA $C010       ; clear the keyboard strobe
        halt:   JMP halt        ; spin here forever -- our known address
        """)
        code = asm.generate_code(tokens)
        byte_array = asm.to_byte_array(code)

        emulator = Emulator(no_display=True)
        emulator.apple2.memory.load_test_data(0x6000, byte_array)
        emulator.cpu.PC = 0x6000

        keys = KeyScript([(300, 'A')])
        emulator.add_checkpoint(keys.press_keys)

        emulator.run(until=at_address(asm.labels['HALT']))

        self.assertEqual(emulator.mem[0x0300], ord('A') | 0x80)
