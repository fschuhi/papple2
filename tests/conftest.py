from pathlib import Path
from typing import NamedTuple

import pytest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU
from papple2.core.emulator import Emulator
from papple2.debug.assembler import Assembler
from papple2.debug.stop_conditions import at_address
from papple2.workbench import shell
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    build_graph,
    immediate_dominators,
    natural_loops,
    read_split_reports,
)
from papple2.workbench.session import Session
from papple2.workbench.tiling import Tiling


@pytest.fixture
def memory():
    return Memory()


@pytest.fixture
def cpu(memory):
    return CPU(memory, None)


@pytest.fixture
def fresh_session(monkeypatch):
    """A new, empty Session as the shell's current one, with no reports
    folder and no dossier. The shell's own Session is back after the test,
    so the tests don't see each other's state."""
    monkeypatch.setattr(shell, "session", Session())


@pytest.fixture
def assemble():
    """Factory fixture: returns a function that assembles one program string
    into (Assembler, byte code). Each test picks its own program, so this
    hands back a callable rather than a fixed value."""

    def _assemble(program: str) -> tuple[Assembler, list[int]]:
        asm = Assembler()
        tokens = asm.tokenize(program)
        code = asm.generate_code(tokens)
        return asm, asm.to_byte_array(code)

    return _assemble


@pytest.fixture
def make_emulator(assemble):
    """Factory fixture: returns a function that assembles a program, loads
    it into a headless Emulator at $6000, sets PC there, and applies any
    preload bytes. Anything specific to what's under test stays in the
    test."""

    def _make_emulator(
        program: str, preload: dict[int, int] | None = None
    ) -> tuple[Assembler, Emulator]:
        asm, code = assemble(program)
        emulator = Emulator(no_display=True)
        emulator.apple2.memory.load_test_data(0x6000, code)
        emulator.cpu.PC = 0x6000
        if preload:
            for address, value in preload.items():
                emulator.apple2.memory.load_test_data(address, [value])
        return asm, emulator

    return _make_emulator


# The program of scripts/walkthrough.py: two nested loops, one JSR, and a
# JMP over the subroutine to DONE. Twenty bytes, $6000-$6013.
WALKTHROUGH_PROGRAM = """
        *=$6000
        LDY #$02
OUTER   LDX #$03
INNER   JSR SUB
        DEX
        BNE INNER
        DEY
        BNE OUTER
        JMP DONE
SUB     INC $10
        RTS
DONE    NOP
"""
WALKTHROUGH_ENTRY = 0x6000
WALKTHROUGH_END = 0x6014  # the byte behind DONE's NOP: the run stops here

# The names of scripts/walkthrough.py's NAMES.
WALKTHROUGH_NAMES = {
    0x6002: "OUTER",
    0x6004: "INNER",
    0x6010: "SUB",
    0x6013: "DONE",
}


class Walkthrough(NamedTuple):
    """What %run scripts/walkthrough.py leaves in IPython's namespace, plus
    the folder the reports went into."""

    emulator: Emulator
    tiling: Tiling
    graph: BlockGraph
    loops: dict[int, Loop]
    labels: dict[int, str]
    folder: Path


@pytest.fixture
def walkthrough(make_emulator, tmp_path: Path) -> Walkthrough:
    """The walkthrough's run, as scripts/walkthrough.py does it: run the
    program with Tiling attached, write the reports into a folder, read
    the split reports back, build the graph and find the loops."""
    _, emulator = make_emulator(WALKTHROUGH_PROGRAM)
    tiling = Tiling(emulator.cpu)
    emulator.attach(tiling)
    emulator.run(until=at_address(WALKTHROUGH_END))
    emulator.detach(tiling)
    tiling.write_reports(tmp_path, emulator.instructions, rwts_reads=0)

    tiles, transitions = read_split_reports(tmp_path)
    graph = build_graph(tiles, transitions, entry=WALKTHROUGH_ENTRY)
    loops = natural_loops(graph, immediate_dominators(graph))
    labels = dict(WALKTHROUGH_NAMES)
    return Walkthrough(emulator, tiling, graph, loops, labels, tmp_path)
