import unittest
from papple2.debug.assembler import Assembler
from papple2.core.emulator import Emulator


def run_steps(emulator, count):
    for _ in range(count):
        emulator.cpu.do_next_step()
        emulator.post_op()


def assemble(program):
    asm = Assembler()
    tokens = asm.tokenize(program)
    code = asm.generate_code(tokens)
    return asm, asm.to_byte_array(code)


def make_emulator(program, preload=None):
    """preload: optional {address: value}, written directly into memory before
    running -- lets a test control the "old" value a read or RMW instruction
    sees, without needing an extra instruction (and extra log entry) to set it up."""
    asm, code = assemble(program)
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(0x6000, code)
    emulator.cpu.PC = 0x6000
    if preload:
        for address, value in preload.items():
            emulator.apple2.memory.load_test_data(address, [value])
    emulator.mem_access.enable_hooks()
    return asm, emulator


class TestMemAccessCollector(unittest.TestCase):

    def test_read_alone_logs_one_entry_with_no_write(self):
        asm, emulator = make_emulator(
            """
                *=$6000
        start:  LDA $0300
        done:   JMP done
            """,
            preload={0x0300: 0x77},
        )

        run_steps(emulator, 1)

        states = emulator.mem_access.memory_states
        self.assertEqual(len(states), 1)
        cpu_state, reads, write = states[0]
        self.assertEqual(reads, [(0x0300, 0x77)])
        self.assertIsNone(write)

    def test_write_alone_logs_one_entry_with_no_read(self):
        asm, emulator = make_emulator(
            """
                *=$6000
        start:  STA $0301
        done:   JMP done
            """
        )
        emulator.cpu.A = 0x99

        run_steps(emulator, 1)

        states = emulator.mem_access.memory_states
        self.assertEqual(len(states), 1)
        cpu_state, reads, write = states[0]
        self.assertIsNone(reads)
        self.assertEqual(write, (0x0301, 0x00, 0x99))

    def test_read_modify_write_instruction_logs_as_one_entry(self):
        asm, emulator = make_emulator(
            """
                *=$6000
        start:  INC $0302
        done:   JMP done
            """,
            preload={0x0302: 0x10},
        )

        run_steps(emulator, 1)

        states = emulator.mem_access.memory_states
        self.assertEqual(len(states), 1)  # one instruction, one entry -- not two
        cpu_state, reads, write = states[0]
        self.assertEqual(reads, [(0x0302, 0x10)])
        self.assertEqual(write, (0x0302, 0x10, 0x11))

    def test_cpu_state_has_correct_pc_and_nondecreasing_cycles(self):
        asm, emulator = make_emulator(
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
        self.assertEqual(len(states), 2)

        (cycles0, pc0), reads0, write0 = states[0]
        (cycles1, pc1), reads1, write1 = states[1]

        self.assertEqual(pc0, asm.labels['FIRST'])
        self.assertEqual(pc1, asm.labels['SECOND'])
        self.assertGreaterEqual(cycles1, cycles0)

    def test_immediate_mode_read_is_not_logged(self):
        asm, emulator = make_emulator(
            """
                *=$6000
        start:  LDA #$11
        done:   JMP done
            """
        )

        run_steps(emulator, 1)

        self.assertEqual(emulator.mem_access.memory_states, [])

    def test_count_mem_accesses_matches_recorded_states(self):
        asm, emulator = make_emulator(
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

        self.assertEqual(
            emulator.mem_access.count_mem_accesses(),
            len(emulator.mem_access.memory_states),
        )
        self.assertEqual(emulator.mem_access.count_mem_accesses(), 3)


if __name__ == "__main__":
    unittest.main()
