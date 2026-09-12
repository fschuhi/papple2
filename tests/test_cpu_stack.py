import unittest
from papple2.core.Memory import Memory
from papple2.core.CPU import CPU


class TestStackOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_TSX(self):
        s = self.cpu.SP
        self.cpu.TSX()
        self.assertEqual( self.cpu.X, s )
        # @@@ check NZ?

    def test_TXS(self):
        x = self.cpu.X
        self.cpu.TXS()
        self.assertEqual( self.cpu.SP, x )

    def test_PHA_and_PLA(self):
        self.cpu.A = 0x00
        self.cpu.PHA()
        self.cpu.A = 0x01
        self.cpu.PHA()
        self.cpu.A = 0xFF
        self.cpu.PHA()
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.cpu.PLA()
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.cpu.PLA()
        self.assertEqual( self.cpu.A, 0x01 )
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.cpu.PLA()
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.sign_flag, 0)

    def test_PHP_and_PLP(self):
        p = self.cpu.status_as_byte()
        self.cpu.PHP()
        self.cpu.status_from_byte(0xFF)
        self.cpu.PLP()
        self.assertEqual(self.cpu.status_as_byte(), p)
