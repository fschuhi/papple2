"""The hook list in CPU: after_instruction, called at the end of
do_next_step(), in list order. A hook gets no arguments; it reads the
instruction count, the instruction's PC and the opcode from the CPU's
fields. See docs/instrumentation-design.md, section 4."""

from papple2.core.cpu import CPU
from papple2.core.memory import Memory

NOP = 0xEA
LDA_IMMEDIATE = 0xA9


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
