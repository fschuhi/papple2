#!/usr/bin/env python3

"""
Tiles, stretches, and call trees -- the building blocks the Robotron
disassembly work uses to turn raw instruction data into a Graphviz
call-flow graph.

Tile
    A "tile" is a basic block: a run of instructions that always
    execute one after another, with nothing jumping into the middle
    of it. `TileFactory.create_tiles` starts a new tile whenever an
    instruction is a "leap" (a branch, jump, call, or return -- see
    `OpInfo.is_leap`) or whenever some other instruction can jump
    *to* this one.

Stretch
    A "stretch" is a chain of tiles linked end-to-end because control
    flow moves between them in a fixed, predictable way: falling
    straight through to the next tile (`TYPE_SEQUENTIAL`), an
    always-taken branch (`TYPE_BRANCH_ALWAYS`), or a `JSR` that
    always returns to the very next instruction (`TYPE_STRAIGHT_JSR`).
    A stretch is "compact" if it is only ever entered via `JSR` and
    ends in a plain `RTS` -- i.e. it looks like a clean subroutine
    body. NOTE: unlike the tile concept (which maps cleanly onto the
    standard "basic block" idea), it is an open question whether
    "stretch" is pulling its own weight as a concept, or whether it
    should be reworked or folded into something else -- revisit
    before extending this further.

    `TYPE_BRANCH_OVER_RTS`, `TYPE_BRANCH_OVER_JMP`, and
    `TYPE_SHOWTEXT` are not produced by the automatic linker above --
    they are tags for `link_tiles_manually`, the escape hatch used by
    the Robotron showcase (`examples/Robotron/workbench.py`) to bridge
    control-flow patterns (a branch that jumps *over* an `RTS`/`JMP`,
    and one Robotron-specific case near `showText`) that the automatic
    rules don't catch. Whether Robotron-specific tags like
    `TYPE_SHOWTEXT` belong in this general-purpose module, or should
    move out to the showcase, is an open question for the M4/M7
    core-vs-showcase split -- not resolved here.

Call tree
    `DotCallTree` turns stretches into a Graphviz graph: each stretch
    becomes one node (drawn as a box if compact, an ellipse
    otherwise), and arrows are drawn for branches, `JSR` calls,
    `JMP`, and unmatched `RTS`s -- giving a visual map of how the
    disassembled program's control flow actually moves.
"""

from collections.abc import Callable, Iterator

from papple2.util import hexaddr, pairwise, dot_RGB
from papple2.core.cpu import JSR, RTS, JMP_absolute
from papple2.debug.memory_map import MemoryMap, OpInfo
# from papple2.MemoryMap import *

TYPE_SEQUENTIAL = 1
TYPE_BRANCH_ALWAYS = 2
TYPE_STRAIGHT_JSR = 4
TYPE_BRANCH_OVER_RTS = 6
TYPE_BRANCH_OVER_JMP = 8
TYPE_SHOWTEXT = 10


class Tile:
    def __init__( self, infos: list[OpInfo] ) -> None:
        assert infos is not None and len( infos ) > 0
        self.infos = infos
        self.link_next_type = None
        self.link_prev: Tile | None = None
        self.link_next: Tile | None = None
        self.is_head = False
        self.is_body = False
        self.is_tail = False

    def verbose( self ) -> str:
        return '%s -> %s' % (hexaddr( self.first_info( ).address ), hexaddr( self.last_info( ).address ))

    def first_info( self ) -> OpInfo:
        return self.infos[0]

    def last_info( self ) -> OpInfo:
        return self.infos[-1]

    def index_of( self, address: int ) -> int | None:
        for index, info in enumerate( self.infos ):
            if info.address == address:
                return index
        return None


class TileFactory:
    def __init__( self, memory_map: MemoryMap ) -> None:
        self.memory_map = memory_map

        # build double-linked list of all tiles
        self.all_tiles: list[Tile] = []

        # each instruction (i.e. a MemInfo) is contained in exactly one tile
        self.infos: dict[int, Tile] = {}


    def init(self, start_address: int, end_address: int ) -> None:
        self.all_tiles.clear()
        self.infos.clear()

        # build double-linked list of all tiles
        self.create_tiles( start_address, end_address )

        # each instruction (i.e. a MemInfo) is contained in exactly one tile
        self.init_infos_dictionary()

        # link tiles as best as possible
        # method could also be called "link_prev_tiles", because the condition is written from the perspective of the prev tile
        self.link_tiles( self.is_sequential_tile, TYPE_SEQUENTIAL )
        self.link_tiles( self.is_branch_always_tile, TYPE_BRANCH_ALWAYS )
        self.link_tiles( self.is_straight_jsr_tile, TYPE_STRAIGHT_JSR )

        # "stretches" of tiles have heads and tails
        # you can wrap those "stretches" into Stretch decorators
        # NOTE: needs to be called again after manual bridging of tiles
        self.update_heads_and_tails()


    def create_tiles( self, start_address: int, end_address: int ) -> None:
        address = start_address
        current_tile: list[OpInfo] = []
        while address <= end_address:

            info = self.memory_map.get_info( address )

            if info is None:
                # no instruction
                address += 1
                continue

            if info.is_leap():
                # leap instruction concludes the tile i.e. it's part of this tile
                current_tile.append( info )

                # tile completed
                new_tile = Tile( current_tile )
                self.all_tiles.append( new_tile )

                # start new tile: next instruction is the first in the tile
                current_tile = []
            else:
                # instruction is sequentially executed, no leap

                # any instruction can be leaped to
                if info.leaps_from.exist( ):

                    # leaping to this instruction breaks the tile, before the current instruction
                    # afterwards the previous instruction is the last of the previous tile and we now start a new tile...
                    if len( current_tile ) == 0:
                        # ... but we need to have instructions for the tile first
                        pass
                    else:
                        # now we can create the tile and store it
                        new_tile = Tile( current_tile )
                        self.all_tiles.append( new_tile )

                    # in any case (i.e. when there are leaps from somewhere): start new tile, we are the first instruction
                    current_tile = [info]

                else:
                    # no leaping to this instruction from elsewhere
                    # => collect the serial execution instructions, to be wrapped as Tile
                    current_tile.append( info )
            address += info.operand_length + 1


    def init_infos_dictionary(self) -> None:
        for tile in self.all_tiles:
            for info in tile.infos:
                self.infos[info.address] = tile

    ###
    ### helpers
    ###

    def get_tile( self, address: int ) -> Tile | None:
        return self.infos[address] if address in self.infos else None

    # TODO: think about dumping towards html, makes more sense for bigger collections (like all Tiles in the TileFactory)
    def dump( self ) -> None:
        for tile in self.all_tiles:
            first_info = tile.infos[0]
            last_info = tile.infos[-1]
            print( '%s -> %s' % (hexaddr( first_info.address ), hexaddr( last_info.address )) )

    ###
    ### linking tiles
    ###

    def link_tiles( self, condition: Callable[[Tile, Tile, OpInfo, OpInfo], bool], link_type: int ) -> None:
        for (prev_tile, next_tile) in pairwise( self.all_tiles ):
            prev_info = prev_tile.last_info()
            next_info = next_tile.first_info()
            consecutive = prev_info.address + prev_info.operand_length + 1 == next_info.address
            if consecutive:
                if condition(prev_tile, next_tile, prev_info, next_info ):
                    # next tile was sequentially executed from this tile
                    self.link_consecutive_tiles( prev_tile, next_tile, prev_info, next_info, link_type )

    @staticmethod
    def is_sequential_tile( prev_tile: Tile, next_tile: Tile, prev_info: OpInfo, next_info: OpInfo ) -> bool:
        # next tile was sequentially executed from this tile
        return prev_info.next_sequential_info is not None

    @staticmethod
    def is_branch_always_tile( prev_tile: Tile, next_tile: Tile, prev_info: OpInfo, next_info: OpInfo ) -> bool:
        if prev_info.is_branch():
            # this is an '+' branch
            # it it were a '0' or '-' branch, it would have been already in the tile

            # TODO: have a central place to manage excemptions from connecting tiles to stretches
            # 0x51b6: SEC/BCS combo
            # 0x5171 is SEC/BCS but it is branched over by 0x5161->0x5173
            return prev_info.address not in [0x51b6]
        return False

    @staticmethod
    def is_straight_jsr_tile( prev_tile: Tile, next_tile: Tile, prev_info: OpInfo, next_info: OpInfo ) -> bool:
        if prev_info.opcode == JSR:
            for leap_from in next_info.leaps_from.infos:
                if leap_from.opcode == RTS:
                    # intentionally split the double condition
                    # we might have multiple leaps_from, not all of them RTS
                    return bool(leap_from.has_matched_JSR)
        return False

    @staticmethod
    def link_consecutive_tiles( prev_tile: Tile, next_tile: Tile, prev_info: OpInfo, next_info: OpInfo, link_type: int ) -> None:
        prev_tile.link_next = next_tile
        next_tile.link_prev = prev_tile

        consecutive = prev_info.address + prev_info.operand_length + 1 == next_info.address
        the_link_type = link_type if consecutive else link_type + 1
        prev_tile.link_type = the_link_type
        next_tile.link_type = the_link_type

    def link_tiles_manually( self, prev_address: int, next_address: int, link_type: int ) -> None:
        prev_tile = self.get_tile(prev_address)
        next_tile = self.get_tile(next_address)
        if prev_tile is not None and next_tile is not None:
            prev_info = prev_tile.last_info()
            next_info = next_tile.first_info()
            self.link_consecutive_tiles( prev_tile, next_tile, prev_info, next_info, link_type )

    def update_heads_and_tails(self) -> None:
        for tile in self.all_tiles:
            # if tile.link_prev is None and tile.link_next is not None:
            if tile.link_prev is None:
                tile.is_head = True
                tile.is_body = False
                tile.is_tail = False
            elif tile.link_prev is not None and tile.link_next is None:
                tile.is_head = False
                tile.is_body = False
                tile.is_tail = True
            else:
                tile.is_head = False
                tile.is_body = True
                tile.is_tail = True

    ###
    ### collect tiles
    ###

    def collect(self, func: Callable[[Tile], bool]) -> list[Tile]:
        return list( filter( func, self.all_tiles ) )

    def collect_heads( self ) -> list[Tile]:
        return self.collect( lambda tile: tile.is_head )

    def collect_tails( self ) -> list[Tile]:
        return self.collect( lambda tile: tile.is_tail )

    @staticmethod
    def pull_tiles( anchor_tile: Tile ) -> list[Tile]:
        assert anchor_tile is not None

        # pull a chain of linked tiles from the factory, using any of the tiles (anchor)

        # chain obviously needs to include the anchor
        tiles = [anchor_tile]

        # go in prev-direction and insert all linked tiles
        tile = anchor_tile
        while tile.link_prev is not None:
            tiles.insert( 0, tile.link_prev )
            tile = tile.link_prev

        # go in next-direction and append all linked tiles
        tile = anchor_tile
        while tile.link_next is not None:
            tiles.append( tile.link_next)
            tile = tile.link_next

        return tiles

    def pull_address_tiles(self, anchor_address: int) -> list[Tile]:
        anchor_tile = self.get_tile(anchor_address)
        assert anchor_tile is not None
        return self.pull_tiles(anchor_tile)


class Stretch:
    def __init__( self, tile_factory: TileFactory, tiles: list[Tile] ) -> None:
        self.tile_factory = tile_factory
        self.memory_map = self.tile_factory.memory_map
        self.tiles = tiles

    def verbose_tiles( self ) -> list[str]:
        return list( map( lambda tile: tile.verbose( ), self.tiles ) )

    def first_tile( self ) -> Tile | None:
        return self.tiles[0] if len( self.tiles ) > 0 else None

    def last_tile( self ) -> Tile | None:
        return self.tiles[-1] if len( self.tiles ) > 0 else None

    def first_info(self) -> OpInfo | None:
        return self.first_tile( ).first_info( ) if len( self.tiles ) > 0 else None

    def first_address(self) -> int:
        return self.first_info().address

    def last_info(self) -> OpInfo | None:
        return self.last_tile( ).last_info( ) if len( self.tiles ) > 0 else None

    def all_infos(self) -> Iterator[OpInfo]:
        for tile in self.tiles:
            for info in tile.infos:
                yield info

    def all_leaps(self) -> Iterator[OpInfo]:
        for tile in self.tiles:
            for info in tile.infos:
                if info.is_leap():
                    yield info

    def filter_opcode( self, opcode: int ) -> list[OpInfo]:
        infos = self.all_infos()
        return list( filter( lambda info: info.opcode == opcode, infos ) )

    def filter_branches( self ) -> list[OpInfo]:
        infos = self.all_infos()
        return list( filter( lambda info: info.is_branch(), infos ) )


    def is_compact( self) -> bool:
        # "compact" means ending w/ a regular RTS
        if self.last_info().opcode != RTS:
            return False

        # "compact" means only JSR as entry point allowed
        if not self.first_info().leaps_from.has_only_leaps_from_JSR():
            return False

        # "compact" means that we only allow JSR leaps which leap outside the stretch
        # TODO: how does the [:-1] work and what does it mean?
        # if not all( info.leap_type in [None, LeapType.branch] for info in list( self.all_infos( ) )[:-1] ):
        if not all( (not info.is_leap() or info.is_branch() or info.opcode == JSR) for info in list( self.all_infos( ) )[:-1] ):
            return False

        # TODO: "compact" also means no JMP, rtsjump, JSR *into* the stretch
        # TODO: we should also define another type of compactness: we want all branchings starting from the stretch ending in tiles of the stretch
        # TODO: define a stretch condition for JMP (and JSR as well): always leap outside the stretch

        return True

    def is_shallow( self) -> bool:
        # compactness is necessary condition for shallowness
        if not self.is_compact():
            return False

        # "shallow" means that we don't allow leap
        # if not all( info.leap_type in [None, LeapType.branch] for info in list( self.all_infos( ) )[:-1] ):
        if not all( (not info.is_leap() or info.is_branch()) for info in list( self.all_infos( ) )[:-1] ):
            return False

        return True


class DotCallTree:
    def __init__(self, tile_factory: TileFactory) -> None:
        self.tile_factory = tile_factory

        # node_stretches contains all stretches which are shown in the dot
        self.node_stretches: dict[int, Stretch] = {}

    def add_node_stretch( self, address: int ) -> Stretch:
        stretch = self.node_stretches.get( address )
        if stretch is None:
            stretch = Stretch( self.tile_factory, self.tile_factory.pull_address_tiles( address ) )
            self.node_stretches[address] = stretch
        return stretch

    # represent a MemInfo in a Graphviz node
    def info_to_node( self, info: OpInfo ) -> str:
        # TODO: info_to_node doesn't have labels anymore (came via OpInfo)
        return info.label if info.has_label() else info.verbose_node( )


    def collect_arrows_dot( self, stretch: Stretch ) -> list[str]:

        arrows = []

        # include origin of arrow
        stretch = self.add_node_stretch( stretch.first_address() )

        # stretches are represented by the first info from the fire tile (head)
        from_stretch_info = stretch.first_info( )
        from_node = self.info_to_node( from_stretch_info )

        for leap_in_stretch_info in stretch.all_leaps():

            if leap_in_stretch_info.is_branch():
                color = dot_RGB( 83, 141, 213 )

            elif leap_in_stretch_info.opcode == JSR:
                color = dot_RGB( 0, 176, 80 )

            elif leap_in_stretch_info.opcode == JMP_absolute:
                color = dot_RGB( 192, 0, 0 )

            elif leap_in_stretch_info.opcode == RTS:
                if leap_in_stretch_info.has_matched_JSR:
                    # do not show regular RTS, only rtsjump
                    continue
                else:
                    color = dot_RGB( 255, 192, 0 )

            else:
                assert False

            if leap_in_stretch_info.leaps_to.exist():
                # an RTS encountered while spidering cannot be resolved
                # for this case that RTS cannot trigger an arrow, because the target stretch is unknown
                # this is a slightly degenerate case where the op is a leap but doesn't show any actual leaps
                # TODO: same situation will arise w/ indirect JMP
                for leap_to_info in leap_in_stretch_info.leaps_to.infos:
                    if leap_to_info.prev_sequential_info == leap_in_stretch_info:
                        # do not show branches not taken
                        pass
                    else:
                        # arrow goes from one stretch (from_node) to stretch which contains the info leaped to (to_node)
                        leap_to_stretch = self.add_node_stretch( leap_to_info.address )
                        leap_to_stretch_first_info = leap_to_stretch.first_info( )
                        to_node = self.info_to_node( leap_to_stretch_first_info )
                        arrows.append( '"%s" -> "%s" [color=%s]' % (from_node, to_node, color) )

        return arrows


    def collect_nodes_dot(self) -> list[str]:
        nodes = []
        # change the node shapes etc. depending on stretch conditions
        for _, node_stretch in self.node_stretches.items():
            node_first_info = node_stretch.first_info( )
            node = self.info_to_node( node_first_info )
            params = 'shape=box' if node_stretch.is_compact() else 'shape=ellipse'
            nodes.append( '"%s" [label="%s (%s)" %s]' % (node, node, node_first_info.execution_count, params) )
        return nodes


    def collect_cycles_ruler( self ) -> list[str]:
        # https://stackoverflow.com/questions/15762014/graphviz-keep-node-position-with-dot
        ruler = [
            '{',
            'node [shape=point, color=white]',
            'edge [style=invis]',
            'splines=false',
        ]

        cycles = set()
        for _, node_stretch in self.node_stretches.items():
            first_info = node_stretch.first_tile().first_info()
            first_cycles = first_info.first_cycles
            # print(node_stretch, node_stretch.first_tile().first_info().verbose())
            # assert first_cycles not in cycles
            cycles.add(first_cycles)
        for prev_cycles, next_cycles in pairwise(sorted(cycles)):
            ruler.append( 'n%i -> n%i' % (prev_cycles, next_cycles) )
        ruler.append('}')

        for _, node_stretch in self.node_stretches.items():
            node_first_info = node_stretch.first_tile().first_info()
            ruler.extend([
                "{",
                "rank=same",
                '"%s"' % self.info_to_node(node_first_info),
                "n%i" % node_first_info.first_cycles,
                "}",
            ])

        return ruler


    def generate_dot( self, heads: list[Tile], cycles_ruler: bool ) -> list[str]:
        dot = [
            'digraph G {',
            'nodesep=0.1',
            'ranksep=0.23',
            'node [fontname=Arial, fontsize=10]',
            'node [margin=0.07 width=0 height=0]',
            'node [color=%s]' % dot_RGB(180,180,180),
            'edge [style=solid, color=black, arrowsize=0.6]',
            'splines=true'
        ]

        # first collect all arrows
        # we do it first because we will have to add the target stretches the heads leap to
        arrows_dot = []
        for head in heads:
            tiles = self.tile_factory.pull_tiles( head )
            stretch = Stretch( self.tile_factory, tiles )
            arrows_dot = arrows_dot + self.collect_arrows_dot(stretch)

        # after doing all branches, we know that we have all nodes (head stretches and the target stretches leaped to)
        nodes_dot = self.collect_nodes_dot()

        # each node stands for the first info of a stretch
        # each info was executed first at some cycles => use this to show the stretches stretched out in time
        cycle_ruler_dot = self.collect_cycles_ruler( ) if cycles_ruler else []

        dot = dot + cycle_ruler_dot + nodes_dot + arrows_dot
        dot.append("}")
        return dot


    def save_dot( self, heads: list[Tile], fnDot: str, file_format: str, cycles_ruler: bool ) -> str:
        dot_lines = self.generate_dot( heads, cycles_ruler )

        with open( fnDot, "w" ) as text_file:
            print(*dot_lines, sep='\n', file=text_file)

        # 05.09.26 removed, but might need to be revisited when using papple2 from Windows (via Excel)
        # import os
        # os.environ["PATH"] += os.pathsep + r's:\shared\Graphviz\bin'

        from graphviz import render
        fnRendered = render('dot', file_format, fnDot )
        return fnRendered


