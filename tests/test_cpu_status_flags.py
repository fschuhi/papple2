import unittest
from papple2.Memory import Memory
from papple2.CPU import CPU


class TestStatusFlagOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_CLC(self):
        self.cpu.carry_flag = 1
        self.cpu.CLC()
        self.assertEqual(self.cpu.carry_flag, 0)

    def test_CLD(self):
        self.cpu.decimal_mode_flag = 1
        self.cpu.CLD()
        self.assertEqual(self.cpu.decimal_mode_flag, 0)

    def test_CLI(self):
        self.cpu.interrupt_disable_flag = 1
        self.cpu.CLI()
        self.assertEqual(self.cpu.interrupt_disable_flag, 0)

    def test_CLV(self):
        self.cpu.overflow_flag = 1
        self.cpu.CLV()
        self.assertEqual(self.cpu.overflow_flag, 0)

    def test_SEC(self):
        self.cpu.carry_flag = 0
        self.cpu.SEC()
        self.assertEqual(self.cpu.carry_flag, 1)

    def test_SED(self):
        self.cpu.decimal_mode_flag = 0
        self.cpu.SED()
        self.assertEqual(self.cpu.decimal_mode_flag, 1)

    def test_SEI(self):
        self.cpu.interrupt_disable_flag = 0
        self.cpu.SEI()
        self.assertEqual(self.cpu.interrupt_disable_flag, 1)
