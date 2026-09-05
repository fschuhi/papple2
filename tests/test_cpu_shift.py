import unittest
from papple2.Memory import Memory
from papple2.CPU import CPU


class TestShiftOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_ASL(self):
        self.cpu.A = 0x01
        self.cpu.ASL()
        self.assertEqual( self.cpu.A, 0x02 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)
        self.memory.write_byte(0x1000, 0x02)
        self.cpu.ASL(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x04)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)
        self.cpu.A = 0x80
        self.cpu.ASL()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)

    def test_LSR(self):
        self.cpu.A = 0x01
        self.cpu.LSR()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.LSR(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x00)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.A = 0x80
        self.cpu.LSR()
        self.assertEqual( self.cpu.A, 0x40 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

    def test_ROL(self):
        self.cpu.carry_flag = 0
        self.cpu.A = 0x80
        self.cpu.ROL()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x80
        self.cpu.ROL()
        self.assertEqual( self.cpu.A, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 0
        self.memory.write_byte(0x1000, 0x80)
        self.cpu.ROL(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x00)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 1
        self.memory.write_byte(0x1000, 0x80)
        self.cpu.ROL(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x01)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)

    def test_ROR(self):
        self.cpu.carry_flag = 0
        self.cpu.A = 0x01
        self.cpu.ROR()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x01
        self.cpu.ROR()
        self.assertEqual( self.cpu.A, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)  # @@@
        self.assertEqual(self.cpu.zero_flag, 0)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 0
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.ROR(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x00)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.cpu.carry_flag = 1
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.ROR(0x1000)
        self.assertEqual(self.memory.read_byte(0x1000), 0x80)
        self.assertEqual(self.cpu.sign_flag, 1)  # @@@
        self.assertEqual(self.cpu.zero_flag, 0)  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
