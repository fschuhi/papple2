import pytest

INCREMENT_SEQUENCE = [
    (0x00, 0x01, 0, 0),
    (0x7F, 0x80, 1, 0),
    (0xFF, 0x00, 0, 1),
]

DECREMENT_SEQUENCE = [
    (0x01, 0x00, 0, 1),
    (0x80, 0x7F, 0, 0),
    (0x00, 0xFF, 1, 0),
]


@pytest.mark.parametrize("op, reg_attr, sequence", [
    ("INX", "X", INCREMENT_SEQUENCE),
    ("INY", "Y", INCREMENT_SEQUENCE),
    ("DEX", "X", DECREMENT_SEQUENCE),
    ("DEY", "Y", DECREMENT_SEQUENCE),
])
def test_register_inc_dec(cpu, op, reg_attr, sequence):
    for before, after, sign, zero in sequence:
        setattr(cpu, reg_attr, before)
        getattr(cpu, op)()
        assert getattr(cpu, reg_attr) == after
        assert cpu.sign_flag == sign
        assert cpu.zero_flag == zero


@pytest.mark.parametrize("op, sequence", [
    ("INC", INCREMENT_SEQUENCE),
    ("DEC", DECREMENT_SEQUENCE),
])
def test_memory_inc_dec(cpu, memory, op, sequence):
    for before, after, sign, zero in sequence:
        memory.write_byte(0x1000, before)
        getattr(cpu, op)(0x1000)
        assert memory.read_byte(0x1000) == after
        assert cpu.sign_flag == sign
        assert cpu.zero_flag == zero
