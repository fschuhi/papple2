import unittest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


class TestIncrementDecrementOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_INC(self):
        self.memory.write_byte(0x1000, 0x00)
        self.cpu.INC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x01)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.memory.write_byte(0x1000, 0x7F)
        self.cpu.INC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x80)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.memory.write_byte(0x1000, 0xFF)
        self.cpu.INC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x00)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)

    def test_INX(self):
        self.cpu.X = 0x00
        self.cpu.INX()
        self.assertEqual( self.cpu.X, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.X = 0x7F
        self.cpu.INX()
        self.assertEqual( self.cpu.X, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.X = 0xFF
        self.cpu.INX()
        self.assertEqual( self.cpu.X, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)

    def test_INY(self):
        self.cpu.Y = 0x00
        self.cpu.INY()
        self.assertEqual( self.cpu.Y, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.Y = 0x7F
        self.cpu.INY()
        self.assertEqual( self.cpu.Y, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.Y = 0xFF
        self.cpu.INY()
        self.assertEqual( self.cpu.Y, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)

    def test_DEC(self):
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.DEC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x00)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.memory.write_byte(0x1000, 0x80)
        self.cpu.DEC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x7F)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.memory.write_byte(0x1000, 0x00)
        self.cpu.DEC(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0xFF)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_DEX(self):
        self.cpu.X = 0x01
        self.cpu.DEX()
        self.assertEqual( self.cpu.X, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.X = 0x80
        self.cpu.DEX()
        self.assertEqual( self.cpu.X, 0x7F )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.X = 0x00
        self.cpu.DEX()
        self.assertEqual( self.cpu.X, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_DEY(self):
        self.cpu.Y = 0x01
        self.cpu.DEY()
        self.assertEqual( self.cpu.Y, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.Y = 0x80
        self.cpu.DEY()
        self.assertEqual( self.cpu.Y, 0x7F )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.Y = 0x00
        self.cpu.DEY()
        self.assertEqual( self.cpu.Y, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
