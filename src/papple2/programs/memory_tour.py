"""A tiny program that touches memory in every way the cross reference
counts: a program of the walkthrough.

It reads a table with an index and writes it into page 3, builds a pointer
in zero page and reads through it, and writes into the operands of two of
its own instructions: one that reads an address, one that holds an
immediate. A counter in zero page is read and written by one INC.

boot() gives a ready machine, the program at $6000 and PC there:
run(memory_tour.boot(), 38, CrossReferencing) at the prompt. 38
instructions run it to its end; after them, PC stands at $6035, the byte
after done's NOP.
"""

from papple2.core.emulator import Emulator
from papple2.debug.assembler import assemble

# Must match the *= line of PROGRAM.
LOAD_ADDRESS = 0x6000

# The assembler has no operators for the low and high byte of a label, so
# the pointer points at a fixed address, $0300, the page the copy loop
# writes into. The data lies between JMP and done, so it never runs.
PROGRAM = """
        *=$6000
        LDX #$02
copy    LDA table,X     ; a table read: one target, three effective addresses
        STA $0300,X     ; and a table write, into page 3
        DEX
        BPL copy
        LDA #$00
        STA $06         ; the pointer, low byte
        LDA #$03
        STA $07         ; the pointer, high byte: it points at $0300
        LDY #$01
        LDA ($06),Y     ; reads the pointer, then $0301
        LDX #$01
again   LDA lows,X      ; a low byte for patch's operand
        STA patch+1     ; writes into patch's own operand
        STX imm+1       ; writes into imm's own operand: the immediate
patch   LDA $0300       ; reads $0301, then $0300: same instruction, two targets
imm     LDY #$00        ; reads $01, then $00: one immediate, two values
        INC $08         ; read-modify-write: a read and a write at $08
        DEX
        BPL again
        JMP done        ; jump over the data
table   .byte $11,$22,$33
lows    .byte $00,$01
done    NOP
"""


def boot() -> Emulator:
    """The program, ready to run: at LOAD_ADDRESS, and PC there."""
    emulator = Emulator(no_display=True)
    emulator.apple2.memory.load_test_data(LOAD_ADDRESS, assemble(PROGRAM))
    emulator.cpu.PC = LOAD_ADDRESS
    return emulator
