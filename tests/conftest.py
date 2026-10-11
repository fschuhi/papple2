from pathlib import Path
from typing import NamedTuple

import pytest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU
from papple2.core.emulator import Emulator
from papple2.debug.assembler import Assembler
from papple2.programs import nested_loops
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
from papple2.workbench.shell import run, tiling_reports, use_reports_folder
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


# The names for nested_loops' addresses, given by hand.
WALKTHROUGH_NAMES = {
    0x6002: "OUTER",
    0x6004: "INNER",
    0x6010: "SUB",
    0x6013: "DONE",
}


class Walkthrough(NamedTuple):
    """The walkthrough's run: the machine as the run left it, its tiling,
    the graph and loops of the routine at $6000, the names, and the folder
    the reports went into."""

    emulator: Emulator
    tiling: Tiling
    graph: BlockGraph
    loops: dict[int, Loop]
    labels: dict[int, str]
    folder: Path


@pytest.fixture
def walkthrough(tmp_path: Path, fresh_session: None) -> Walkthrough:
    """The walkthrough's run, with the recipe of scripts/walkthrough.py:
    run nested_loops with Tiling attached and write the reports into a
    folder. Then read the split reports back, build the graph of the
    routine at $6000 and find its loops."""
    use_reports_folder(tmp_path)
    run(nested_loops.boot(), 39, Tiling)
    tiling_reports()
    emulator = shell.session.run_emulator
    (tiling,) = shell.session.run_instrumentations

    tiles, transitions = read_split_reports(tmp_path)
    graph = build_graph(tiles, transitions, entry=nested_loops.LOAD_ADDRESS)
    loops = natural_loops(graph, immediate_dominators(graph))
    labels = dict(WALKTHROUGH_NAMES)
    return Walkthrough(emulator, tiling, graph, loops, labels, tmp_path)
