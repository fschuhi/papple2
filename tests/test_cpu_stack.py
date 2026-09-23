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


# -- stack wrap -------------------------------------------------------------

def test_rts_with_sp_at_ff_pulls_from_bottom_of_page_1(cpu, memory):
    # return address $1233 on the stack, so RTS continues at $1234
    memory.load_test_data(0x0100, [0x33, 0x12])
    cpu.SP = 0xFF

    cpu.RTS()

    assert cpu.PC == 0x1234
    assert cpu.SP == 0x01


def test_jsr_and_rts_round_trip_across_the_wrap(cpu):
    # with SP=$00, JSR pushes the high byte to $0100 and the low byte to $01FF
    cpu.SP = 0x00
    cpu.PC = 0x6003
    cpu.JSR(0x7000)

    assert cpu.SP == 0xFE

    cpu.RTS()

    assert cpu.PC == 0x6003
    assert cpu.SP == 0x00


def test_rti_with_wrap_pulls_status_then_address(cpu, memory):
    # status at $01FF, return address $4567 at $0100/$0101
    memory.load_test_data(0x01FF, [0x01])  # carry set
    memory.load_test_data(0x0100, [0x67, 0x45])
    cpu.SP = 0xFE

    cpu.RTI()

    assert cpu.PC == 0x4567
    assert cpu.carry_flag == 1
    assert cpu.SP == 0x01
