import unittest
from papple2.core.Memory import Memory
from papple2.core.CPU import CPU


class TestLogicalOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_AND(self):
        self.memory.write_byte(0x1000, 0x37)
        self.cpu.A = 0x34
        self.cpu.AND(0x1000)
        self.assertEqual( self.cpu.A, 0x34 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.cpu.A = 0x40
        self.cpu.AND(0x1000)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 0)

    def test_EOR(self):
        self.memory.write_byte(0x1000, 0x37)
        self.cpu.A = 0x34
        self.cpu.EOR(0x1000)
        self.assertEqual( self.cpu.A, 0x03 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.cpu.A = 0x90
        self.cpu.EOR(0x1000)
        self.assertEqual( self.cpu.A, 0xA7 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.cpu.A = 0x37
        self.cpu.EOR(0x1000)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 0)

    def test_ORA(self):
        self.memory.write_byte(0x1000, 0x37)
        self.cpu.A = 0x34
        self.cpu.ORA(0x1000)
        self.assertEqual( self.cpu.A, 0x37 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.cpu.A = 0x90
        self.cpu.ORA(0x1000)
        self.assertEqual( self.cpu.A, 0xB7 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.cpu.A = 0x00
        self.cpu.ORA(0x1001)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 0)

    def test_BIT(self):
        self.memory.write_byte(0x1000, 0x00)
        self.cpu.A = 0x00
        self.cpu.BIT(0x1000)
        self.assertEqual(self.cpu.overflow_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.memory.write_byte(0x1000, 0x40)
        self.cpu.A = 0x00
        self.cpu.BIT(0x1000)
        self.assertEqual(self.cpu.overflow_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.memory.write_byte(0x1000, 0x80)
        self.cpu.A = 0x00
        self.cpu.BIT(0x1000)
        self.assertEqual(self.cpu.overflow_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.memory.write_byte(0x1000, 0xC0)
        self.cpu.A = 0x00
        self.cpu.BIT(0x1000)
        self.assertEqual(self.cpu.overflow_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.memory.write_byte(0x1000, 0xC0)
        self.cpu.A = 0xC0
        self.cpu.BIT(0x1000)
        self.assertEqual(self.cpu.overflow_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
