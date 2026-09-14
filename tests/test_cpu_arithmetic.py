import pytest

# TODO: BCD versions missing/incomplete


@pytest.mark.parametrize("carry_in, a_before, operand, a_after, carry_out, overflow_out", [
    # test cases from http://www.6502.org/tutorials/vflag.html
    # 1 + 1 = 2  (C = 0; V = 0)
    (0, 0x01, 0x01, 0x02, 0, 0),
    # 1 + -1 = 0  (C = 1; V = 0)
    (0, 0x01, 0xFF, 0x00, 1, 0),
    # 127 + 1 = 128  (C = 0; V = 1)
    (0, 0x7F, 0x01, 0x80, 0, 1),
    # -128 + -1 = -129  (C = 1; V = 1)
    (0, 0x80, 0xFF, 0x7F, 1, 1),
    # 63 + 64 + 1 = 128  (C = 0; V = 1)
    (1, 0x3F, 0x40, 0x80, 0, 1),
])
def test_ADC_without_BCD(cpu, memory, carry_in, a_before, operand, a_after, carry_out, overflow_out):
    cpu.carry_flag = carry_in
    cpu.A = a_before
    memory.write_byte(0x1000, operand)
    cpu.ADC(0x1000)
    assert cpu.A == a_after
    assert cpu.carry_flag == carry_out
    assert cpu.overflow_flag == overflow_out


@pytest.mark.parametrize("carry_in, a_before, operand, a_after, carry_out, overflow_out", [
    (0, 0x02, 0x01, 0x00, 1, 0),
    (1, 0x01, 0x02, 0xFF, 0, 0),
    # test cases from http://www.6502.org/tutorials/vflag.html
    # 0 - 1 = -1  (V = 0)
    (1, 0x00, 0x01, 0xFF, 0, 0),
    # -128 - 1 = -129  (V = 1)
    (1, 0x80, 0x01, 0x7F, 1, 1),
    # 127 - -1 = 128  (V = 1)
    (1, 0x7F, 0xFF, 0x80, 0, 1),
    # -64 -64 -1 = -129  (V = 1)
    (0, 0xC0, 0x40, 0x7F, 1, 1),
])
def test_SBC_without_BCD(cpu, memory, carry_in, a_before, operand, a_after, carry_out, overflow_out):
    cpu.carry_flag = carry_in
    cpu.A = a_before
    memory.write_byte(0x1000, operand)
    cpu.SBC(0x1000)
    assert cpu.A == a_after
    assert cpu.carry_flag == carry_out
    assert cpu.overflow_flag == overflow_out


CMP_SEQUENCE = [
    (0x0A, 0x09, 0, 0, 1),
    (0x0A, 0x0B, 1, 0, 0),
    (0x0A, 0x0A, 0, 1, 1),
    (0xA0, 0x0A, 1, 0, 1),
    (0x0A, 0xA0, 0, 0, 0),
]


@pytest.mark.parametrize("op, reg_attr", [
    ("CMP", "A"),
    ("CPX", "X"),
    ("CPY", "Y"),
])
def test_compare_instruction(cpu, memory, op, reg_attr):
    for reg_value, operand, sign, zero, carry in CMP_SEQUENCE:
        setattr(cpu, reg_attr, reg_value)
        memory.write_byte(0x1000, operand)
        getattr(cpu, op)(0x1000)
        assert cpu.sign_flag == sign
        assert cpu.zero_flag == zero
        assert cpu.carry_flag == carry
