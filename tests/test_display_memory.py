import unittest
from papple2.core.apple import Apple2


class TestDisplayMemory(unittest.TestCase):

    def setUp(self):
        self.apple2 = Apple2(no_display=True)

    def test_hires_page1_write_read_roundtrip(self):
        for address in (0x2000, 0x2abc, 0x3fff):
            self.apple2.memory.write_byte(address, 0x55)
            self.assertEqual(self.apple2.memory.read_byte(address), 0x55)

    def test_hires_page2_write_read_roundtrip(self):
        for address in (0x4000, 0x4abc, 0x5ffe):
            self.apple2.memory.write_byte(address, 0xAA)
            self.assertEqual(self.apple2.memory.read_byte(address), 0xAA)

    def test_write_outside_hires_range_does_not_call_display_update(self):
        # Spies on display.update to confirm the range check in Memory.write_byte
        # is what keeps rendering out of the way -- not just an accident of no_display.
        calls = []
        self.apple2.display.update = lambda address, value: calls.append((address, value))

        self.apple2.memory.write_byte(0x5fff, 0x11)  # just above Memory's checked range
        self.assertEqual(calls, [])

        self.apple2.memory.write_byte(0x5ffe, 0x11)  # last address inside it
        self.assertEqual(calls, [(0x5ffe, 0x11)])

    def test_no_display_write_across_full_hires_span_does_not_raise(self):
        for address in range(0x2000, 0x6000):
            self.apple2.memory.write_byte(address, address & 0xFF)


if __name__ == "__main__":
    unittest.main()
