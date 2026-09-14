import pytest
from papple2.debug.tiles import TileFactory


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


@pytest.fixture
def tile_factory(make_emulator, run_steps):
    asm, emulator = make_emulator(BRANCH_PROGRAM)

    # LDA, STA, BEQ, LDA(target), STA, JMP -- six instructions, enough to
    # populate the MemoryMap with the executed path (see memory_map.py:
    # OpInfo entries only exist for addresses that were actually
    # executed or spidered, so the dead LDA #$FF never gets one).
    run_steps(emulator, 6)

    factory = TileFactory(emulator.map)
    factory.init(asm.labels['START'], asm.labels['DONE'])

    return asm, factory


def test_branch_ends_a_tile_and_its_target_starts_a_new_one(tile_factory):
    asm, factory = tile_factory

    # A leap instruction (here: the branch) always concludes a tile,
    # and its target -- being something jumped *to* -- always starts
    # a new one. That should hold regardless of how the two end up
    # linked (or not) into a stretch.
    assert len(factory.all_tiles) == 2

    first_tile = factory.get_tile(asm.labels['START'])
    assert first_tile.first_info().address == asm.labels['START']
    assert first_tile.last_info().is_branch()

    target_tile = factory.get_tile(asm.labels['TARGET'])
    assert target_tile is not first_tile
    assert target_tile.first_info().address == asm.labels['TARGET']


def test_tiles_are_unlinked_given_the_non_adjacent_layout(tile_factory):
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
    asm, factory = tile_factory

    first_tile = factory.get_tile(asm.labels['START'])
    target_tile = factory.get_tile(asm.labels['TARGET'])

    for tile in (first_tile, target_tile):
        assert tile.is_head
        assert not tile.is_body
        assert not tile.is_tail
        assert tile.link_prev is None
        assert tile.link_next is None
