"""A tiny program that jumps with RTS: two routines, called through a
jump table, the way many Apple II programs dispatch.

dispatch takes a routine number in A. It pushes the routine's address
minus one from table, high byte first, and "returns" with RTS: RTS pulls
that address, adds one, and continues there. So the RTS is a jump, not a
return. The routine's own RTS then returns directly after the JSR that
called dispatch.

boot() gives a ready machine, the program at $6000 and PC there:
run(rts_dispatch.boot(), 24, Tiling, StackTracking) at the prompt. 24
instructions run it to its end; after them, PC stands at $6023, the byte
after done's NOP.
"""

from papple2.core.emulator import Emulator
from papple2.debug.assembler import assemble

# Must match the *= line of PROGRAM.
LOAD_ADDRESS = 0x6000

# The table holds each routine's address minus one, since RTS adds one
# to the address it pulls. It lies between the code and done: data that
# never runs.
PROGRAM = """
        *=$6000
        LDA #$00
        JSR dispatch     ; routine 0
        LDA #$01
        JSR dispatch     ; routine 1
        JMP done
dispatch ASL             ; A * 2: index into the table of words
        TAX
        LDA table+1,X    ; high byte of the routine's address - 1
        PHA
        LDA table,X      ; low byte
        PHA
        RTS              ; "returns" into the routine
inc_10  INC $10
        RTS              ; a real return: after the JSR
inc_11  INC $11
        RTS
table   .WORD inc_10-1
        .WORD inc_11-1
done    NOP
"""


def boot() -> Emulator:
    """The program, ready to run: at LOAD_ADDRESS, and PC there."""
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(LOAD_ADDRESS, assemble(PROGRAM))
    emulator.cpu.PC = LOAD_ADDRESS
    return emulator
