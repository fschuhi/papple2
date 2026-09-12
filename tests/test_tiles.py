
import unittest
from papple2.debug.assembler import Assembler
from papple2.core.emulator import Emulator
from papple2.debug.tiles import TileFactory


def run_steps(emulator, count):
    for _ in range(count):
        emulator.cpu.do_next_step()
        emulator.post_op()


def assemble(program):
    asm = Assembler()
    tokens = asm.tokenize(program)
    code = asm.generate_code(tokens)
    return asm, asm.to_byte_array(code)


# LDA #$00 sets Z, so BEQ is always taken. A dead LDA #$FF sits between the
# branch and its target so the two tiles stay physically non-adjacent in
# memory -- this keeps the test clear of the automatic tile-linker's
# "physically consecutive" heuristic (see tiles.py docstring: whether that
# heuristic should link a taken branch to its target at all is an open
# question, not something this test should depend on either way).
BRANCH_PROGRAM = """
        *=$6000
start:  LDA #$00
        STA $0300
        BEQ target
        LDA #$FF        ; dead code, never executed -- BEQ always taken
target: LDA #$11
        STA $0301
done:   JMP done
"""


class TestTileFactory(unittest.TestCase):

    def setUp(self):
        self.asm, program = assemble(BRANCH_PROGRAM)
        self.emulator = Emulator(no_display=True)
        self.emulator.apple2.memory.load_test_data(0x6000, program)
        self.emulator.cpu.PC = 0x6000

        # LDA, STA, BEQ, LDA(target), STA, JMP -- six instructions, enough to
        # populate the MemoryMap with the executed path (see memory_map.py:
        # OpInfo entries only exist for addresses that were actually
        # executed or spidered, so the dead LDA #$FF never gets one).
        run_steps(self.emulator, 6)

        self.factory = TileFactory(self.emulator.map)
        self.factory.init(self.asm.labels['START'], self.asm.labels['DONE'])

    def test_branch_ends_a_tile_and_its_target_starts_a_new_one(self):
        # A leap instruction (here: the branch) always concludes a tile,
        # and its target -- being something jumped *to* -- always starts
        # a new one. That should hold regardless of how the two end up
        # linked (or not) into a stretch.
        self.assertEqual(len(self.factory.all_tiles), 2)

        first_tile = self.factory.get_tile(self.asm.labels['START'])
        self.assertEqual(first_tile.first_info().address, self.asm.labels['START'])
        self.assertTrue(first_tile.last_info().is_branch())

        target_tile = self.factory.get_tile(self.asm.labels['TARGET'])
        self.assertIsNot(target_tile, first_tile)
        self.assertEqual(target_tile.first_info().address, self.asm.labels['TARGET'])

    def test_tiles_are_unlinked_given_the_non_adjacent_layout(self):
        # With the dead byte keeping the branch and its target physically
        # apart, the automatic linker's "consecutive" check never fires --
        # so neither tile ends up linked to the other.
        #
        # NOTE: an unlinked tile (no link_prev, no link_next) comes out of
        # update_heads_and_tails() as is_head=True but is_tail=False -- the
        # "is this a chain's end" flag only ever turns True for a tile that
        # *has* a link_prev, so a standalone tile is head-only, never tail,
        # by the current mechanism. Documented here as a finding, not
        # something this test tries to fix (M6 explicitly excludes
        # redesigning tiles/stretches).
        first_tile = self.factory.get_tile(self.asm.labels['START'])
        target_tile = self.factory.get_tile(self.asm.labels['TARGET'])

        for tile in (first_tile, target_tile):
            self.assertTrue(tile.is_head)
            self.assertFalse(tile.is_body)
            self.assertFalse(tile.is_tail)
            self.assertIsNone(tile.link_prev)
            self.assertIsNone(tile.link_next)


if __name__ == '__main__':
    unittest.main()
