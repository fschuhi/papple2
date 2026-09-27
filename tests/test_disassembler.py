import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.debug.disassembler import Disassembler
from papple2.debug.labels import Labels

BNE = 0xD0


@pytest.fixture
def disassembler(memory: Memory, cpu: CPU) -> Disassembler:
    return Disassembler(cpu, Labels())


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


def test_every_address_is_code_by_default(
    memory: Memory, disassembler: Disassembler
) -> None:
    # Without an is_code function, every address is decoded as an
    # instruction: a plain static disassembler.
    memory.load_test_data(0x0300, [0xA9, 0x05, 0x60])  # LDA #$05 / RTS

    lines = disassembler.disassemble(0x0300, 0x0302)

    assert [line[3] for line in lines] == ["LDA", "RTS"]


def test_addresses_that_are_not_code_become_a_byte_block(
    memory: Memory, cpu: CPU
) -> None:
    # is_code decides code or data per address. Here nothing is code, so
    # the three bytes come out as one .byte line.
    disassembler = Disassembler(cpu, Labels(), is_code=lambda address: False)
    memory.load_test_data(0x0300, [0xA9, 0x05, 0x60])

    lines = disassembler.disassemble(0x0300, 0x0302)

    assert lines[-1][3:5] == [".byte", "a9 05 60"]
