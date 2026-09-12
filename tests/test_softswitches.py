import unittest
from papple2.core.apple import Display, Speaker, SoftSwitches, Apple2


class TestSoftSwitches(unittest.TestCase):

    def setUp(self):
        self.display = Display(apple2=None, no_display=True)
        self.speaker = Speaker(quiet=True)
        self.switches = SoftSwitches(self.display, self.speaker)

    def test_keyboard_strobe(self):
        self.switches.kbd = 0xC1  # e.g. 'A' with the high bit set, as the real keyboard would deliver it
        self.assertEqual(self.switches.read_byte(0xC000), 0xC1)
        self.assertEqual(self.switches.read_byte(0xC010), 0x00)
        self.assertEqual(self.switches.kbd, 0x41)  # strobe cleared: high bit gone

    def test_txtclr_txtset(self):
        self.switches.read_byte(0xC051)  # txtset first, so txtclr has something to undo
        self.switches.read_byte(0xC050)
        self.assertFalse(self.display.text)

        self.switches.read_byte(0xC051)
        self.assertTrue(self.display.text)
        self.assertFalse(self.display.colour)

    def test_mixclr_mixset(self):
        self.switches.read_byte(0xC052)
        self.assertFalse(self.display.mix)

        self.switches.read_byte(0xC053)
        self.assertTrue(self.display.mix)
        self.assertTrue(self.display.colour)

    def test_lowscr_hiscr(self):
        self.switches.read_byte(0xC054)
        self.assertEqual(self.display.page, 1)

        self.switches.read_byte(0xC055)
        self.assertEqual(self.display.page, 2)

    def test_lores_hires(self):
        self.switches.read_byte(0xC056)
        self.assertFalse(self.display.high_res)

        self.switches.read_byte(0xC057)
        self.assertTrue(self.display.high_res)

    def test_write_byte_ignores_value_but_triggers_same_effect(self):
        # SoftSwitches is "ROM": writing doesn't store a value, it just triggers
        # the same read-side effect, regardless of what's written.
        self.switches.write_byte(0xC051, 0x00)
        self.assertTrue(self.display.text)

    def test_read_byte_out_of_range_raises(self):
        with self.assertRaises(AssertionError):
            self.switches.read_byte(0xD000)


class TestSoftSwitchesThroughMemory(unittest.TestCase):

    def test_memory_mapped_write_reaches_softswitches(self):
        # One level up from the unit tests above: proves the $C0-page routing
        # in Memory.write_byte actually dispatches to SoftSwitches, not just
        # that SoftSwitches works when called directly.
        apple2 = Apple2(no_display=True)
        apple2.memory.write_byte(0xC051, 0x00)
        self.assertTrue(apple2.display.text)


if __name__ == "__main__":
    unittest.main()
