import pytest


@pytest.fixture
def make_mem_access_emulator(make_emulator):
    """Wraps the shared make_emulator fixture and additionally enables the
    mem_access hooks -- every test in this file needs that, so it's folded
    in here rather than repeated per test."""

    def _make_mem_access_emulator(program, preload=None):
        asm, emulator = make_emulator(program, preload=preload)
        emulator.mem_access.enable_hooks()
        return asm, emulator

    return _make_mem_access_emulator


def test_read_alone_logs_one_entry_with_no_write(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    start:  LDA $0300
    done:   JMP done
        """,
        preload={0x0300: 0x77},
    )

    run_steps(emulator, 1)

    states = emulator.mem_access.memory_states
    assert len(states) == 1
    cpu_state, reads, write = states[0]
    assert reads == [(0x0300, 0x77)]
    assert write is None


def test_write_alone_logs_one_entry_with_no_read(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    start:  STA $0301
    done:   JMP done
        """
    )
    emulator.cpu.A = 0x99

    run_steps(emulator, 1)

    states = emulator.mem_access.memory_states
    assert len(states) == 1
    cpu_state, reads, write = states[0]
    assert reads is None
    assert write == (0x0301, 0x00, 0x99)


def test_read_modify_write_instruction_logs_as_one_entry(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    start:  INC $0302
    done:   JMP done
        """,
        preload={0x0302: 0x10},
    )

    run_steps(emulator, 1)

    states = emulator.mem_access.memory_states
    assert len(states) == 1  # one instruction, one entry -- not two
    cpu_state, reads, write = states[0]
    assert reads == [(0x0302, 0x10)]
    assert write == (0x0302, 0x10, 0x11)


def test_cpu_state_has_correct_pc_and_nondecreasing_cycles(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    first:  LDA $0300
    second: STA $0301
    done:   JMP done
        """,
        preload={0x0300: 0x42},
    )

    run_steps(emulator, 2)

    states = emulator.mem_access.memory_states
    assert len(states) == 2

    (cycles0, pc0), reads0, write0 = states[0]
    (cycles1, pc1), reads1, write1 = states[1]

    assert pc0 == asm.labels['FIRST']
    assert pc1 == asm.labels['SECOND']
    assert cycles1 >= cycles0


def test_immediate_mode_read_is_not_logged(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    start:  LDA #$11
    done:   JMP done
        """
    )

    run_steps(emulator, 1)

    assert emulator.mem_access.memory_states == []


def test_count_mem_accesses_matches_recorded_states(make_mem_access_emulator, run_steps):
    asm, emulator = make_mem_access_emulator(
        """
            *=$6000
    first:  LDA $0300
    second: STA $0301
    third:  INC $0301
    done:   JMP done
        """,
        preload={0x0300: 0x42},
    )

    run_steps(emulator, 3)

    assert emulator.mem_access.count_mem_accesses() == len(emulator.mem_access.memory_states)
    assert emulator.mem_access.count_mem_accesses() == 3
