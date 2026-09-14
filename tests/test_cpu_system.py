def test_BRK(cpu, memory):
    cpu.PC = 0x1000
    memory.load_test_data(0xFFFE, [0x00, 0x20])
    status = cpu.status_as_byte()
    cpu.BRK()
    assert cpu.PC == 0x2000
    assert cpu.break_flag == 1
    assert memory.read_byte(cpu.STACK_PAGE + cpu.SP + 1) == status
    assert memory.read_byte(cpu.STACK_PAGE + cpu.SP + 2) == 0x01
    assert memory.read_byte(cpu.STACK_PAGE + cpu.SP + 3) == 0x10


def test_RTI(cpu, memory):
    memory.write_byte(cpu.STACK_PAGE + 0xFF, 0x12)
    memory.write_byte(cpu.STACK_PAGE + 0xFE, 0x33)
    memory.write_byte(cpu.STACK_PAGE + 0xFD, 0x20)
    cpu.SP = 0xFC
    cpu.RTI()
    assert cpu.PC == 0x1233
    assert cpu.status_as_byte() == 0x20


def test_NOP(cpu):
    cpu.NOP()
