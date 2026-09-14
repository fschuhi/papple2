def test_ASL(cpu, memory):
    cpu.A = 0x01
    cpu.ASL()
    assert cpu.A == 0x02
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 0
    memory.write_byte(0x1000, 0x02)
    cpu.ASL(0x1000)
    assert memory.read_byte(0x1000) == 0x04
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 0
    cpu.A = 0x80
    cpu.ASL()
    assert cpu.A == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1


def test_LSR(cpu, memory):
    cpu.A = 0x01
    cpu.LSR()
    assert cpu.A == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    memory.write_byte(0x1000, 0x01)
    cpu.LSR(0x1000)
    assert memory.read_byte(0x1000) == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    cpu.A = 0x80
    cpu.LSR()
    assert cpu.A == 0x40
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 0


def test_ROL(cpu, memory):
    cpu.carry_flag = 0
    cpu.A = 0x80
    cpu.ROL()
    assert cpu.A == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    cpu.carry_flag = 1
    cpu.A = 0x80
    cpu.ROL()
    assert cpu.A == 0x01
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 1
    cpu.carry_flag = 0
    memory.write_byte(0x1000, 0x80)
    cpu.ROL(0x1000)
    assert memory.read_byte(0x1000) == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    cpu.carry_flag = 1
    memory.write_byte(0x1000, 0x80)
    cpu.ROL(0x1000)
    assert memory.read_byte(0x1000) == 0x01
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 1


def test_ROR(cpu, memory):
    cpu.carry_flag = 0
    cpu.A = 0x01
    cpu.ROR()
    assert cpu.A == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    cpu.carry_flag = 1
    cpu.A = 0x01
    cpu.ROR()
    assert cpu.A == 0x80
    assert cpu.sign_flag == 1
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 1
    cpu.carry_flag = 0
    memory.write_byte(0x1000, 0x01)
    cpu.ROR(0x1000)
    assert memory.read_byte(0x1000) == 0x00
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    assert cpu.carry_flag == 1
    cpu.carry_flag = 1
    memory.write_byte(0x1000, 0x01)
    cpu.ROR(0x1000)
    assert memory.read_byte(0x1000) == 0x80
    assert cpu.sign_flag == 1
    assert cpu.zero_flag == 0
    assert cpu.carry_flag == 1
