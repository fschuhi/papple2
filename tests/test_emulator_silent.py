import unittest
from pysm import Event
from papple2.Assembler import Assembler
from papple2.Checkpoints import KeyScript
from papple2.Emulator import Emulator, after_instructions, at_address
from papple2.Hooks import CPUHook


class WriteProtectHook(CPUHook):
    """
    Minimal demonstration of the veto-based write-hook pattern -- the same one
    `TimeMachine` and `MemAccessCollector` use in `Hooks.py`. Returning False
    from `write_hook` stops `CPU.write_byte` from writing at all, so nothing
    outside this hook needs to know the protected ranges exist. Whoever needs
    real write protection (e.g. a Robotron-specific hook) can start from this.
    """

    def __init__(self, emulator, protected_ranges):
        super().__init__(emulator)
        self.protected_ranges = protected_ranges  # list of (start, end), inclusive

    def write_hook(self, address, newvalue):
        for start, end in self.protected_ranges:
            if start <= address <= end:
                return False
        return super().write_hook(address, newvalue)


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

    def test_checkpoint_stop_halts_headless_run(self):
        """
        A checkpoint-requested stop (execute=False) has to act like a real
        halt when there's no window to resume it from -- otherwise `run()`
        never returns. This exercises that path directly, with no `until`
        involved at all: the checkpoint below is the only thing stopping it.
        """
        emulator = Emulator(no_display=True)
        emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')

        def stop_after_10(e):
            return (True, e.instructions < 10)  # (active, execute)

        emulator.add_checkpoint(stop_after_10)
        emulator.run()  # no `until` -- only the checkpoint can stop this

        self.assertEqual(emulator.instructions, 10)
        self.assertEqual(emulator.states.leaf_state.name, 'Stopped')

    def test_rts_without_matching_jsr_does_not_crash(self):
        """
        Regression test for a real bug (not a Robotron assumption): `handle_rts`
        used to assert that `jsr_stack` was non-empty on every RTS. That's false
        in general -- the classic 6502 "computed jump" trick pushes a target
        address by hand (PHA/PHA) and uses RTS to jump to it, with no JSR
        involved at all. This program does exactly that: it never executes a
        JSR, only two PHAs and an RTS, and should land at `landed` without
        `handle_rts` raising.
        """
        asm = Assembler()
        tokens = asm.tokenize("""
                *=$6000

        start:  LDA #$60       ; high byte of (landed - 1)
                PHA
                LDA #$06       ; low byte of (landed - 1)
                PHA
                RTS             ; "jumps" to landed via the stack, no JSR involved
        landed: JMP landed
        """)
        code = asm.generate_code(tokens)
        byte_array = asm.to_byte_array(code)

        emulator = Emulator(no_display=True)
        emulator.apple2.memory.load_test_data(0x6000, byte_array)
        emulator.cpu.PC = 0x6000

        emulator.run(until=at_address(asm.labels['LANDED']))

        self.assertEqual(emulator.cpu.PC, asm.labels['LANDED'])
        self.assertEqual(len(emulator.jsr_stack), 0)

    def test_write_protect_hook_vetoes_writes_in_range(self):
        """
        The program writes once inside the protected range and once outside
        it. Only the write outside the range should actually land in memory --
        showing that write protection can live entirely in a hook, with no
        changes to Memory or CPU needed.
        """
        asm = Assembler()
        tokens = asm.tokenize("""
                *=$6000

        start:  LDA #$42
                STA $4050       ; inside the protected range -- should be vetoed
                LDA #$99
                STA $0300       ; outside the protected range -- should go through
        done:   JMP done
        """)
        code = asm.generate_code(tokens)
        byte_array = asm.to_byte_array(code)

        emulator = Emulator(no_display=True)
        emulator.apple2.memory.load_test_data(0x6000, byte_array)
        emulator.cpu.PC = 0x6000

        guard = WriteProtectHook(emulator, protected_ranges=[(0x4000, 0x40ff)])
        guard.enable_write_hook()

        emulator.run(until=at_address(asm.labels['DONE']))

        self.assertEqual(emulator.mem[0x4050], 0x00)  # vetoed
        self.assertEqual(emulator.mem[0x0300], 0x99)  # went through
