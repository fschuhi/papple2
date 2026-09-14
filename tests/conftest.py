import pytest
from papple2.core.memory import Memory
from papple2.core.cpu import CPU
from papple2.core.emulator import Emulator
from papple2.debug.assembler import Assembler


@pytest.fixture
def memory():
    return Memory()


@pytest.fixture
def cpu(memory):
    return CPU(memory, None)


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
    preload bytes. Hook setup (mem_access, time_machine, write-protect, ...)
    stays in the test, since that's specific to what's under test."""

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


@pytest.fixture
def run_steps():
    """Factory fixture: returns a function that drives the CPU directly,
    one instruction at a time -- the same way Emulator.run() does per step,
    but without going through the state machine / checkpoints / window
    layer, so tests control exactly when side effects like TimeMachine
    restoring get involved."""

    def _run_steps(emulator: Emulator, count: int) -> None:
        for _ in range(count):
            emulator.cpu.do_next_step()
            emulator.post_op()

    return _run_steps
