import unittest
from papple2.Emulator import Emulator


class TestEmulator(unittest.TestCase):

    def test_create_no_display(self):
        emulator = Emulator(no_display=True)
