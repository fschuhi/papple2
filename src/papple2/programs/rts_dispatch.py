"""A tiny program that jumps with RTS: two commands, called through a
jump table, the way many Apple II programs dispatch.

dispatch takes a command number in A. It pushes the command's address
minus one from table, high byte first, and "returns" with RTS: RTS pulls
that address, adds one, and continues there. So the RTS is a jump, not a
return. The command's own RTS then returns behind the JSR that called
dispatch.

boot() gives a ready machine, the program at $6000 and PC there:
run(rts_dispatch.boot(), 24, Tiling, StackTracking) at the prompt. 24
instructions run it to its end; after them, PC stands at $6023, the byte
behind done's NOP.
"""

from papple2.core.emulator import Emulator
from papple2.debug.assembler import assemble

# Must match the *= line of PROGRAM.
LOAD_ADDRESS = 0x6000

# The table holds each command's address minus one, since RTS adds one
# to the address it pulls. It lies between the code and done: data that
# never runs.
PROGRAM = """
        *=$6000
        LDA #$00
        JSR dispatch     ; command 0
        LDA #$01
        JSR dispatch     ; command 1
        JMP done
dispatch ASL             ; A * 2: index into the table of words
        TAX
        LDA table+1,X    ; high byte of the command's address - 1
        PHA
        LDA table,X      ; low byte
        PHA
        RTS              ; "returns" into the command
cmd0    INC $10
        RTS              ; a real return: behind the JSR
cmd1    INC $11
        RTS
table   .WORD cmd0-1
        .WORD cmd1-1
done    NOP
"""


def boot() -> Emulator:
    """The program, ready to run: at LOAD_ADDRESS, and PC there."""
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(LOAD_ADDRESS, assemble(PROGRAM))
    emulator.cpu.PC = LOAD_ADDRESS
    return emulator
