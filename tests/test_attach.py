"""Emulator.attach() and detach(): an experiment's hook methods go into the
hook lists of the same name in Memory and CPU, and come out again.

The experiments here are small classes with one or two hook methods, like
the real ones in scripts/."""

import logging

import pytest

from papple2.core.emulator import Emulator

NOP = 0xEA


class OpcodeAndInstruction:
    """One Memory hook and one CPU hook, to show both owners are served."""

    def __init__(self) -> None:
        self.opcodes: list[int] = []
        self.instructions = 0

    def after_read_opcode(self, address: int, value: int) -> None:
        self.opcodes.append(address)

    def after_instruction(self) -> None:
        self.instructions += 1


class Misspelled:
    def after_read_opcod(self, address: int, value: int) -> None:
        pass


@pytest.fixture
def emulator() -> Emulator:
    # NOP at $1000, PC there; tests call do_next_step() directly
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(0x1000, [NOP])
    emulator.cpu.PC = 0x1000
    return emulator


def test_attach_puts_each_method_into_its_list(emulator: Emulator) -> None:
    experiment = OpcodeAndInstruction()

    emulator.attach(experiment)

    assert emulator.apple2.memory.after_read_opcode == [experiment.after_read_opcode]
    assert emulator.cpu.after_instruction == [experiment.after_instruction]
    assert emulator.apple2.memory.after_read_data == []


def test_attached_hooks_are_called(emulator: Emulator) -> None:
    experiment = OpcodeAndInstruction()
    emulator.attach(experiment)

    emulator.cpu.do_next_step()

    assert experiment.opcodes == [0x1000]
    assert experiment.instructions == 1


def test_detach_takes_the_hooks_out(emulator: Emulator) -> None:
    experiment = OpcodeAndInstruction()
    emulator.attach(experiment)

    emulator.detach(experiment)
    emulator.cpu.do_next_step()

    assert emulator.apple2.memory.after_read_opcode == []
    assert emulator.cpu.after_instruction == []
    assert experiment.opcodes == []
    assert experiment.instructions == 0


def test_detach_leaves_other_hooks_in_place(emulator: Emulator) -> None:
    def other(address: int, value: int) -> None:
        pass

    experiment = OpcodeAndInstruction()
    emulator.apple2.memory.after_read_opcode.append(other)
    emulator.attach(experiment)

    emulator.detach(experiment)

    assert emulator.apple2.memory.after_read_opcode == [other]


def test_a_misspelled_hook_name_is_refused(emulator: Emulator) -> None:
    with pytest.raises(ValueError, match="after_read_opcod"):
        emulator.attach(Misspelled())

    assert emulator.apple2.memory.after_read_opcode == []


def test_attach_and_detach_are_logged(emulator: Emulator, caplog: pytest.LogCaptureFixture) -> None:
    # caplog is pytest's own fixture: it collects what the logging module
    # writes during the test
    caplog.set_level(logging.INFO)
    experiment = OpcodeAndInstruction()

    emulator.attach(experiment)
    emulator.detach(experiment)

    assert "attached OpcodeAndInstruction: after_read_opcode, after_instruction" in caplog.text
    assert "detached OpcodeAndInstruction: after_read_opcode, after_instruction" in caplog.text
