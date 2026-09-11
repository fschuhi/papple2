import unittest
from papple2.Emulator import Emulator


class TestEmulatorSilent(unittest.TestCase):

    def test_create_no_display(self):
        # 2026-09-11 This results in `AttributeError: 'Display' object has no attribute 'screen'`
        # see `TODO.md` for details on M2.5
        emulator = Emulator(no_display=True)

    def test_constructs_without_window(self):
        emulator = Emulator(no_display=True)
        emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')

