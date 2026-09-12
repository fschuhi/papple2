import unittest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


class TestSystemFunctionOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_BRK(self):
        self.cpu.PC = 0x1000
        self.memory.load_test_data(0xFFFE, [0x00, 0x20])
        status = self.cpu.status_as_byte()
        self.cpu.BRK()
        self.assertEqual( self.cpu.PC, 0x2000 )
        self.assertEqual(self.cpu.break_flag, 1)
        self.assertEqual( self.memory.read_byte( self.cpu.STACK_PAGE + self.cpu.SP + 1 ), status )
        self.assertEqual( self.memory.read_byte( self.cpu.STACK_PAGE + self.cpu.SP + 2 ), 0x01 )
        self.assertEqual( self.memory.read_byte( self.cpu.STACK_PAGE + self.cpu.SP + 3 ), 0x10 )

    def test_RTI(self):
        self.memory.write_byte(self.cpu.STACK_PAGE + 0xFF, 0x12)
        self.memory.write_byte(self.cpu.STACK_PAGE + 0xFE, 0x33)
        self.memory.write_byte(self.cpu.STACK_PAGE + 0xFD, 0x20)
        self.cpu.SP = 0xFC
        self.cpu.RTI()
        self.assertEqual( self.cpu.PC, 0x1233 )
        self.assertEqual(self.cpu.status_as_byte(), 0x20)

    def test_NOP(self):
        self.cpu.NOP()
