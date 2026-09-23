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


# -- decimal mode -------------------------------------------------------------

OPERAND = 0x0300


def _arith(cpu, memory, op, a, operand, carry, decimal=1):
    memory.load_test_data(OPERAND, [operand])
    cpu.A = a
    cpu.carry_flag = carry
    cpu.decimal_mode_flag = decimal
    getattr(cpu, op)(OPERAND)
    return cpu.A, cpu.carry_flag


@pytest.mark.parametrize(
    "a, operand, carry_in, expected, carry_out",
    [
        (0x19, 0x01, 0, 0x20, 0),  # digit carry into the tens
        (0x99, 0x01, 0, 0x00, 1),  # overflow past 99 sets carry
        (0x45, 0x55, 1, 0x01, 1),  # 45 + 55 + 1 = 101
        (0x12, 0x34, 0, 0x46, 0),  # no carries at all
    ],
)
def test_adc_decimal(cpu, memory, a, operand, carry_in, expected, carry_out):
    assert _arith(cpu, memory, "ADC", a, operand, carry_in) == (expected, carry_out)


@pytest.mark.parametrize(
    "a, operand, carry_in, expected, carry_out",
    [
        (0x20, 0x01, 1, 0x19, 1),  # borrow from the tens
        (0x00, 0x01, 1, 0x99, 0),  # underflow wraps to 99, carry clear = borrow
        (0x50, 0x25, 0, 0x24, 1),  # carry clear subtracts one more
        (0x46, 0x34, 1, 0x12, 1),  # no borrows at all
    ],
)
def test_sbc_decimal(cpu, memory, a, operand, carry_in, expected, carry_out):
    assert _arith(cpu, memory, "SBC", a, operand, carry_in) == (expected, carry_out)


def test_decimal_sets_zero_flag_from_result(cpu, memory):
    _arith(cpu, memory, "ADC", 0x99, 0x01, 0)

    assert cpu.zero_flag == 1


def test_binary_mode_unchanged(cpu, memory):
    # same operands as the first decimal case, but without SED
    assert _arith(cpu, memory, "ADC", 0x19, 0x01, 0, decimal=0) == (0x1A, 0)
