import unittest
from papple2.Memory import Memory


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()

    def test_load(self):
        self.memory.load_test_data(0x1000, [0x01, 0x02, 0x03])
        self.assertEqual(self.memory.read_byte(0x1000), 0x01)
        self.assertEqual(self.memory.read_byte(0x1001), 0x02)
        self.assertEqual(self.memory.read_byte(0x1002), 0x03)

    def test_write(self):
        self.memory.write_byte(0x1000, 0x11)
        self.memory.write_byte(0x1001, 0x12)
        self.memory.write_byte(0x1002, 0x13)
        self.assertEqual(self.memory.read_byte(0x1000), 0x11)
        self.assertEqual(self.memory.read_byte(0x1001), 0x12)
        self.assertEqual(self.memory.read_byte(0x1002), 0x13)
