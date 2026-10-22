"""Tests for papple2.workbench.stack_tracking: the shadow stack.

Each test runs a small program with StackTracking attached and checks
how every frame ended. A row is (call site, entry, return site, return
target, outcome). Each program ends at DONE, or at the byte after its
last instruction, where the run stops.

The programs keep their labels in column 0, as in conftest.py.
"""

from pathlib import Path

from papple2.debug.stop_conditions import at_address, instruction_count_reaches
from papple2.workbench.stack_tracking import (
    ABANDONED,
    MATCHED,
    REDIRECTED,
    RETURNS_FILE,
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
# goes to OTHER (600c + 1) instead of directly after the JSR.
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


# PUTS takes its return address off the stack into zero page, as
# PUT_STRING does, and moves it past the byte after the JSR, TEXT. While
# the address is off the stack, it calls CHAR, whose JSR pushes into the
# same two bytes of page 1. Then PUTS pushes the moved address back, and
# its RTS goes to 6004, after TEXT, instead of 6003.
PAYLOAD = """
        *=$6000
        JSR PUTS
TEXT    .BYTE $00
        JMP DONE
PUTS    PLA
        STA $10
        PLA
        STA $11
        INC $10
        JSR CHAR
        LDA $11
        PHA
        LDA $10
        PHA
        RTS
CHAR    RTS
DONE    NOP
"""


def test_a_call_made_while_the_return_address_is_off_the_stack_keeps_the_frame(
    make_emulator,
) -> None:
    # CHAR's frame lies on top of PUTS's frame, at the same SP. CHAR's
    # RTS closes its own frame; PUTS's RTS then finds PUTS's frame, and
    # lands after the payload: redirected, not unmatched.
    tracking = track(make_emulator, PAYLOAD, end=0x601A)

    assert dict(tracking.returns) == {
        Return(0x600F, 0x6019, 0x6019, 0x6012, MATCHED): 1,
        Return(0x6000, 0x6007, 0x6018, 0x6004, REDIRECTED): 1,
    }
    assert tracking.frames == {}


def report_lines(folder: Path) -> list[str]:
    return (folder / RETURNS_FILE).read_text(encoding="utf-8").splitlines()


def test_the_report_puts_the_abandoned_before_the_matched(make_emulator, tmp_path: Path) -> None:
    # The abandoned frame comes before the matched return, though its
    # addresses are higher.
    tracking = track(make_emulator, THROWN_AWAY, end=0x600D)

    tracking.write_reports(tmp_path)

    assert report_lines(tmp_path) == [
        "call_site,entry,return_site,return_target,outcome,count",
        "6006,600a,,,abandoned,1",
        "6000,6006,600c,6003,matched,1",
    ]


# WAIT never returns, so its frame is still open when the run stops.
NEVER_RETURNS = """
        *=$6000
        JSR WAIT
        NOP
WAIT    JMP WAIT
"""


def test_a_frame_still_open_is_reported_as_open(
    make_emulator, tmp_path: Path
) -> None:
    _, emulator = make_emulator(NEVER_RETURNS)
    tracking = StackTracking(emulator.cpu)
    emulator.attach(tracking)
    emulator.run(until=instruction_count_reaches(5))
    emulator.detach(tracking)

    tracking.write_reports(tmp_path)

    # Not counted as a return, but in the report.
    assert dict(tracking.returns) == {}
    assert report_lines(tmp_path) == [
        "call_site,entry,return_site,return_target,outcome,count",
        "6000,6004,,,open,1",
    ]
