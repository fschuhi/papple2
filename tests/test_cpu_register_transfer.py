import pytest


@pytest.mark.parametrize("op, src_attr, dst_attr", [
    ("TAX", "A", "X"),
    ("TAY", "A", "Y"),
    ("TXA", "X", "A"),
    ("TYA", "Y", "A"),
])
def test_register_transfer(cpu, op, src_attr, dst_attr):
    for value, sign, zero in [(0x00, 0, 1), (0x01, 0, 0), (0xFF, 1, 0)]:
        setattr(cpu, src_attr, value)
        getattr(cpu, op)()
        assert getattr(cpu, dst_attr) == value
        assert cpu.sign_flag == sign
        assert cpu.zero_flag == zero
