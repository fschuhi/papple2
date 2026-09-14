import pytest


@pytest.fixture
def loaded_memory(memory):
    memory.load_test_data(0x1000, [0x00, 0x01, 0x7F, 0x80, 0xFF])
    return memory


@pytest.mark.parametrize("op, reg_attr", [
    ("LDA", "A"),
    ("LDX", "X"),
    ("LDY", "Y"),
])
def test_load_instruction(cpu, loaded_memory, op, reg_attr):
    for addr, value, sign, zero in [
        (0x1000, 0x00, 0, 1),
        (0x1001, 0x01, 0, 0),
        (0x1002, 0x7F, 0, 0),
        (0x1003, 0x80, 1, 0),
        (0x1004, 0xFF, 1, 0),
    ]:
        getattr(cpu, op)(addr)
        assert getattr(cpu, reg_attr) == value
        assert cpu.sign_flag == sign
        assert cpu.zero_flag == zero


@pytest.mark.parametrize("op, reg_attr, value", [
    ("STA", "A", 0x37),
    ("STX", "X", 0x38),
    ("STY", "Y", 0x39),
])
def test_store_instruction(cpu, memory, op, reg_attr, value):
    setattr(cpu, reg_attr, value)
    getattr(cpu, op)(0x2000)
    assert memory.read_byte(0x2000) == value
