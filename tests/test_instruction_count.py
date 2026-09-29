from papple2.core.cpu import CPU
from papple2.core.memory import Memory

# The instruction count lives in CPU and is reset only at a fresh start, like
# cycles (docs/instrumentation-design.md, section 5). It is not
# Emulator.instructions, which every run() call resets.

NOP = 0xEA


def test_instruction_count_starts_at_zero(cpu: CPU) -> None:
    assert cpu.instruction_count == 0


def test_each_instruction_adds_one(cpu: CPU, memory: Memory) -> None:
    memory.load_test_data(0x1000, [NOP, NOP, NOP])
    cpu.PC = 0x1000

    for _ in range(3):
        cpu.do_next_step()

    assert cpu.instruction_count == 3


def test_reset_zeroes_the_instruction_count(cpu: CPU, memory: Memory) -> None:
    memory.load_test_data(0x1000, [NOP])
    cpu.PC = 0x1000
    cpu.do_next_step()

    cpu.reset()

    assert cpu.instruction_count == 0
