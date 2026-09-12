import unittest
from papple2.core.Memory import Memory
from papple2.core.CPU import CPU


class TestRegisterTransferOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_TAX(self):
        self.cpu.A = 0x00
        self.cpu.TAX()
        self.assertEqual( self.cpu.X, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.A = 0x01
        self.cpu.TAX()
        self.assertEqual( self.cpu.X, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.A = 0xFF
        self.cpu.TAX()
        self.assertEqual( self.cpu.X, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_TAY(self):
        self.cpu.A = 0x00
        self.cpu.TAY()
        self.assertEqual( self.cpu.Y, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.A = 0x01
        self.cpu.TAY()
        self.assertEqual( self.cpu.Y, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.A = 0xFF
        self.cpu.TAY()
        self.assertEqual( self.cpu.Y, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_TXA(self):
        self.cpu.X = 0x00
        self.cpu.TXA()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.X = 0x01
        self.cpu.TXA()
        self.assertEqual( self.cpu.A, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.X = 0xFF
        self.cpu.TXA()
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_TYA(self):
        self.cpu.Y = 0x00
        self.cpu.TYA()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.Y = 0x01
        self.cpu.TYA()
        self.assertEqual( self.cpu.A, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.Y = 0xFF
        self.cpu.TYA()
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
