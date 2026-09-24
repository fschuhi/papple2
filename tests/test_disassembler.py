import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.debug.disassembler import Disassembler
from papple2.debug.labels import Labels
from papple2.debug.memory_map import MemoryMap

BNE = 0xD0


@pytest.fixture
def disassembler(memory: Memory, cpu: CPU) -> Disassembler:
    return Disassembler(cpu, MemoryMap(memory), Labels())


@pytest.mark.parametrize(
    "offset, target",
    [
        (0x00, 0x1002),  # no jump: the instruction right after the branch
        (0x7E, 0x1080),  # the two longest forward branches, which used to
        (0x7F, 0x1081),  # come out as backward jumps ($0F80, $0F81)
        (0x80, 0x0F82),  # the longest backward branch
        (0xFE, 0x1000),  # back to the branch itself: an endless loop
    ],
)
def test_branch_target(
    memory: Memory, disassembler: Disassembler, offset: int, target: int
) -> None:
    # The 6502 counts a branch offset from the instruction *after* the
    # two-byte branch: target = address + 2 + signed(offset).
    memory.load_test_data(0x1000, [BNE, offset])

    info, length = disassembler.collect_op_info(0x1000)

    assert length == 2
    assert info["operand_address"] == target


def test_disassembling_leaves_the_softswitches_on(
    memory: Memory, disassembler: Disassembler
) -> None:
    # A plain Memory has no Apple II, so its softswitch flag starts off.
    # Switch it on by hand: the instruction below never touches $C0xx,
    # so the missing Apple II is never asked for anything.
    memory.use_apple_softswitches = True
    memory.load_test_data(0x0300, [0xAD, 0x00, 0x04])  # LDA $0400

    disassembler.collect_op_info(0x0300)

    assert memory.use_apple_softswitches
