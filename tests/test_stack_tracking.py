"""Tests for papple2.workbench.stack_tracking: the shadow stack.

Each test runs a small program with StackTracking attached and checks
how every frame ended. A row is (call site, entry, return site, return
target, outcome). Each program ends at DONE, or at the byte behind its
last instruction, where the run stops.

The programs keep their labels in column 0, as in conftest.py.
"""

from papple2.debug.stop_conditions import at_address
from papple2.workbench.stack_tracking import (
    ABANDONED,
    MATCHED,
    REDIRECTED,
    UNMATCHED,
    Return,
    StackTracking,
)


def track(make_emulator, program: str, end: int) -> StackTracking:
    """Run program until end with StackTracking attached."""
    _, emulator = make_emulator(program)
    tracking = StackTracking(emulator.cpu)
    emulator.attach(tracking)
    emulator.run(until=at_address(end))
    emulator.detach(tracking)
    return tracking


PLAIN_CALL = """
        *=$6000
        JSR SUB
        JMP DONE
SUB     RTS
DONE    NOP
"""


def test_a_plain_call_is_matched(make_emulator) -> None:
    tracking = track(make_emulator, PLAIN_CALL, end=0x6007)

    assert dict(tracking.returns) == {
        Return(0x6000, 0x6006, 0x6006, 0x6003, MATCHED): 1,
    }
    assert tracking.frames == {}


# TAIL ends in a JMP to SUB, whose RTS returns for TAIL.
TAIL_CALL = """
        *=$6000
        JSR TAIL
        JMP DONE
TAIL    JMP SUB
SUB     RTS
DONE    NOP
"""


def test_a_tail_call_is_matched_but_returns_from_another_routine(
    make_emulator,
) -> None:
    # The frame is opened for TAIL at 6006, and closed by SUB's RTS at
    # 6009: matched, since SUB returns where TAIL's caller expects.
    tracking = track(make_emulator, TAIL_CALL, end=0x600A)

    assert dict(tracking.returns) == {
        Return(0x6000, 0x6006, 0x6009, 0x6003, MATCHED): 1,
    }


# PHA/PHA/RTS: the two bytes are TARGET minus one, high byte first, as
# JSR would push them.
PUSHED_BY_HAND = """
        *=$6000
        LDA #$60
        PHA
        LDA #$06
        PHA
        RTS
TARGET  NOP
"""


def test_a_return_address_pushed_by_hand_is_unmatched(make_emulator) -> None:
    # No JSR opened a frame where the RTS lands.
    tracking = track(make_emulator, PUSHED_BY_HAND, end=0x6008)

    assert dict(tracking.returns) == {
        Return(None, None, 0x6006, 0x6007, UNMATCHED): 1,
    }


# SUB overwrites the low byte of its return address in page 1, so its RTS
# goes to OTHER (600c + 1) instead of behind the JSR.
REWRITTEN = """
        *=$6000
        JSR SUB
        JMP DONE
SUB     TSX
        LDA #$0c
        STA $0101,X
        RTS
OTHER   NOP
DONE    NOP
"""


def test_a_rewritten_return_address_is_redirected(make_emulator) -> None:
    tracking = track(make_emulator, REWRITTEN, end=0x600E)

    assert dict(tracking.returns) == {
        Return(0x6000, 0x6006, 0x600C, 0x600D, REDIRECTED): 1,
    }


# INNER pulls its own return address off the stack, so its RTS returns
# for OUTER, to OUTER's caller.
THROWN_AWAY = """
        *=$6000
        JSR OUTER
        JMP DONE
OUTER   JSR INNER
        RTS
INNER   PLA
        PLA
        RTS
DONE    NOP
"""


def test_a_return_address_thrown_away_abandons_its_frame(make_emulator) -> None:
    # INNER's frame can never return; OUTER's is matched, by INNER's RTS.
    tracking = track(make_emulator, THROWN_AWAY, end=0x600D)

    assert dict(tracking.returns) == {
        Return(0x6006, 0x600A, None, None, ABANDONED): 1,
        Return(0x6000, 0x6006, 0x600C, 0x6003, MATCHED): 1,
    }
    assert tracking.frames == {}
