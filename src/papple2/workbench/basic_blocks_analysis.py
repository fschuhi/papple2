"""Basic blocks analysis: the graph of basic blocks, built from tiling reports.

An analysis package: no Emulator. It reads the split reports that the
tiling instrumentation wrote into a folder, builds a graph from them, and
computes the dominator tree. Natural loops follow in a later step
(briefing.md, section 3).

The tiling reports speak of tiles and transitions; the graph speaks of
basic blocks and edges. build_graph() is the only place that translates
between the two: read_split_reports() returns tiles and transitions,
build_graph() returns basic blocks and edges.
"""

import csv
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from papple2.core.cpu import JSR, RTS

# A "speaking" import: the analysis names the instrumentation whose reports
# it reads. How an analysis states what it needs upstream is still open
# (briefing.md, section 7).
from papple2.workbench.tiling import (
    BRK,
    RTI,
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
)

# Leap rows that give no edge. A JSR's edge into the callee is replaced by
# its call fall-through edge; returns and BRK lead out of the routine.
# Everything else stays: branches, JMP absolute, JMP indirect.
NO_EDGE_OPCODES = frozenset({JSR, RTS, RTI, BRK})

GLIDE = "glide"


@dataclass(frozen=True)
class SplitTile:
    """One row of lr_split_tiles.csv."""

    start: int
    end: int  # exclusive
    executions: int


@dataclass(frozen=True)
class SplitTransition:
    """One row of lr_split_transitions.csv. Glide rows have no leap, so
    their leap_from_pc and opcode are None."""

    source_tile: int
    leap_from_pc: int | None
    opcode: int | None
    outcome: str
    target_tile: int
    count: int


@dataclass(frozen=True)
class BasicBlock:
    """A node of the graph. Each basic block comes from one split tile."""

    start: int
    end: int  # exclusive
    executions: int


@dataclass
class BlockGraph:
    """The basic blocks reachable from entry, and the edges between them.

    Blocks are keyed by their start address. edges maps (source, target)
    to how often the edge was taken; successors and predecessors list the
    neighbours of each block in address order. Both are kept because the
    later steps walk the graph in both directions.
    """

    entry: int
    blocks: dict[int, BasicBlock]
    edges: dict[tuple[int, int], int]
    successors: dict[int, list[int]]
    predecessors: dict[int, list[int]]


def parse_address(text: str) -> int:
    return int(text, 16)


def parse_opcode(text: str) -> int | None:
    """'$4C' -> 0x4C; '' (a glide row) -> None."""
    return int(text.removeprefix("$"), 16) if text else None


def read_split_reports(folder: Path) -> tuple[list[SplitTile], list[SplitTransition]]:
    """Read the two split reports the tiling instrumentation wrote into folder."""
    with (folder / SPLIT_TILES_FILE).open(newline="", encoding="utf-8") as tiles_file:
        tiles = [
            SplitTile(
                start=parse_address(row["tile_start_PC"]),
                end=parse_address(row["tile_end_PC"]),
                executions=int(row["executions"]),
            )
            for row in csv.DictReader(tiles_file)
        ]
    with (folder / SPLIT_TRANSITIONS_FILE).open(
            newline="", encoding="utf-8"
    ) as transitions_file:
        transitions = [
            SplitTransition(
                source_tile=parse_address(row["source_tile"]),
                leap_from_pc=(
                    parse_address(row["leap_from_PC"]) if row["leap_from_PC"] else None
                ),
                opcode=parse_opcode(row["opcode"]),
                outcome=row["outcome"],
                target_tile=parse_address(row["target_tile"]),
                count=int(row["count"]),
            )
            for row in csv.DictReader(transitions_file)
        ]
    return tiles, transitions


def collect_edges(
        transitions: list[SplitTransition], block_starts: set[int]
) -> dict[tuple[int, int], int]:
    """Turn transition rows into edges, following briefing.md, section 3.B."""
    edges: dict[tuple[int, int], int] = defaultdict(int)
    for row in transitions:
        if row.outcome == GLIDE:
            edges[(row.source_tile, row.target_tile)] += row.count
        elif row.opcode == JSR:
            # The call fall-through edge: from the block holding the JSR to
            # the block right behind it. The run never observes this edge,
            # so it carries the JSR's count: how often the call was made,
            # an upper bound for how often it returned. If no block starts
            # there, the JSR never returned during the run: no edge.
            return_point = (row.leap_from_pc + 3) & 0xFFFF
            if return_point in block_starts:
                edges[(row.source_tile, return_point)] += row.count
        elif row.opcode not in NO_EDGE_OPCODES:
            edges[(row.source_tile, row.target_tile)] += row.count

    # The tiling's consistency checks guarantee that every transition starts
    # and ends at a split tile, so a stray edge means the reports don't
    # belong together. Stop rather than build a graph with holes.
    for source, target in edges:
        if source not in block_starts or target not in block_starts:
            raise ValueError(
                f"edge {source:04x} -> {target:04x} has an end that is no basic block"
            )
    return dict(edges)


def reachable_from(entry: int, edges: dict[tuple[int, int], int]) -> set[int]:
    """The blocks reachable from entry along edges, entry included."""
    successors: dict[int, list[int]] = defaultdict(list)
    for source, target in edges:
        successors[source].append(target)
    reached = {entry}
    queue = deque([entry])
    while queue:
        block = queue.popleft()
        for target in successors[block]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def build_graph(
        tiles: list[SplitTile], transitions: list[SplitTransition], entry: int
) -> BlockGraph:
    """Build the graph of the basic blocks reachable from entry."""
    all_blocks = {
        tile.start: BasicBlock(tile.start, tile.end, tile.executions)
        for tile in tiles
    }
    if entry not in all_blocks:
        raise ValueError(f"entry {entry:04x} is not the start of a basic block")

    all_edges = collect_edges(transitions, set(all_blocks))
    reached = reachable_from(entry, all_edges)

    # Edges are kept if their source is reachable; their target then is too.
    edges = {
        (source, target): count
        for (source, target), count in sorted(all_edges.items())
        if source in reached
    }
    successors: dict[int, list[int]] = {start: [] for start in sorted(reached)}
    predecessors: dict[int, list[int]] = {start: [] for start in sorted(reached)}
    for source, target in edges:
        successors[source].append(target)
        predecessors[target].append(source)

    return BlockGraph(
        entry=entry,
        blocks={start: all_blocks[start] for start in sorted(reached)},
        edges=edges,
        successors=successors,
        predecessors=predecessors,
    )


def reverse_postorder(graph: BlockGraph) -> list[int]:
    """The blocks in reverse postorder of a depth-first search from entry.

    A block gets its postorder number when the search has finished with all
    of its successors, so a block always comes before its successors here,
    except along edges that lead back. The search visits successors in
    address order, so the same graph is always numbered the same way.
    It keeps its own stack instead of recursing: Python stops recursion at
    a depth of about 1000, and a whole game's graph can go deeper.
    """
    postorder: list[int] = []
    visited = {graph.entry}
    # Each stack entry: a block, and an iterator over the successors the
    # search has not looked at yet.
    stack = [(graph.entry, iter(graph.successors[graph.entry]))]
    while stack:
        block, successors = stack[-1]
        for successor in successors:
            if successor not in visited:
                visited.add(successor)
                stack.append((successor, iter(graph.successors[successor])))
                break
        else:
            # No successor left to visit: the block is finished.
            stack.pop()
            postorder.append(block)
    postorder.reverse()
    return postorder


def immediate_dominators(graph: BlockGraph) -> dict[int, int]:
    """Each block's immediate dominator; the entry maps to itself.

    Cooper, Harvey, Kennedy: "A Simple, Fast Dominance Algorithm" (2001).
    Walk the blocks in reverse postorder and set each block's idom to the
    meeting point of its predecessors that already have one. Repeat whole
    passes until one pass changes nothing.
    """
    order = reverse_postorder(graph)
    # The entry, finished last, gets the highest number.
    postorder_number = {
        block: len(order) - 1 - position for position, block in enumerate(order)
    }
    idom: dict[int, int] = {graph.entry: graph.entry}

    def intersect(finger1: int, finger2: int) -> int:
        # Climbing to an idom always leads to a higher postorder number, so
        # the finger with the lower number is the deeper one: move it up
        # until both fingers meet at the closest common dominator.
        while finger1 != finger2:
            while postorder_number[finger1] < postorder_number[finger2]:
                finger1 = idom[finger1]
            while postorder_number[finger2] < postorder_number[finger1]:
                finger2 = idom[finger2]
        return finger1

    changed = True
    while changed:
        changed = False
        for block in order[1:]:  # order[0] is the entry
            # The block the search reached this one from comes earlier in
            # the order, so at least one predecessor always has an idom.
            processed = [p for p in graph.predecessors[block] if p in idom]
            new_idom = processed[0]
            for predecessor in processed[1:]:
                new_idom = intersect(predecessor, new_idom)
            if idom.get(block) != new_idom:
                idom[block] = new_idom
                changed = True
    return idom


def dominates(idom: dict[int, int], a: int, b: int) -> bool:
    """True if every path from the entry to b passes through a: a is b, or
    an ancestor of b in the dominator tree."""
    while b != a:
        parent = idom[b]
        if parent == b:  # b is the entry, the root of the tree
            return False
        b = parent
    return True
