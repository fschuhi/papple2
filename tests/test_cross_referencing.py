"""Tests for papple2.workbench.cross_referencing: what each kind of access
gives in the report.

Each test runs a small program with CrossReferencing attached and checks
its rows: (instruction, kind, target, effective address), each with how
often, and the indexes, values and old values seen, sorted. The
walkthrough's memory_tour (chapters 18 to 22 of tests/test_walkthrough.py)
shows the common cases; these are the rest.

The programs keep their labels in column 0, as in conftest.py.
"""

from papple2.debug.stop_conditions import at_address
from papple2.workbench.cross_referencing import (
    READ_DATA,
    READ_IMMEDIATE,
    READ_POINTER,
    WRITE_DATA,
    CrossReferencing,
    Xref,
)


def xrefs(
    make_emulator, program: str, end: int, preload: dict[int, int] | None = None
) -> dict[Xref, tuple[int, list[int], list[int], list[int]]]:
    """Run program until end with CrossReferencing attached; its rows, each
    with (count, indexes, values, old values)."""
    _, emulator = make_emulator(program, preload)
    cross_referencing = CrossReferencing(emulator.cpu)
    emulator.attach(cross_referencing)
    emulator.run(until=at_address(end))
    emulator.detach(cross_referencing)
    return {
        xref: (
            tally.count,
            sorted(tally.indexes),
            sorted(tally.values),
            sorted(tally.old_values),
        )
        for xref, tally in cross_referencing.tallies.items()
    }


INDIRECT_X = """
        *=$6000
        LDX #$02
        LDA ($04,X)
"""


def test_indirect_x_adds_x_to_find_the_pointer_not_the_data(make_emulator) -> None:
    # ($04,X) with X = 2 reads the pointer at $06 and $07, which points at
    # $0300. X is the index of the pointer's rows; the data row has none:
    # its address came from the pointer.
    rows = xrefs(
        make_emulator,
        INDIRECT_X,
        end=0x6004,
        preload={0x06: 0x00, 0x07: 0x03, 0x0300: 0x42},
    )

    assert rows == {
        Xref(0x6000, READ_IMMEDIATE, None, 0x6001): (1, [], [0x02], []),
        Xref(0x6002, READ_POINTER, 0x04, 0x06): (1, [0x02], [0x00], []),
        Xref(0x6002, READ_POINTER, 0x04, 0x07): (1, [0x02], [0x03], []),
        Xref(0x6002, READ_DATA, 0x04, 0x0300): (1, [], [0x42], []),
    }


ZERO_PAGE_X = """
        *=$6000
        LDX #$02
        LDA $FF,X
"""


def test_zero_page_x_wraps_within_zero_page(make_emulator) -> None:
    # $FF + 2 wraps to $01, not $0101: the target stays $ff, the byte
    # touched is $01.
    rows = xrefs(make_emulator, ZERO_PAGE_X, end=0x6004, preload={0x01: 0x42})

    assert rows[Xref(0x6002, READ_DATA, 0xFF, 0x01)] == (1, [0x02], [0x42], [])


JMP_INDIRECT = """
        *=$6000
        JMP ($0010)
        NOP
DONE    NOP
"""


def test_jmp_indirect_reads_a_pointer_and_no_data(make_emulator) -> None:
    # JMP ($0010) reads its pointer, $6004, and jumps there: two pointer
    # rows, and no data row, since a jump reads nothing at its target.
    rows = xrefs(
        make_emulator, JMP_INDIRECT, end=0x6004, preload={0x10: 0x04, 0x11: 0x60}
    )

    assert rows == {
        Xref(0x6000, READ_POINTER, 0x0010, 0x0010): (1, [], [0x04], []),
        Xref(0x6000, READ_POINTER, 0x0010, 0x0011): (1, [], [0x60], []),
    }


CALL_AND_STACK = """
        *=$6000
        JSR SUB
        JMP DONE
SUB     PHA
        PLA
        RTS
DONE    NOP
"""


def test_calls_and_the_stack_give_no_rows(make_emulator) -> None:
    # JSR and JMP name an address but read nothing there; PHA, PLA and the
    # return address go through the stack's own hooks. Opcode and operand
    # fetches are not counted either: Tiling knows what ran.
    rows = xrefs(make_emulator, CALL_AND_STACK, end=0x6009)

    assert rows == {}


WRITES_ITS_OWN_OPERAND = """
        *=$6000
        INC $6001
"""


def test_an_instruction_writing_its_own_operand_counts_the_write_under_the_new_target(
    make_emulator,
) -> None:
    # The known limit: INC $6001 increments the low byte of its own
    # operand, $01 to $02. The write hook runs after the write, so the
    # target it reads is already the new one, $6002.
    rows = xrefs(make_emulator, WRITES_ITS_OWN_OPERAND, end=0x6003)

    assert rows == {
        Xref(0x6000, READ_DATA, 0x6001, 0x6001): (1, [], [0x01], []),
        Xref(0x6000, WRITE_DATA, 0x6002, 0x6001): (1, [], [0x02], [0x01]),
    }
