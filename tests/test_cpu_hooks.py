"""The hook list in CPU: after_instruction, called at the end of
do_next_step(), in list order. A hook gets no arguments; it reads the
instruction count, the instruction's PC and the opcode from the CPU's
fields. See docs/instrumentation-design.md, section 4."""

import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory

NOP = 0xEA
LDA_IMMEDIATE = 0xA9
LDA_ABSOLUTE = 0xAD


def test_a_hook_sees_the_instruction_it_follows(cpu: CPU, memory: Memory) -> None:
    # NOP at $1000, LDA #$42 at $1001
    memory.load_test_data(0x1000, [NOP, LDA_IMMEDIATE, 0x42])
    cpu.PC = 0x1000
    seen = []
    cpu.after_instruction.append(
        lambda: seen.append((cpu.instruction_count, cpu.last_PC, cpu.last_opcode, cpu.A))
    )

    cpu.do_next_step()
    cpu.do_next_step()

    # A is already $42 in the second call: the hook runs after the instruction
    assert seen == [(1, 0x1000, NOP, 0x00), (2, 0x1001, LDA_IMMEDIATE, 0x42)]


def test_a_hook_is_called_once_per_instruction(cpu: CPU, memory: Memory) -> None:
    memory.load_test_data(0x1000, [NOP, NOP, NOP])
    cpu.PC = 0x1000
    calls = []
    cpu.after_instruction.append(lambda: calls.append(cpu.last_PC))

    for _ in range(3):
        cpu.do_next_step()

    assert calls == [0x1000, 0x1001, 0x1002]


def test_hooks_run_in_list_order(cpu: CPU, memory: Memory) -> None:
    memory.load_test_data(0x1000, [NOP])
    cpu.PC = 0x1000
    order = []
    cpu.after_instruction.append(lambda: order.append("first"))
    cpu.after_instruction.append(lambda: order.append("second"))

    cpu.do_next_step()

    assert order == ["first", "second"]


def test_reset_keeps_the_hooks(cpu: CPU) -> None:
    def hook() -> None:
        pass

    cpu.after_instruction.append(hook)

    cpu.reset()

    assert cpu.after_instruction == [hook]


# Which kind of read the CPU reports: an immediate operand goes to
# Memory.after_read_immediate, every other operand byte the operation reads
# goes to after_read_data. See docs/instrumentation-design.md, section 3.

# One case per place in cpu.py that reads through read_data_or_immediate():
# the 11 opcodes with immediate mode, and ADC and SBC once more in decimal
# mode, which reads in a branch of its own.
IMMEDIATE_CASES = [
    pytest.param(0x09, False, id="ORA"),
    pytest.param(0x29, False, id="AND"),
    pytest.param(0x49, False, id="EOR"),
    pytest.param(0x69, False, id="ADC"),
    pytest.param(0x69, True, id="ADC decimal"),
    pytest.param(0xA0, False, id="LDY"),
    pytest.param(0xA2, False, id="LDX"),
    pytest.param(0xA9, False, id="LDA"),
    pytest.param(0xC0, False, id="CPY"),
    pytest.param(0xC9, False, id="CMP"),
    pytest.param(0xE0, False, id="CPX"),
    pytest.param(0xE9, False, id="SBC"),
    pytest.param(0xE9, True, id="SBC decimal"),
]


@pytest.mark.parametrize("opcode, decimal", IMMEDIATE_CASES)
def test_an_immediate_operand_is_reported_as_immediate(
    cpu: CPU, memory: Memory, opcode: int, decimal: bool
) -> None:
    memory.load_test_data(0x1000, [opcode, 0x42])
    cpu.PC = 0x1000
    cpu.decimal_mode_flag = int(decimal)
    immediate = []
    data = []
    memory.after_read_immediate.append(lambda address, value: immediate.append((address, value)))
    memory.after_read_data.append(lambda address, value: data.append((address, value)))

    cpu.do_next_step()

    assert immediate == [(0x1001, 0x42)]
    assert data == []


def test_the_next_instruction_reads_data_again(cpu: CPU, memory: Memory) -> None:
    # LDA #$42 at $1000, LDA $0300 at $1002; $0300 holds $07
    memory.load_test_data(0x1000, [LDA_IMMEDIATE, 0x42, LDA_ABSOLUTE, 0x00, 0x03])
    memory.load_test_data(0x0300, [0x07])
    cpu.PC = 0x1000
    immediate = []
    data = []
    memory.after_read_immediate.append(lambda address, value: immediate.append((address, value)))
    memory.after_read_data.append(lambda address, value: data.append((address, value)))

    cpu.do_next_step()
    cpu.do_next_step()

    # do_next_step() resets the flag, so the second LDA reads data
    assert immediate == [(0x1001, 0x42)]
    assert data == [(0x0300, 0x07)]
    assert cpu.A == 0x07
