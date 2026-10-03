"""Walk a tiny program through the workbench's pipeline.

Assembles a small 6502 program (two nested loops, one JSR), runs it
headless with the tiling instrumentation attached, and writes seven
reports into tmp/walkthrough/:
    from Tiling (papple2.workbench.tiling):
        lr_unbroken_tiles.csv
        lr_unbroken_transitions.csv
        lr_measurements.txt
        lr_split_tiles.csv
        lr_split_transitions.csv
    from the basic blocks analysis (papple2.workbench.basic_blocks_analysis):
        lr_loops_6000.csv
        lr_loop_members_6000.csv

The program is small enough to follow by hand, so each report's rows can
be predicted before looking.

Run from the repo root:

    make walkthrough

or in IPython, which keeps the run's objects (emulator, tiling, graph,
loops) in its namespace afterwards:

    %run scripts/walkthrough.py

After %run, show_blocks(graph, loops), show_edges(graph, loops) and
show_loops(loops) print them with hex addresses, and dis(emulator, start,
end, labels) disassembles a range, with the names of NAMES
(papple2.workbench.shell).
"""

from pathlib import Path

from papple2.core.emulator import Emulator
from papple2.debug.assembler import Assembler
from papple2.debug.stop_conditions import at_address
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Loop,
    build_graph,
    immediate_dominators,
    natural_loops,
    read_split_reports,
    write_loop_reports,
)
from papple2.workbench.tiling import Tiling, address

# Not used here: imported so that IPython's %run leaves them in its
# namespace, ready for looking at the run.
from papple2.workbench.shell import (  # noqa: F401
    dis,
    show_blocks,
    show_edges,
    show_loops,
)

# One folder per script, named after it.
REPORTS_FOLDER = Path("tmp/walkthrough")

# Must match the *= line of PROGRAM.
LOAD_ADDRESS = 0x6000

# Two nested loops and one JSR. SUB sits behind the loops, so the JMP
# jumps over it. LDY and LDX sit in front of the two branch targets, so
# the first tile runs straight through addresses that later become
# entry points.
PROGRAM = """
        *=$6000
        LDY #$02      ; outer loop: 2 passes
OUTER   LDX #$03      ; inner loop: 3 passes per outer pass
INNER   JSR SUB
        DEX
        BNE INNER
        DEY
        BNE OUTER
        JMP DONE      ; jump over SUB
SUB     INC $10
        RTS
DONE    NOP
"""

# The names for PROGRAM's addresses, given by hand: the way names will
# come for Lode Runner, from the user (the oracle protocol in README.md).
NAMES = {
    0x6002: "OUTER",
    0x6004: "INNER",
    0x6010: "SUB",
    0x6013: "DONE",
}


def assemble(program: str) -> list[int]:
    """Assemble program into bytes, the way tests/test_assembler.py does."""
    asm = Assembler()
    tokens = asm.tokenize(program, verbose=False)
    code = asm.generate_code(tokens, verbose=False)
    return asm.to_byte_array(code)


def walkthrough(
    folder: Path,
) -> tuple[Emulator, Tiling, BlockGraph, dict[int, Loop]]:
    """Run PROGRAM with Tiling attached, then write the tiling reports
    and the loop reports into folder."""
    code = assemble(PROGRAM)
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(LOAD_ADDRESS, code)
    emulator.cpu.PC = LOAD_ADDRESS

    tiling = Tiling(emulator.cpu)
    emulator.attach(tiling)

    # Stop at the byte behind the program, once DONE's NOP has run. Every
    # tile the run entered has then run at least one instruction.
    try:
        emulator.run(until=at_address(LOAD_ADDRESS + len(code)))
    finally:
        emulator.detach(tiling)

    first_tile = next(
        tile for tile in tiling.tiles.values() if tile.initial_entries
    )
    print(
        f"{emulator.instructions} instructions; "
        f"run started in tile {address(first_tile.start_pc)}, "
        f"stopped in tile {address(tiling.current_tile.start_pc)}"
    )

    # run() counts from 0, so emulator.instructions is what ran while the
    # tiling was attached. No disk routine here, so no RWTS reads.
    tiling.write_reports(folder, emulator.instructions, rwts_reads=0)

    # The analysis reads the reports back from the folder, as it would
    # for any other run: the files are the only connection.
    tiles, transitions = read_split_reports(folder)
    graph = build_graph(tiles, transitions, entry=LOAD_ADDRESS)
    loops = natural_loops(graph, immediate_dominators(graph))
    write_loop_reports(folder, graph, loops)
    return emulator, tiling, graph, loops


if __name__ == "__main__":
    # At module level on purpose: IPython's %run keeps these names in
    # its namespace, so the run can be inspected afterwards.
    emulator, tiling, graph, loops = walkthrough(REPORTS_FOLDER)
    labels = NAMES
