def test_zero_page_x(cpu, memory):
    cpu.X = 0x01
    memory.load_test_data(0x1000, [0x00, 0x7F, 0xFF])
    cpu.PC = 0x1000
    assert cpu.zero_page_x_mode() == 0x01
    assert cpu.zero_page_x_mode() == 0x80
    assert cpu.zero_page_x_mode() == 0x00


def test_indirect(cpu, memory):
    memory.load_test_data(0x20, [0x00, 0x20])
    memory.load_test_data(0x00, [0x12])
    memory.load_test_data(0xFF, [0x34])
    memory.load_test_data(0x100, [0x56])
    memory.load_test_data(0x1000, [0x20, 0x20, 0xFF, 0xFF, 0x00, 0x45, 0x23])
    memory.load_test_data(0x2000, [0x05])
    memory.load_test_data(0x1234, [0x05])
    memory.load_test_data(0x2345, [0x00, 0xF0])

    cpu.PC = 0x1000

    cpu.X = 0x00
    cpu.LDA(cpu.indirect_x_mode())
    assert cpu.A == 0x05

    cpu.Y = 0x00
    cpu.LDA(cpu.indirect_y_mode())
    assert cpu.A == 0x05

    cpu.Y = 0x00
    cpu.LDA(cpu.indirect_y_mode())
    assert cpu.A == 0x05

    cpu.X = 0x00
    cpu.LDA(cpu.indirect_x_mode())
    assert cpu.A == 0x05

    cpu.X = 0xFF
    cpu.LDA(cpu.indirect_x_mode())
    assert cpu.A == 0x05

    assert cpu.indirect_mode() == 0xF000
