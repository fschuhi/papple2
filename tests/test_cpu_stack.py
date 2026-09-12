import pytest


@pytest.mark.parametrize("sp, expected_x, expected_sign, expected_zero", [
    (0x00, 0x00, 0, 1),
    (0x01, 0x01, 0, 0),
    (0xFF, 0xFF, 1, 0),
])
def test_TSX(cpu, sp, expected_x, expected_sign, expected_zero):
    cpu.SP = sp
    cpu.TSX()
    assert cpu.X == expected_x
    assert cpu.sign_flag == expected_sign
    assert cpu.zero_flag == expected_zero


def test_TXS(cpu):
    x = cpu.X
    cpu.TXS()
    assert cpu.SP == x


def test_PHA_and_PLA(cpu):
    cpu.A = 0x00
    cpu.PHA()
    cpu.A = 0x01
    cpu.PHA()
    cpu.A = 0xFF
    cpu.PHA()
    assert cpu.A == 0xFF
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 0

    cpu.PLA()
    assert cpu.A == 0xFF
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 1

    cpu.PLA()
    assert cpu.A == 0x01
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 0

    cpu.PLA()
    assert cpu.A == 0x00
    assert cpu.zero_flag == 1
    assert cpu.sign_flag == 0


def test_PHP_and_PLP(cpu):
    p = cpu.status_as_byte()
    cpu.PHP()
    cpu.status_from_byte(0xFF)
    cpu.PLP()
    assert cpu.status_as_byte() == p
