import unittest
from papple2.Memory import Memory
from papple2.CPU import CPU


class TestArithmeticOperations(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.cpu = CPU(self.memory, None)

    def test_ADC_without_BCD(self):

        ## test cases from http://www.6502.org/tutorials/vflag.html

        # 1 + 1 = 2  (C = 0; V = 0)
        self.cpu.carry_flag = 0
        self.cpu.A = 0x01
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.ADC(0x1000)
        self.assertEqual( self.cpu.A, 0x02 )
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 0)

        # 1 + -1 = 0  (C = 1; V = 0)
        self.cpu.carry_flag = 0
        self.cpu.A = 0x01
        self.memory.write_byte(0x1000, 0xFF)
        self.cpu.ADC(0x1000)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.carry_flag, 1)
        self.assertEqual(self.cpu.overflow_flag, 0)

        # 127 + 1 = 128  (C = 0; V = 1)
        self.cpu.carry_flag = 0
        self.cpu.A = 0x7F
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.ADC(0x1000)
        self.assertEqual( self.cpu.A, 0x80 )  # @@@
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 1)

        # -128 + -1 = -129  (C = 1; V = 1)
        self.cpu.carry_flag = 0
        self.cpu.A = 0x80
        self.memory.write_byte(0x1000, 0xFF)
        self.cpu.ADC(0x1000)
        self.assertEqual( self.cpu.A, 0x7F )  # @@@
        self.assertEqual(self.cpu.carry_flag, 1)
        self.assertEqual(self.cpu.overflow_flag, 1)

        # 63 + 64 + 1 = 128  (C = 0; V = 1)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x3F
        self.memory.write_byte(0x1000, 0x40)
        self.cpu.ADC(0x1000)
        self.assertEqual( self.cpu.A, 0x80 )
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 1)

    def test_SBC_without_BCD(self):
        self.cpu.A = 0x02
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.carry_flag, 1)
        self.assertEqual(self.cpu.overflow_flag, 0)

        self.cpu.A = 0x01
        self.memory.write_byte(0x1000, 0x02)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 0)  # @@@

        ## test cases from http://www.6502.org/tutorials/vflag.html

        # 0 - 1 = -1  (V = 0)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x00
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0xFF )
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 0)  # @@@

        # -128 - 1 = -129  (V = 1)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x80
        self.memory.write_byte(0x1000, 0x01)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0x7F )
        self.assertEqual(self.cpu.carry_flag, 1)
        self.assertEqual(self.cpu.overflow_flag, 1)

        # 127 - -1 = 128  (V = 1)
        self.cpu.carry_flag = 1
        self.cpu.A = 0x7F
        self.memory.write_byte(0x1000, 0xFF)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0x80 )
        self.assertEqual(self.cpu.carry_flag, 0)
        self.assertEqual(self.cpu.overflow_flag, 1)

        # -64 -64 -1 = -129  (V = 1)
        self.cpu.carry_flag = 0
        self.cpu.A = 0xC0
        self.memory.write_byte(0x1000, 0x40)
        self.cpu.SBC(0x1000)
        self.assertEqual( self.cpu.A, 0x7F )
        self.assertEqual(self.cpu.carry_flag, 1)
        self.assertEqual(self.cpu.overflow_flag, 1)  # @@@

    ## @@@ BCD versions still to do

    def test_CMP(self):
        self.cpu.A = 0x0A
        self.memory.write_byte(0x1000, 0x09)
        self.cpu.CMP(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.A = 0x0A
        self.memory.write_byte(0x1000, 0x0B)
        self.cpu.CMP(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

        self.cpu.A = 0x0A
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CMP(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.A = 0xA0
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CMP(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.A = 0x0A
        self.memory.write_byte(0x1000, 0xA0)
        self.cpu.CMP(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)  # @@@
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

    def test_CPX(self):
        self.cpu.X = 0x0A
        self.memory.write_byte(0x1000, 0x09)
        self.cpu.CPX(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.X = 0x0A
        self.memory.write_byte(0x1000, 0x0B)
        self.cpu.CPX(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

        self.cpu.X = 0x0A
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CPX(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.X = 0xA0
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CPX(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.X = 0x0A
        self.memory.write_byte(0x1000, 0xA0)
        self.cpu.CPX(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)  # @@@
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

    def test_CPY(self):
        self.cpu.Y = 0x0A
        self.memory.write_byte(0x1000, 0x09)
        self.cpu.CPY(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.Y = 0x0A
        self.memory.write_byte(0x1000, 0x0B)
        self.cpu.CPY(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)

        self.cpu.Y = 0x0A
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CPY(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)
        self.assertEqual(self.cpu.zero_flag, 1)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.Y = 0xA0
        self.memory.write_byte(0x1000, 0x0A)
        self.cpu.CPY(0x1000)
        self.assertEqual(self.cpu.sign_flag, 1)
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 1)

        self.cpu.Y = 0x0A
        self.memory.write_byte(0x1000, 0xA0)
        self.cpu.CPY(0x1000)
        self.assertEqual(self.cpu.sign_flag, 0)  # @@@
        self.assertEqual(self.cpu.zero_flag, 0)
        self.assertEqual(self.cpu.carry_flag, 0)
