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
