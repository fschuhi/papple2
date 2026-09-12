import unittest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


class TestLoadStoreOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU( self.memory, program_counter=0 )
        self.memory.load_test_data(0x1000, [0x00, 0x01, 0x7F, 0x80, 0xFF])

    def test_LDA(self):
        self.cpu.LDA(0x1000)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.LDA(0x1001)
        self.assertEqual( self.cpu.A, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDA(0x1002)
        self.assertEqual( self.cpu.A, 0x7F )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDA(0x1003)
        self.assertEqual( self.cpu.A, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDA(0x1004)
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_LDX(self):
        self.cpu.LDX(0x1000)
        self.assertEqual( self.cpu.X, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.LDX(0x1001)
        self.assertEqual( self.cpu.X, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDX(0x1002)
        self.assertEqual( self.cpu.X, 0x7F )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDX(0x1003)
        self.assertEqual( self.cpu.X, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDX(0x1004)
        self.assertEqual( self.cpu.X, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_LDY(self):
        self.cpu.LDY(0x1000)
        self.assertEqual( self.cpu.Y, 0x00 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.cpu.LDY(0x1001)
        self.assertEqual( self.cpu.Y, 0x01 )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDY(0x1002)
        self.assertEqual( self.cpu.Y, 0x7F )
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDY(0x1003)
        self.assertEqual( self.cpu.Y, 0x80 )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.cpu.LDY(0x1004)
        self.assertEqual( self.cpu.Y, 0xFF )
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)

    def test_STA(self):
        self.cpu.A = 0x37
        self.cpu.STA(0x2000)
        self.assertEqual(self.memory.read_byte(0x2000), 0x37)

    def test_STX(self):
        self.cpu.X = 0x38
        self.cpu.STX(0x2000)
        self.assertEqual(self.memory.read_byte(0x2000), 0x38)

    def test_STY(self):
        self.cpu.Y = 0x39
        self.cpu.STY(0x2000)
        self.assertEqual(self.memory.read_byte(0x2000), 0x39)
