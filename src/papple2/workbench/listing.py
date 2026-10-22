"""Listing: the rows of a disassembly listing, read from a run's memory.

ListingRow is one line of a listing. listing_rows() builds the rows of an
address range from the emulator's memory, with labels, comments, the
jumps the run took as arrows, the gaps that never ran and the hidden
ranges; print_listing() prints them, plain or with location colors.

Nothing here keeps state: the caller hands over the memory, the run graph
and the dossier's entries. The commands in shell.py and the listing
editor both use the rows; this module imports neither of them.
"""

import re
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass

from papple2.core.emulator import Emulator
from papple2.debug.disassembler import Disassembler
from papple2.workbench.basic_blocks_analysis import BlockGraph
from papple2.workbench.hidden import HiddenRange


@dataclass
class ListingRow:
    """One line of a listing, its pieces kept apart, so that each caller
    lays them out as it needs: print_listing() prints them, the listing
    editor shows them in columns of its own. address is None for a row that
    is no instruction: the empty line before a .byte block, and a gap the
    run never reached, whose text is in instruction ("... 6004-6006: 2
    bytes never ran ..."). There, every other field but the gutter is
    empty, and the bar skips the row.

    The row below a routine that runs on into another one, without a
    leap, has no address either. Its text says where it runs on into
    ("... runs on into CLEAR_PAGE ...", runs_on()), and target holds that
    address: the bar stops on it, and Enter in the listing editor goes
    there. Session.current_listing_rows() adds it.

    target is the address the operand names, the one a label in the operand
    stands for: $1a85 in LDA $1a85,Y, the pointer $1b in STA ($1b),Y, a
    branch's target. None where the operand names no address: implied,
    accumulator and immediate operands, and .byte lines."""

    address: int | None
    gutter: str
    hex_bytes: str
    label: str
    instruction: str
    comment: str
    target: int | None = None


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


def listing_rows(
    emulator: Emulator,
    start: int,
    end: int,
    labels: dict[int, str] | None = None,
    graph: BlockGraph | None = None,
    comments: dict[int, str] | None = None,
    only_ran: bool = False,
    hidden_ranges: dict[str, HiddenRange] | None = None,
) -> list[ListingRow]:
    """The rows of a listing from start up to, not including, end, one per
    instruction: address, bytes, instruction. Read from the emulator's
    memory as it is now, i.e. after the run, past anything that watches the
    CPU. Prints nothing; print_listing() prints the rows.

    With labels, an operand whose address has a name shows the name
    (JSR sub instead of JSR $6010), and an instruction whose own address
    has a name carries it in its label. A local label (routine_6238.loop1)
    shows by its short part, .loop1: always in the label column, since the
    dossier keeps every local label under the global label above it; in an
    operand only if the line lies in the same scope, i.e. under the same
    global label. An operand leading into another scope shows the full name.

    With comments, an instruction whose own address has a comment carries
    it in its comment.

    With graph, the jumps the run took are drawn as arrows in the gutter:
    every edge whose target is not simply the next instruction (taken
    branches, JMPs). Glides, fall-throughs and calls are not drawn. An
    arrow is drawn only if both of its ends lie in the range. And an
    operand that points into a labelled instruction that ran, without a
    label of its own, shows as label+N: STA .selfmod1+2.

    With only_ran, only the code in graph's blocks is listed: each gap
    between them is one row whose instruction says which bytes never ran,
    e.g. "... 0803-2800: 8,189 bytes never ran ...". Give it the run graph
    (build_run_graph()), whose blocks are all the code the run executed: a
    routine's graph leaves out the routines it calls, which ran all the
    same. Without only_ran, every byte in the range is listed.

    With hidden_ranges, each named range is clipped to the listing and
    shown as one row, whether or not it ran. Hidden spans are omitted
    before disassembly. Their labels and comments are not shown; arrows
    with a hidden end are dropped. Place bounds between instructions when
    hiding code. The ranges must not overlap, as Hidden enforces.

    An instruction that starts before end is listed whole, even if its
    operand reaches past end. A block's end always lies after its last
    instruction, so this only shows for ranges that cut an instruction.

    Each instruction's row carries the address its operand names in target,
    as the disassembler works it out, so the listing editor can label it.
    """
    disassembler = Disassembler(emulator.cpu, labels, comments, ran=ran_in(graph))
    # disassemble() takes an inclusive end. A gap or hidden span gets an
    # empty row; gaps keeps its display text, by row number.
    rows: list[list[str]] = []
    gaps: dict[int, str] = {}

    def add_visible(span_start: int, span_end: int) -> None:
        """List one span outside the hidden ranges, with its run gaps."""
        if span_start >= span_end:
            return
        position = span_start
        for part_start, part_end in ran_parts(
            span_start, span_end, graph if only_ran else None
        ):
            if part_start > position:
                gaps[len(rows)] = never_ran(position, part_start)
                rows.append(["", "", "", "", "", ""])
            rows.extend(disassembler.disassemble(part_start, part_end - 1))
            position = part_end
        if position < span_end:
            gaps[len(rows)] = never_ran(position, span_end)
            rows.append(["", "", "", "", "", ""])

    position = start
    for name, definition in sorted(
        (hidden_ranges or {}).items(),
        key=lambda item: (item[1].start, item[0]),
    ):
        hidden_start = max(start, definition.start)
        hidden_end = min(end, definition.end)
        if hidden_start >= hidden_end:
            continue
        add_visible(position, hidden_start)
        note = f": {definition.note}" if definition.note else ""
        gaps[len(rows)] = f"... {hidden_start:04x}-{hidden_end:04x} {name}{note} ..."
        rows.append(["", "", "", "", "", ""])
        position = hidden_end
    add_visible(position, end)
    gutter = draw_gutter(len(rows), *arrows_in(rows, graph, hidden_ranges))
    # The addresses of the global labels, sorted, to find each line's scope.
    global_addresses = sorted(
        address for address, text in (labels or {}).items() if "." not in text
    )
    result = []
    for index, (row, prefix) in enumerate(zip(rows, gutter)):
        row_address, row_bytes, label, mnemonic, operand, comment = row
        instruction = f"{mnemonic} {operand}".rstrip()
        target = None
        if row_address:
            # The disassembler gives "$6004": four hex digits after the "$".
            address = int(row_address.removeprefix("$"), 16)
            if "." in label:
                label = label[label.index(".") :]
            owner = scope_of(address, global_addresses, labels or {})
            if owner is not None:
                instruction = shorten_locals(instruction, owner)
            if mnemonic != ".byte":
                info, _length = disassembler.collect_op_info(address)
                target = info.get("operand_address")
        else:  # the empty line before a .byte block, a gap or a hidden span
            address = None
            instruction = gaps.get(index, "")
        result.append(
            ListingRow(
                address=address,
                gutter=prefix,
                hex_bytes=row_bytes,
                label=label,
                instruction=instruction,
                comment=comment,
                target=target,
            )
        )
    return result


def ran_parts(
    start: int, end: int, graph: BlockGraph | None
) -> list[tuple[int, int]]:
    """The parts of the range from start up to end to list instruction by
    instruction, in address order, each as (start, end). Without graph,
    the whole range. With it, only the code the run executed: its blocks,
    cut to the range, adjoining blocks joined into one part. Whatever lies
    between the parts never ran."""
    if graph is None:
        return [(start, end)]
    parts: list[tuple[int, int]] = []
    for block in sorted(graph.blocks.values(), key=lambda block: block.start):
        part_start, part_end = max(block.start, start), min(block.end, end)
        if part_start >= part_end:  # the block lies outside the range
            continue
        if parts and parts[-1][1] >= part_start:
            parts[-1] = (parts[-1][0], max(parts[-1][1], part_end))
        else:
            parts.append((part_start, part_end))
    return parts


def never_ran(start: int, end: int) -> str:
    """The text of the row that stands for a gap: the bytes from start up
    to, not including, end."""
    size = end - start
    return (
        f"... {start:04x}-{end:04x}: {size:,} byte{'' if size == 1 else 's'}"
        " never ran ..."
    )


def runs_on(name: str) -> str:
    """The text of the row below a routine that runs on into another one,
    without a leap: name is where, a label or an address."""
    return f"... runs on into {name} ..."


def ran_in(graph: BlockGraph | None) -> Callable[[int], bool]:
    """Whether an address lies in a block of graph, i.e. in code the run
    executed. Without a graph, nothing ran."""
    if graph is None:
        return lambda address: False
    blocks = list(graph.blocks.values())
    return lambda address: any(block.start <= address < block.end for block in blocks)


def scope_of(
    address: int, global_addresses: list[int], labels: dict[int, str]
) -> str | None:
    """The global label whose scope address lies in: the one at address
    itself or the nearest above it. None above the first global label.
    global_addresses holds the addresses of labels' global labels, sorted."""
    index = bisect_right(global_addresses, address) - 1
    if index < 0:
        return None
    return labels[global_addresses[index]]


def shorten_locals(instruction: str, owner: str) -> str:
    """instruction with owner's local labels shown short: BNE
    routine_6238.loop1 -> BNE .loop1, if owner is routine_6238. A name that
    only ends in the owner's name (xroutine_6238.loop1) is left alone."""
    return re.sub(
        rf"(?<![A-Za-z0-9_:.]){re.escape(owner)}\.(?=[A-Za-z0-9_])",
        ".",
        instruction,
    )


# Terminal foreground colors for the dossier's supported shades.
LISTING_COLORS = {
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    # MIX_COLOR in colors.py: light yellow, for different shades at once.
    "brightyellow": "\x1b[93m",
}


def print_listing(
    rows: list[ListingRow],
    color_of: Callable[[int], str | None] | None = None,
) -> None:
    """Print listing rows, optionally colored by their starting addresses.

    The label column follows the longest label. Comments align after the
    widest commented instruction. Colors cover addresses, bytes, labels
    and instructions, including operands and .byte contents; comments,
    arrow gutters and collapsed rows remain uncolored.

    Without color_of, print plain text, suitable for reports and copying.
    """
    width = max((len(row.label) for row in rows), default=0)
    instruction_width = max(
        (len(row.instruction) for row in rows if row.comment), default=0
    )
    for row in rows:
        if row.address is None:
            print((row.gutter + row.instruction).rstrip())
            continue
        name_column = f"{row.label:<{width}}  " if width else ""
        instruction = row.instruction
        if row.comment:
            instruction = f"{instruction:<{instruction_width}}"
        code = (
            f"{row.address:04x}  {row.hex_bytes:<8}  "
            f"{name_column}{instruction}"
        )
        shade = color_of(row.address) if color_of is not None else None
        if shade is not None:
            # Keep alignment padding outside the color, and reset before
            # the comment so location color does not spread into prose.
            visible = code.rstrip()
            padding = code[len(visible):]
            code = LISTING_COLORS[shade] + visible + "\x1b[0m" + padding
        comment = f"  ; {row.comment}" if row.comment else ""
        print(f"{row.gutter}{code}{comment}".rstrip())


def arrows_in(
    rows: list[list[str]],
    graph: BlockGraph | None,
    hidden_ranges: dict[str, HiddenRange] | None = None,
) -> tuple[list[tuple[int, int]], list[int]]:
    """The arrows for the rows of a listing, as (source row, target row),
    and their lanes. An arrow starts at the last instruction of an edge's
    source block, the leap, and ends at the edge's target. A hidden leap
    must not move its arrow onto an earlier visible instruction."""
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
        # The block ends directly after its leap. With instruction-aligned
        # hidden bounds, a hidden last byte means the leap is hidden too.
        if any(
            definition.start <= block.end - 1 < definition.end
            for definition in (hidden_ranges or {}).values()
        ):
            continue
        leaps = [address for address in row_of if source <= address < block.end]
        if not leaps or target not in row_of:  # an end lies outside the range
            continue
        arrows.append((row_of[max(leaps)], row_of[target]))
    spans = [(min(source, target), max(source, target)) for source, target in arrows]
    return arrows, assign_lanes(spans)
