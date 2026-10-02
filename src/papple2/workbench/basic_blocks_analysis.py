"""Basic blocks analysis: the graph of basic blocks, built from tiling reports.

An analysis package: no Emulator. It reads the split reports that the
tiling instrumentation wrote into a folder, builds a graph from them, and
computes the dominator tree and the natural loops, and writes the two loop
reports into a folder (briefing.md, section 3).

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
    address,
)

# Leap rows that give no edge. A JSR's edge into the callee is replaced by
# its call fall-through edge; returns and BRK lead out of the routine.
# Everything else stays: branches, JMP absolute, JMP indirect.
NO_EDGE_OPCODES = frozenset({JSR, RTS, RTI, BRK})

GLIDE = "glide"

# The loop reports this analysis writes, and their columns (briefing.md,
# section 3.E).
LOOPS_FILE = "lr_loops.csv"
LOOP_MEMBERS_FILE = "lr_loop_members.csv"
LOOPS_FIELDS = (
    "loop_id",
    "header_block",
    "back_edge_source_block",
    "back_edge_count",
    "nesting_depth",
    "outer_loop_id",
    "member_blocks",
)
LOOP_MEMBERS_FIELDS = (
    "block_start_PC",
    "block_end_PC",
    "executions",
    "innermost_loop",
    "depth",
)


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


@dataclass(frozen=True)
class Loop:
    """A natural loop. Back edges with the same header make one loop, with
    their bodies merged, so a loop is identified by its header."""

    header: int
    back_edges: tuple[tuple[int, int], ...]  # (source, header), in address order
    body: frozenset[int]
    parent: int | None  # header of the enclosing loop
    depth: int  # 0 = outermost


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


def back_edges(graph: BlockGraph, idom: dict[int, int]) -> list[tuple[int, int]]:
    """The edges source -> target whose target dominates their source, in
    address order. Each target is a loop header."""
    return [(source, target) for source, target in graph.edges if dominates(idom, target, source)]


def loop_body(graph: BlockGraph, header: int, source: int) -> set[int]:
    """The body of the loop closed by the back edge source -> header: the
    header, plus every block that can reach source without passing through
    the header. The header is in the set from the start, so the backward
    walk stops there and never leaves the loop."""
    body = {header}
    stack = []
    if source not in body:  # a self-loop's body is just the header
        body.add(source)
        stack.append(source)
    while stack:
        block = stack.pop()
        for predecessor in graph.predecessors[block]:
            if predecessor not in body:
                body.add(predecessor)
                stack.append(predecessor)
    return body


def natural_loops(graph: BlockGraph, idom: dict[int, int]) -> dict[int, Loop]:
    """The natural loops of the graph, keyed by header, in address order."""
    edges_by_header: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for edge in back_edges(graph, idom):
        edges_by_header[edge[1]].append(edge)

    bodies: dict[int, frozenset[int]] = {}
    for header in sorted(edges_by_header):
        body: set[int] = set()
        for source, _ in edges_by_header[header]:
            body |= loop_body(graph, header, source)
        bodies[header] = frozenset(body)

    # Natural loops with different headers are either disjoint or nested,
    # never partly overlapping. So the loops that strictly contain a loop
    # form a chain, and its parent is the smallest of them.
    parents: dict[int, int | None] = {}
    for header, body in bodies.items():
        enclosing = [other for other in bodies if body < bodies[other]]
        parents[header] = min(enclosing, key=lambda other: len(bodies[other]), default=None)

    def depth_of(header: int) -> int:
        depth = 0
        parent = parents[header]
        while parent is not None:
            depth += 1
            parent = parents[parent]
        return depth

    return {
        header: Loop(
            header=header,
            back_edges=tuple(edges_by_header[header]),
            body=bodies[header],
            parent=parents[header],
            depth=depth_of(header),
        )
        for header in bodies
    }


def write_rows(filename: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} records to {filename}")


def write_loop_reports(folder: Path, graph: BlockGraph, loops: dict[int, Loop]) -> None:
    """Write lr_loops.csv (one row per loop) and lr_loop_members.csv (one row
    per basic block of the graph) into folder.

    Loops are numbered L01, L02, ... in header-address order. A loop with
    several back edges lists their sources and their counts as two
    space-separated lists in the same order, so zip() pairs them up again.
    """
    loop_ids = {
        header: f"L{number:02d}" for number, header in enumerate(sorted(loops), start=1)
    }

    loop_rows = []
    for header in sorted(loops):
        loop = loops[header]
        loop_rows.append(
            {
                "loop_id": loop_ids[header],
                "header_block": address(header),
                "back_edge_source_block": " ".join(
                    address(source) for source, _ in loop.back_edges
                ),
                "back_edge_count": " ".join(
                    str(graph.edges[edge]) for edge in loop.back_edges
                ),
                "nesting_depth": loop.depth,
                "outer_loop_id": "-" if loop.parent is None else loop_ids[loop.parent],
                "member_blocks": " ".join(address(block) for block in sorted(loop.body)),
            }
        )

    member_rows = []
    for start, block in graph.blocks.items():
        # The loops containing a block are nested in each other, so the one
        # with the smallest body is the innermost.
        containing = [loop for loop in loops.values() if start in loop.body]
        innermost = min(containing, key=lambda loop: len(loop.body), default=None)
        member_rows.append(
            {
                "block_start_PC": address(start),
                "block_end_PC": address(block.end),
                "executions": block.executions,
                "innermost_loop": "-" if innermost is None else loop_ids[innermost.header],
                "depth": 0 if innermost is None else innermost.depth + 1,
            }
        )

    write_rows(folder / LOOPS_FILE, LOOPS_FIELDS, loop_rows)
    write_rows(folder / LOOP_MEMBERS_FILE, LOOP_MEMBERS_FIELDS, member_rows)
