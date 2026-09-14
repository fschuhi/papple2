import pytest


@pytest.mark.parametrize("op, flag_attr, non_branching_value, branching_value", [
    ("BCC", "carry_flag", 1, 0),
    ("BCS", "carry_flag", 0, 1),
    ("BEQ", "zero_flag", 0, 1),
    ("BMI", "sign_flag", 0, 1),
    ("BNE", "zero_flag", 1, 0),
    ("BPL", "sign_flag", 1, 0),
    ("BVC", "overflow_flag", 1, 0),
    ("BVS", "overflow_flag", 0, 1),
])
def test_branch_instruction(cpu, op, flag_attr, non_branching_value, branching_value):
    cpu.PC = 0x1000
    setattr(cpu, flag_attr, non_branching_value)
    getattr(cpu, op)(0x2000)
    assert cpu.PC == 0x1000

    cpu.PC = 0x1000
    setattr(cpu, flag_attr, branching_value)
    getattr(cpu, op)(0x2000)
    assert cpu.PC == 0x2000
