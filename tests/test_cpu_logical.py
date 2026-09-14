def test_AND(cpu, memory):
    memory.write_byte(0x1000, 0x37)
    cpu.A = 0x34
    cpu.AND(0x1000)
    assert cpu.A == 0x34
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 0
    cpu.A = 0x40
    cpu.AND(0x1000)
    assert cpu.A == 0x00
    assert cpu.zero_flag == 1
    assert cpu.sign_flag == 0


def test_EOR(cpu, memory):
    memory.write_byte(0x1000, 0x37)
    cpu.A = 0x34
    cpu.EOR(0x1000)
    assert cpu.A == 0x03
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 0
    cpu.A = 0x90
    cpu.EOR(0x1000)
    assert cpu.A == 0xA7
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 1
    cpu.A = 0x37
    cpu.EOR(0x1000)
    assert cpu.A == 0x00
    assert cpu.zero_flag == 1
    assert cpu.sign_flag == 0


def test_ORA(cpu, memory):
    memory.write_byte(0x1000, 0x37)
    cpu.A = 0x34
    cpu.ORA(0x1000)
    assert cpu.A == 0x37
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 0
    cpu.A = 0x90
    cpu.ORA(0x1000)
    assert cpu.A == 0xB7
    assert cpu.zero_flag == 0
    assert cpu.sign_flag == 1
    cpu.A = 0x00
    cpu.ORA(0x1001)
    assert cpu.A == 0x00
    assert cpu.zero_flag == 1
    assert cpu.sign_flag == 0


def test_BIT(cpu, memory):
    memory.write_byte(0x1000, 0x00)
    cpu.A = 0x00
    cpu.BIT(0x1000)
    assert cpu.overflow_flag == 0
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    memory.write_byte(0x1000, 0x40)
    cpu.A = 0x00
    cpu.BIT(0x1000)
    assert cpu.overflow_flag == 1
    assert cpu.sign_flag == 0
    assert cpu.zero_flag == 1
    memory.write_byte(0x1000, 0x80)
    cpu.A = 0x00
    cpu.BIT(0x1000)
    assert cpu.overflow_flag == 0
    assert cpu.sign_flag == 1
    assert cpu.zero_flag == 1
    memory.write_byte(0x1000, 0xC0)
    cpu.A = 0x00
    cpu.BIT(0x1000)
    assert cpu.overflow_flag == 1
    assert cpu.sign_flag == 1
    assert cpu.zero_flag == 1
    memory.write_byte(0x1000, 0xC0)
    cpu.A = 0xC0
    cpu.BIT(0x1000)
    assert cpu.overflow_flag == 1
    assert cpu.sign_flag == 1
    assert cpu.zero_flag == 0
