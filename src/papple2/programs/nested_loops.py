"""A tiny program with two nested loops and one JSR, small enough to
follow by hand: the program of the walkthrough.

boot() gives a ready machine, the program at $6000 and PC there:
run(nested_loops.boot(), 39, Tiling) at the prompt. 39 instructions run it
to its end; after them, PC stands at $6014, the byte behind done's NOP.
"""

from papple2.core.emulator import Emulator
from papple2.debug.assembler import Assembler

# Must match the *= line of PROGRAM.
LOAD_ADDRESS = 0x6000

# sub sits behind the loops, so the JMP jumps over it. LDY and LDX sit in
# front of the two branch targets, so the first tile runs straight through
# addresses that later become entry points.
PROGRAM = """
        *=$6000
        LDY #$02      ; outer loop: 2 passes
outer   LDX #$03      ; inner loop: 3 passes per outer pass
inner   JSR sub
        DEX
        BNE inner
        DEY
        BNE outer
        JMP done      ; jump over sub
sub     INC $10
        RTS
done    NOP
"""


def assemble(program: str) -> list[int]:
    """The bytes of program, from its *= address on."""
    asm = Assembler()
    tokens = asm.tokenize(program, verbose=False)
    return asm.to_byte_array(asm.generate_code(tokens, verbose=False))


def boot() -> Emulator:
    """The program, ready to run: at LOAD_ADDRESS, and PC there."""
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(LOAD_ADDRESS, assemble(PROGRAM))
    emulator.cpu.PC = LOAD_ADDRESS
    return emulator
