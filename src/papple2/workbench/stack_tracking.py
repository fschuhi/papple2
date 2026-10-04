"""Stack tracking: a shadow stack that sorts every RTS by its frame.

An instrumentation package: it watches a running Emulator through one
after_instruction hook, like Tiling. run() builds it from the CPU.

The 6502 has no idea what a call is. JSR pushes its return address minus
one onto page 1 and jumps; RTS pulls whatever two bytes are on top, adds
one, and jumps there. So a program can push two bytes itself and "return"
somewhere no JSR ever called from (PHA/PHA/RTS), throw a return address
away (PLA/PLA), or rewrite one in page 1 before its RTS.

The shadow stack is a second stack outside the machine, kept by this
instrumentation alone. Each JSR opens a frame: the call site, the entry
it jumps to, and the return it expects. A frame is keyed by SP before the
call, which is where SP is again after the matching RTS. Each RTS then
looks for the frame at the SP the CPU is back at:

    frame there, PC is its expected return  -> matched
    frame there, PC is somewhere else       -> redirected
    no frame there                          -> unmatched
    frames deeper than that SP              -> abandoned

Looking frames up by SP, instead of popping the top one, lets the shadow
stack fall back into step with the real one after a trick. A JSR that
opens a frame at or above an old one's place abandons the old one too.

A tail call (a routine ending in JMP to another one) is matched, not a
mismatch: the second routine's RTS returns where the first one's caller
expects. It shows in the entry and the return site of its row instead:
the frame was opened for one routine and closed in another one's code.

Observed, not proven: what this records is what this run did.

Known limits:
- SP wrapping around page 1 confuses "deeper"; a run that wraps would
  show up as odd abandoned frames.
- RTI and BRK are ignored.
- A trap that returns for the routine it stands in for (the RWTS
  stand-in's fake RTS) runs no instruction, so its frame ends up
  abandoned.
- Frames still open when the run stops are left in frames, not counted.

The report, lr_returns.csv, comes in a later step; for now the counts
are in returns.
"""

from collections import Counter
from collections.abc import Callable
from typing import NamedTuple

from papple2.core.cpu import CPU, JSR, RTS

# The outcomes of a frame or an RTS, as they will appear in the report.
MATCHED = "matched"
REDIRECTED = "redirected"
UNMATCHED = "unmatched"
ABANDONED = "abandoned"


class Frame(NamedTuple):
    """One JSR the shadow stack has seen and not yet seen returned from."""

    call_site: int
    entry: int
    expected_return: int


class Return(NamedTuple):
    """One row of the later report: what closed which frame, and how.

    Abandoned rows have no return site and no target; unmatched rows have
    no call site and no entry, since no frame was there."""

    call_site: int | None
    entry: int | None
    return_site: int | None
    return_target: int | None
    outcome: str


class StackTracking:
    """Keep a shadow stack through one after_instruction hook, and count
    how each frame ended."""

    def __init__(self, cpu: CPU) -> None:
        self.cpu = cpu
        # The open frames, keyed by SP before the call.
        self.frames: dict[int, Frame] = {}
        self.returns: Counter[Return] = Counter()

    def after_instruction(self) -> None:
        # Called after every instruction, so everything but JSR and RTS
        # costs one comparison.
        opcode = self.cpu.last_opcode
        if opcode == JSR:
            self._call()
        elif opcode == RTS:
            self._return()

    def _call(self) -> None:
        cpu = self.cpu
        # JSR has pushed two bytes, so SP before the call was two higher.
        key = (cpu.SP + 2) & 0xFF
        # Anything at this place or deeper has been overwritten by the push.
        self._abandon(lambda other: other <= key)
        self.frames[key] = Frame(
            call_site=cpu.last_PC,
            entry=cpu.PC,
            expected_return=(cpu.last_PC + 3) & 0xFFFF,
        )

    def _return(self) -> None:
        cpu = self.cpu
        key = cpu.SP
        # Frames deeper than where the CPU is back at can never return.
        self._abandon(lambda other: other < key)
        frame = self.frames.pop(key, None)
        if frame is None:
            self.returns[Return(None, None, cpu.last_PC, cpu.PC, UNMATCHED)] += 1
            return
        outcome = MATCHED if cpu.PC == frame.expected_return else REDIRECTED
        self.returns[
            Return(frame.call_site, frame.entry, cpu.last_PC, cpu.PC, outcome)
        ] += 1

    def _abandon(self, is_gone: Callable[[int], bool]) -> None:
        """Count and drop every open frame whose key is_gone() says is
        gone."""
        for key in [key for key in self.frames if is_gone(key)]:
            frame = self.frames.pop(key)
            self.returns[
                Return(frame.call_site, frame.entry, None, None, ABANDONED)
            ] += 1
