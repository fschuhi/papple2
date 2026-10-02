"""Shell: functions for looking at a run at the IPython prompt.

The analysis objects keep addresses as plain ints, which Python prints in
decimal. Only a function that knows what each number means can choose its
format, so these print addresses in hex, as the reports do, and leave
counts in decimal. They print and return nothing, so IPython adds no
output line of its own.

Ranges are half-open, as everywhere in the workbench: start is the first
byte, end the first byte behind. So a block printed as 6004-6007 is
dis(emulator, 0x6004, 0x6007).
"""

from papple2.core.emulator import Emulator
from papple2.debug.disassembler import Disassembler
from papple2.debug.labels import Labels
from papple2.workbench.basic_blocks_analysis import BlockGraph, Loop
from papple2.workbench.tiling import address


def loop_ids(loops: dict[int, Loop]) -> dict[int, str]:
    """L01, L02, ... in header-address order, as in the loop reports."""
    return {
        header: f"L{number:02d}"
        for number, header in enumerate(sorted(loops), start=1)
    }


def innermost_loop(block: int, loops: dict[int, Loop]) -> Loop | None:
    """The smallest loop whose body holds block, or None. The loops holding
    a block are nested in each other, so the smallest is the innermost."""
    containing = [loop for loop in loops.values() if block in loop.body]
    return min(containing, key=lambda loop: len(loop.body), default=None)


def show_blocks(graph: BlockGraph, loops: dict[int, Loop] | None = None) -> None:
    """One line per basic block: its bytes, how often it ran, and, if loops
    are given, the innermost loop it belongs to."""
    ids = loop_ids(loops) if loops else {}
    header = f"{'block':<9}  {'runs':>6}"
    if loops:
        header += "  loop"
    print(header)
    for start, block in graph.blocks.items():
        line = f"{address(start)}-{address(block.end)}  {block.executions:>6,}"
        if loops:
            innermost = innermost_loop(start, loops)
            line += "  " + ("-" if innermost is None else ids[innermost.header])
        print(line)


def show_edges(graph: BlockGraph, loops: dict[int, Loop] | None = None) -> None:
    """One line per edge: source and target block, how often it was taken,
    and, if loops are given, which edges are back edges."""
    back_edge_of: dict[tuple[int, int], str] = {}
    if loops:
        ids = loop_ids(loops)
        for loop in loops.values():
            for edge in loop.back_edges:
                back_edge_of[edge] = ids[loop.header]
    print(f"{'edge':<12}  {'count':>6}")
    for (source, target), count in graph.edges.items():
        line = f"{address(source)} -> {address(target)}  {count:>6,}"
        if (source, target) in back_edge_of:
            line += f"  back edge of {back_edge_of[(source, target)]}"
        print(line)


def show_loops(loops: dict[int, Loop]) -> None:
    """One line per loop, in the order and with the ids of the loop
    reports: header, nesting depth, enclosing loop, back edge sources,
    member blocks."""
    ids = loop_ids(loops)
    print(
        f"{'loop':<4}  {'header':<6}  {'depth':>5}  {'outer':<5}  "
        f"{'back from':<9}  members"
    )
    for header in sorted(loops):
        loop = loops[header]
        outer = "-" if loop.parent is None else ids[loop.parent]
        sources = " ".join(address(source) for source, _ in loop.back_edges)
        members = " ".join(address(block) for block in sorted(loop.body))
        print(
            f"{ids[header]:<4}  {address(header):<6}  {loop.depth:>5}  "
            f"{outer:<5}  {sources:<9}  {members}"
        )


def assign_lanes(spans: list[tuple[int, int]]) -> list[int]:
    """Give each arrow a lane in the gutter; lane 0 lies next to the code.

    An arrow is given as the span of rows it covers, (first, last). Shorter
    arrows are placed first, each into the lowest lane that holds no arrow
    sharing a row with it. So an arrow inside another one gets the lane
    nearer the code, and arrows that don't overlap can share a lane.
    """
    order = sorted(
        range(len(spans)),
        key=lambda i: (spans[i][1] - spans[i][0], spans[i][0]),
    )
    lanes = [0] * len(spans)
    occupied: list[list[tuple[int, int]]] = []  # the spans in each lane
    for i in order:
        first, last = spans[i]
        lane = 0
        while lane < len(occupied) and any(
            first <= other_last and other_first <= last
            for other_first, other_last in occupied[lane]
        ):
            lane += 1
        if lane == len(occupied):
            occupied.append([])
        occupied[lane].append((first, last))
        lanes[i] = lane
    return lanes


def draw_gutter(
    row_count: int, arrows: list[tuple[int, int]], lanes: list[int]
) -> list[str]:
    """The gutter left of the code, one string per row.

    arrows are (source row, target row), lanes as assign_lanes() gives
    them. Each lane is two characters wide, followed by two for the arrow
    heads. An arrow starts with "+--" at its source and ends with "+->"
    at its target, and "|" joins the two. No arrows, no gutter.
    """
    if not arrows:
        return [""] * row_count
    lane_count = max(lanes) + 1
    width = 2 * lane_count + 2
    cells = [[" "] * width for _ in range(row_count)]
    # Outer lanes first, so an inner arrow's corner is drawn over an outer
    # arrow's line where the two meet in one row.
    for (source, target), lane in sorted(
        zip(arrows, lanes), key=lambda item: -item[1]
    ):
        column = 2 * (lane_count - 1 - lane)
        for row in range(min(source, target) + 1, max(source, target)):
            if cells[row][column] == " ":
                cells[row][column] = "|"
        # The target is drawn last, so an arrow to its own row shows ">".
        for row, head in ((source, "-"), (target, ">")):
            cells[row][column] = "+"
            for between in range(column + 1, width - 2):
                cells[row][between] = "-"
            cells[row][width - 2] = head
    return ["".join(row) for row in cells]


def dis(
    emulator: Emulator,
    start: int,
    end: int,
    labels: Labels | None = None,
    graph: BlockGraph | None = None,
) -> None:
    """Print the instructions from start up to, not including, end: address,
    bytes, instruction. Read from the emulator's memory as it is now, i.e.
    after the run, past anything that watches the CPU.

    With labels, an operand whose address has a name shows the name
    (JSR SUB instead of JSR $6010). Zero-page operands keep their address:
    Labels doesn't name them yet. An instruction whose own address has a
    name shows it in a column of its own, before the instruction. The
    column is as wide as the longest name in the range, and left out if
    no address in the range has a name.

    With graph, the jumps the run took are drawn as arrows in a gutter on
    the left: every edge whose target is not simply the next instruction
    (taken branches, JMPs). Glides, fall-throughs and calls are not drawn.
    An arrow is drawn only if both of its ends lie in the range.

    An instruction that starts before end is printed whole, even if its
    operand reaches past end. A block's end always lies behind its last
    instruction, so this only shows for ranges that cut an instruction.
    """
    disassembler = Disassembler(
        emulator.cpu, labels if labels is not None else Labels()
    )
    # disassemble() takes an inclusive end.
    rows = disassembler.disassemble(start, end - 1)
    width = max((len(row[2]) for row in rows), default=0)
    gutter = draw_gutter(len(rows), *arrows_in(rows, graph))
    for row, prefix in zip(rows, gutter):
        row_address, row_bytes, label, mnemonic, operand, _comment = row
        if not row_address:  # the empty line before a .byte block
            print(prefix.rstrip())
            continue
        name_column = f"{label:<{width}}  " if width else ""
        print(
            f"{prefix}{row_address.removeprefix('$'):<4}  {row_bytes:<8}  "
            f"{name_column}{mnemonic} {operand}".rstrip()
        )


def arrows_in(
    rows: list[list[str]], graph: BlockGraph | None
) -> tuple[list[tuple[int, int]], list[int]]:
    """The arrows for the rows of a listing, as (source row, target row),
    and their lanes. An arrow starts at the last instruction of an edge's
    source block, the leap, and ends at the edge's target."""
    if graph is None:
        return [], []
    # Row number of each instruction, by its address; empty lines and
    # .byte blocks are no instructions.
    row_of = {
        int(row[0].removeprefix("$"), 16): number
        for number, row in enumerate(rows)
        if row[0] and row[3] != ".byte"
    }
    arrows = []
    for (source, target), _count in graph.edges.items():
        block = graph.blocks[source]
        if target == block.end:  # just the next instruction: no arrow
            continue
        leaps = [address for address in row_of if source <= address < block.end]
        if not leaps or target not in row_of:  # an end lies outside the range
            continue
        arrows.append((row_of[max(leaps)], row_of[target]))
    spans = [(min(source, target), max(source, target)) for source, target in arrows]
    return arrows, assign_lanes(spans)
