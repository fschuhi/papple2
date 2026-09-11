import unittest
from pysm import Event
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
