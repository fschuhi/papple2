import unittest
from papple2.Memory import Memory
from papple2.CPU import CPU


class TestBranchOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_BCC(self):
        self.cpu.PC = 0x1000
        self.cpu.carry_flag = 1
        self.cpu.BCC(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.carry_flag = 0
        self.cpu.BCC(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BCS(self):
        self.cpu.PC = 0x1000
        self.cpu.carry_flag = 0
        self.cpu.BCS(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.carry_flag = 1
        self.cpu.BCS(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BEQ(self):
        self.cpu.PC = 0x1000
        self.cpu.zero_flag = 0
        self.cpu.BEQ(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.zero_flag = 1
        self.cpu.BEQ(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BMI(self):
        self.cpu.PC = 0x1000
        self.cpu.sign_flag = 0
        self.cpu.BMI(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.sign_flag = 1
        self.cpu.BMI(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BNE(self):
        self.cpu.PC = 0x1000
        self.cpu.zero_flag = 1
        self.cpu.BNE(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.zero_flag = 0
        self.cpu.BNE(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BPL(self):
        self.cpu.PC = 0x1000
        self.cpu.sign_flag = 1
        self.cpu.BPL(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.sign_flag = 0
        self.cpu.BPL(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BVC(self):
        self.cpu.PC = 0x1000
        self.cpu.overflow_flag = 1
        self.cpu.BVC(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.overflow_flag = 0
        self.cpu.BVC(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )

    def test_BVS(self):
        self.cpu.PC = 0x1000
        self.cpu.overflow_flag = 0
        self.cpu.BVS(0x2000)
        self.assertEqual( self.cpu.PC, 0x1000 )
        self.cpu.PC = 0x1000
        self.cpu.overflow_flag = 1
        self.cpu.BVS(0x2000)
        self.assertEqual( self.cpu.PC, 0x2000 )
