"""Overview: the current run on one page, and its routines as a table.

Two files for reading outside the prompt, in a text editor and in Excel,
with the dossier's labels next to the addresses:

    lr_overview.txt   the whole run, the routines, the blocks in no
                      routine, and the loops of each routine
    lr_routines.csv   the routines, one row each, the same columns as in
                      lr_overview.txt
    lr_listing.tsv    the listing of every routine, one after the other

Both are built from the Session's current run: its routines (with the
targets of stack jumps, if the returns report was read), its transitions,
its emulator's instruction count and memory. write_overview_reports() writes them
into the Session's reports folder; the command overview_reports() in
shell.py calls it.

The labels make these files go stale when a label changes in the dossier;
the next run of the recipe brings them up to date.
"""

import csv
import io
from dataclasses import dataclass

from papple2.core.cpu import JSR
from papple2.workbench.basic_blocks_analysis import BlockGraph, Loop
from papple2.workbench.session import Session
from papple2.workbench.tiling import address

OVERVIEW_FILE = "lr_overview.txt"
ROUTINES_FILE = "lr_routines.csv"
LISTING_FILE = "lr_listing.tsv"
ROUTINES_FIELDS = (
    "routine",
    "label",
    "end",
    "span_bytes",
    "blocks",
    "blocks_bytes",
    "called",
    "loops",
    "calls",
)

LISTING_FIELDS = (
    "routine",
    "address",
    "bytes",
    "label",
    "instruction",
    "target",
    "target_label",
    "comment",
)


@dataclass(frozen=True)
class RoutineLine:
    """One routine as the overview shows it. end is exclusive, the end of
    its highest block, as listing() lists the routine; span_bytes is
    end - entry, gaps included; blocks_bytes counts only the bytes of its
    blocks. calls holds the names of the routines it calls by JSR: their
    labels, or their addresses where they have none."""

    entry: int
    label: str
    end: int
    span_bytes: int
    blocks: int
    blocks_bytes: int
    called: int
    loops: int
    calls: tuple[str, ...]


def current_labels(session: Session) -> dict[int, str]:
    """The open dossier's labels, read afresh; none without a dossier."""
    session.refresh_annotations()
    if session.annotations is None:
        return {}
    return session.annotations.labels


def routine_lines(session: Session, labels: dict[int, str]) -> list[RoutineLine]:
    """Every routine of the current run, in address order."""
    found = session.current_routines()
    transitions = session.run_transitions or []
    lines = []
    for entry, graph in sorted(found.graphs.items()):
        _, end = session.listing_range(entry)
        callees = sorted(
            {
                row.target_tile
                for row in transitions
                if row.opcode == JSR and row.source_tile in graph.blocks
            }
        )
        lines.append(
            RoutineLine(
                entry=entry,
                label=labels.get(entry, ""),
                end=end,
                span_bytes=end - entry,
                blocks=len(graph.blocks),
                blocks_bytes=sum(
                    block.end - block.start for block in graph.blocks.values()
                ),
                called=found.calls_into[entry],
                loops=len(found.loops_of[entry]),
                calls=tuple(labels.get(callee, address(callee)) for callee in callees),
            )
        )
    return lines


def routines_csv(session: Session) -> str:
    """The text of lr_routines.csv: one row per routine of the current
    run, the callees separated by spaces."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(ROUTINES_FIELDS)
    for line in routine_lines(session, current_labels(session)):
        writer.writerow(
            [
                address(line.entry),
                line.label,
                address(line.end),
                line.span_bytes,
                line.blocks,
                line.blocks_bytes,
                line.called,
                line.loops,
                " ".join(line.calls),
            ]
        )
    return out.getvalue()


def print_loop_tree(
    loops: dict[int, Loop],
    graph: BlockGraph,
    labels: dict[int, str],
    parent: int | None,
    indent: int,
    out: io.StringIO,
) -> None:
    """Print the loops whose enclosing loop is parent, each followed by its
    own inner loops, one step further indented. A loop shows its header,
    how often the header ran, and the header's label, if it has one."""
    for header, loop in sorted(loops.items()):
        if loop.parent == parent:
            runs = graph.blocks[header].executions
            line = f"{'  ' * indent}loop {address(header)}  {runs:>9,}x  "
            print((line + labels.get(header, "")).rstrip(), file=out)
            print_loop_tree(loops, graph, labels, header, indent + 1, out)


def overview_text(session: Session) -> str:
    """The text of lr_overview.txt: the whole run, the routines with
    their labels and callees, the blocks in no routine, and each routine's
    loops."""
    labels = current_labels(session)
    found = session.current_routines()
    run_graph = session.run_graph
    lines = routine_lines(session, labels)

    all_loops = [loop for loops in found.loops_of.values() for loop in loops.values()]
    in_a_routine = {start for graph in found.graphs.values() for start in graph.blocks}
    no_routine = [start for start in run_graph.blocks if start not in in_a_routine]

    out = io.StringIO()
    print("WHOLE RUN", file=out)
    print(f"  {session.run_emulator.instructions:,} instructions", file=out)
    print(
        f"  {len(run_graph.blocks):,} blocks, "
        f"{sum(b.end - b.start for b in run_graph.blocks.values()):,} bytes",
        file=out,
    )
    print(f"  {len(lines)} routines", file=out)
    deepest = max((loop.depth for loop in all_loops), default=-1) + 1
    print(f"  {len(all_loops)} loops, at most {deepest} inside each other", file=out)
    print(file=out)

    label_width = max((len(line.label) for line in lines), default=0)
    label_width = max(label_width, len("label"))
    print("ROUTINES (in address order)", file=out)
    print(
        f"  {'routine':<7}  {'label':<{label_width}}  {'end':<4}  "
        f"{'span_bytes':>10}  {'blocks':>6}  {'blocks_bytes':>12}  "
        f"{'called':>7}  {'loops':>5}  calls",
        file=out,
    )
    for line in lines:
        text = (
            f"  {address(line.entry):<7}  {line.label:<{label_width}}  "
            f"{address(line.end):<4}  {line.span_bytes:>10,}  {line.blocks:>6}  "
            f"{line.blocks_bytes:>12,}  {line.called:>7,}  {line.loops:>5}  "
            + " ".join(line.calls)
        )
        print(text.rstrip(), file=out)
    print(file=out)

    print(f"BLOCKS IN NO ROUTINE: {len(no_routine)}", file=out)
    for start in no_routine:
        print(f"  {address(start)}  {labels.get(start, '')}".rstrip(), file=out)
    print(file=out)

    print("LOOPS PER ROUTINE (runs = how often the loop's header ran)", file=out)
    for line in lines:
        loops = found.loops_of[line.entry]
        if loops:
            print(f"  routine {address(line.entry)}  {line.label}".rstrip(), file=out)
            print_loop_tree(
                loops, found.graphs[line.entry], labels, None, 2, out
            )
    return out.getvalue()


def listing_tsv(session: Session) -> str:
    """The text of lr_listing.tsv: the listing of every routine of the
    current run, in address order, as listing(entry) shows it, without
    the arrows. Code shared by several routines shows once in each.

    Every row has an address, so that Excel can sort and filter on it: a
    row that stands for no instruction (a gap that never ran, a hidden
    range, the empty line before .byte data) takes the address of the next
    row that has one. Between two routines, an empty row carries the next
    routine's name and first address."""
    labels = current_labels(session)
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t")
    writer.writerow(LISTING_FIELDS)
    for number, entry in enumerate(sorted(session.current_routines().graphs)):
        name = labels.get(entry, address(entry))
        rows = session.current_listing_rows(entry)
        # The address each row shows: its own, or the next one there is.
        shown: list[int] = []
        following = session.listing_range(entry)[1]
        for row in reversed(rows):
            if row.address is not None:
                following = row.address
            shown.append(following)
        shown.reverse()
        if number > 0:
            writer.writerow([name, address(shown[0])] + [""] * 6)
        for row, row_address in zip(rows, shown):
            target = "" if row.target is None else address(row.target)
            writer.writerow(
                [
                    name,
                    address(row_address),
                    row.hex_bytes,
                    row.label,
                    row.instruction,
                    target,
                    "" if row.target is None else labels.get(row.target, ""),
                    row.comment,
                ]
            )
    return out.getvalue()


def write_overview_reports(session: Session) -> None:
    """Write lr_overview.txt, lr_routines.csv and lr_listing.tsv of the
    current run into the Session's reports folder."""
    for file_name, text in (
        (OVERVIEW_FILE, overview_text(session)),
        (ROUTINES_FILE, routines_csv(session)),
        (LISTING_FILE, listing_tsv(session)),
    ):
        path = session.write_report(file_name, text)
        print(f"wrote {path}")
