import unittest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


class Test6502Bugs(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_zero_page_x(self):
        self.cpu.X = 0x01
        self.memory.load_test_data(0x1000, [0x00, 0x7F, 0xFF])
        self.cpu.PC = 0x1000
        self.assertEqual(self.cpu.zero_page_x_mode(), 0x01)
        self.assertEqual(self.cpu.zero_page_x_mode(), 0x80)
        self.assertEqual(self.cpu.zero_page_x_mode(), 0x00)

    def test_indirect(self):
        self.memory.load_test_data(0x20, [0x00, 0x20])
        self.memory.load_test_data(0x00, [0x12])
        self.memory.load_test_data(0xFF, [0x34])
        self.memory.load_test_data(0x100, [0x56])
        self.memory.load_test_data(0x1000, [0x20, 0x20, 0xFF, 0xFF, 0x00, 0x45, 0x23])
        self.memory.load_test_data(0x2000, [0x05])
        self.memory.load_test_data(0x1234, [0x05])
        self.memory.load_test_data(0x2345, [0x00, 0xF0])

        self.cpu.PC = 0x1000

        self.cpu.X = 0x00
        self.cpu.LDA(self.cpu.indirect_x_mode())
        self.assertEqual( self.cpu.A, 0x05 )

        self.cpu.Y = 0x00
        self.cpu.LDA(self.cpu.indirect_y_mode())
        self.assertEqual( self.cpu.A, 0x05 )

        self.cpu.Y = 0x00
        self.cpu.LDA(self.cpu.indirect_y_mode())
        self.assertEqual( self.cpu.A, 0x05 )

        self.cpu.X = 0x00
        self.cpu.LDA(self.cpu.indirect_x_mode())
        self.assertEqual( self.cpu.A, 0x05 )

        self.cpu.X = 0xFF
        self.cpu.LDA(self.cpu.indirect_x_mode())
        self.assertEqual( self.cpu.A, 0x05 )

        self.assertEqual(self.cpu.indirect_mode(), 0xF000)
