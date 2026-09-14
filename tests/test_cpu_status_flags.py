import pytest


@pytest.mark.parametrize("op, flag_attr, before, after", [
    ("CLC", "carry_flag", 1, 0),
    ("CLD", "decimal_mode_flag", 1, 0),
    ("CLI", "interrupt_disable_flag", 1, 0),
    ("CLV", "overflow_flag", 1, 0),
    ("SEC", "carry_flag", 0, 1),
    ("SED", "decimal_mode_flag", 0, 1),
    ("SEI", "interrupt_disable_flag", 0, 1),
])
def test_flag_instruction(cpu, op, flag_attr, before, after):
    setattr(cpu, flag_attr, before)
    getattr(cpu, op)()
    assert getattr(cpu, flag_attr) == after
