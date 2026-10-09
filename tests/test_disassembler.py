import pytest

from papple2.core.cpu import CPU
from papple2.core.memory import Memory
from papple2.debug.disassembler import Disassembler

BNE = 0xD0


@pytest.fixture
def disassembler(memory: Memory, cpu: CPU) -> Disassembler:
    return Disassembler(cpu)


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
    disassembler = Disassembler(cpu, is_code=lambda address: False)
    memory.load_test_data(0x0300, [0xA9, 0x05, 0x60])

    lines = disassembler.disassemble(0x0300, 0x0302)

    assert lines[-1][3:5] == [".byte", "a9 05 60"]


def test_a_named_address_fills_the_label_column(
    memory: Memory, cpu: CPU
) -> None:
    # The label column holds the name of the instruction's own address;
    # addresses without a name leave it empty.
    disassembler = Disassembler(cpu, {0x0300: "START"})
    memory.load_test_data(0x0300, [0xA9, 0x05, 0x60])  # LDA #$05 / RTS

    lines = disassembler.disassemble(0x0300, 0x0302)

    assert [line[2] for line in lines] == ["START", ""]


@pytest.mark.parametrize(
    "program, operand",
    [
        ([0xE6, 0x10], "COUNT"),  # INC $10: zero page, two digits
        ([0xB1, 0x10], "(COUNT),Y"),  # LDA ($10),Y: brackets and index stay
        ([0xAD, 0x10, 0x00], "COUNT"),  # LDA $0010: absolute, four digits
    ],
)
def test_a_label_replaces_the_address_in_the_operand(
    memory: Memory, cpu: CPU, program: list[int], operand: str
) -> None:
    # The zero-page modes print an address with two digits, the others
    # with four; the label replaces whichever the mode printed.
    disassembler = Disassembler(cpu, {0x0010: "COUNT"})
    memory.load_test_data(0x0300, program)

    lines = disassembler.disassemble(0x0300, instructions=1)

    assert lines[0][4] == operand


def test_a_commented_address_fills_the_comment_column(
    memory: Memory, cpu: CPU
) -> None:
    # The comment column holds the comment of the instruction's own
    # address; addresses without a comment leave it empty.
    disassembler = Disassembler(cpu, comments={0x0300: "five lives"})
    memory.load_test_data(0x0300, [0xA9, 0x05, 0x60])  # LDA #$05 / RTS

    lines = disassembler.disassemble(0x0300, 0x0302)

    assert [line[5] for line in lines] == ["five lives", ""]


# Code that changes itself: STA $0312 at $0300 writes into the operand of
# LDA $a500,Y at $0310, labelled SELFMOD. $0311 is its low byte, $0312 its
# high byte.
SELF_MODIFYING = {
    0x0300: [0x8D, 0x12, 0x03],  # STA $0312
    0x0310: [0xB9, 0x00, 0xA5],  # SELFMOD: LDA $a500,Y
}


def load(memory: Memory, program: dict[int, list[int]]) -> None:
    for address, data in program.items():
        memory.load_test_data(address, data)


@pytest.mark.parametrize(
    "low_byte, operand", [(0x11, "SELFMOD+1"), (0x12, "SELFMOD+2")]
)
def test_an_operand_inside_a_labelled_instruction_that_ran_shows_an_offset(
    memory: Memory, cpu: CPU, low_byte: int, operand: str
) -> None:
    load(memory, SELF_MODIFYING)
    memory.load_test_data(0x0301, [low_byte])
    disassembler = Disassembler(cpu, {0x0310: "SELFMOD"}, ran=lambda address: True)

    lines = disassembler.disassemble(0x0300, instructions=1)

    assert lines[0][4] == operand


def test_a_label_of_its_own_wins_over_an_offset(memory: Memory, cpu: CPU) -> None:
    load(memory, SELF_MODIFYING)
    disassembler = Disassembler(
        cpu, {0x0310: "SELFMOD", 0x0312: "HIGH"}, ran=lambda address: True
    )

    lines = disassembler.disassemble(0x0300, instructions=1)

    assert lines[0][4] == "HIGH"


def test_no_offset_into_a_labelled_byte_that_never_ran(
    memory: Memory, cpu: CPU
) -> None:
    # As in Lode Runner's zero page: $1e is sprite_num, a data byte. Read
    # as an opcode, $b9 would make a three-byte instruction reaching $1f.
    # Without a run that executed $1e, STA $1f stays as it is.
    memory.load_test_data(0x001E, [0xB9])
    memory.load_test_data(0x0300, [0x85, 0x1F])  # STA $1f
    disassembler = Disassembler(cpu, {0x001E: "sprite_num"})

    lines = disassembler.disassemble(0x0300, instructions=1)

    assert lines[0][4] == "$1f"
