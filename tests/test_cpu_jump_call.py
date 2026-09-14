def test_JMP(cpu):
    cpu.JMP(0x1000)
    assert cpu.PC == 0x1000


def test_JSR(cpu, memory):
    cpu.PC = 0x1000
    cpu.JSR(0x2000)
    assert cpu.PC == 0x2000
    assert memory.read_byte(cpu.STACK_PAGE + cpu.SP + 1) == 0xFF
    assert memory.read_byte(cpu.STACK_PAGE + cpu.SP + 2) == 0x0F


def test_RTS(cpu, memory):
    memory.write_byte(cpu.STACK_PAGE + 0xFF, 0x12)
    memory.write_byte(cpu.STACK_PAGE + 0xFE, 0x33)
    cpu.SP = 0xFD
    cpu.RTS()
    assert cpu.PC == 0x1234


def test_JSR_and_RTS(cpu):
    cpu.PC = 0x1000
    cpu.JSR(0x2000)
    assert cpu.PC == 0x2000
    cpu.RTS()
    assert cpu.PC == 0x1000
