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


def dis(
    emulator: Emulator, start: int, end: int, labels: Labels | None = None
) -> None:
    """Print the instructions from start up to, not including, end: address,
    bytes, instruction. Read from the emulator's memory as it is now, i.e.
    after the run, past anything that watches the CPU.

    With labels, an operand whose address has a name shows the name
    (JSR SUB instead of JSR $6010). Zero-page operands keep their address:
    Labels doesn't name them yet.

    An instruction that starts before end is printed whole, even if its
    operand reaches past end. A block's end always lies behind its last
    instruction, so this only shows for ranges that cut an instruction.
    """
    disassembler = Disassembler(
        emulator.cpu, labels if labels is not None else Labels()
    )
    # disassemble() takes an inclusive end.
    for row in disassembler.disassemble(start, end - 1):
        row_address, row_bytes, _label, mnemonic, operand, _comment = row
        if not row_address:  # the empty line before a .byte block
            print()
            continue
        print(f"{row_address.removeprefix('$'):<4}  {row_bytes:<8}  {mnemonic} {operand}".rstrip())
