import unittest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU


class TestJumpCallOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_JMP(self):
        self.cpu.JMP(0x1000)
        self.assertEqual( self.cpu.PC, 0x1000 )

    def test_JSR(self):
        self.cpu.PC = 0x1000
        self.cpu.JSR(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )
        self.assertEqual( self.memory.read_byte( self.cpu.STACK_PAGE + self.cpu.SP + 1 ), 0xFF )
        self.assertEqual( self.memory.read_byte( self.cpu.STACK_PAGE + self.cpu.SP + 2 ), 0x0F )

    def test_RTS(self):
        self.memory.write_byte(self.cpu.STACK_PAGE + 0xFF, 0x12)
        self.memory.write_byte(self.cpu.STACK_PAGE + 0xFE, 0x33)
        self.cpu.SP = 0xFD
        self.cpu.RTS()
        self.assertEqual( self.cpu.PC, 0x1234 )

    def test_JSR_and_RTS(self):
        self.cpu.PC = 0x1000
        self.cpu.JSR(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )
        self.cpu.RTS()
        self.assertEqual( self.cpu.PC, 0x1000 )
