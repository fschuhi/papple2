import unittest
from papple2.util import hexaddr
from papple2.debug.Assembler import *
from papple2.core.CPU import CPU
from papple2.core.Apple import Apple2


class TestAssembler(unittest.TestCase):

    def setUp(self):
        self.apple2 = Apple2(no_display=True)
        self.cpu = self.apple2.cpu  # type: CPU
        self.asm = Assembler()

    def compile(self, program):
        tokens = self.asm.tokenize( program, verbose=False )
        code = self.asm.generate_code( tokens, verbose=False )
        return self.asm.to_byte_array( code )

    def beautify_byte_array(self, s):
        lines = s.splitlines()
        new = ''
        for index, line in enumerate(lines):
            if index > 0:
                new += '\n'
            new += line.strip()
        return new.strip()

    def run_to_RTS(self, byte_array, pc, max_instructions=1000, dump=None):
        for index, byte in enumerate(byte_array):
            self.cpu.memory._mem[pc+index] = byte
        self.cpu.PC = pc
        i = 0
        # while cpu.memory._mem[cpu.program_counter] != 0x60 and i!= 100:
        while self.cpu.last_opcode != 0x60 and i!= max_instructions:
            if dump is not None:
                dump(self.cpu)
            self.cpu.do_next_step()
            i += 1
        if i == max_instructions:
            print("max instructions reached")

    def dump_chromatix01_state( self ):
        print('%s A=%s X=%s $E0=%s $E1=%s $E2=%s' % (
              hexaddr( self.cpu.PC ),
              hexbyte( self.cpu.A ),
              hexbyte( self.cpu.X ),
              hexbyte(self.cpu.memory._mem[0xe0]),
              hexbyte(self.cpu.memory._mem[0xe1]),
              hexbyte(self.cpu.memory._mem[0xe2]),
              ))

    def test_dump(self, addresses=None, show_stack=False, show_status=False):
        registers = 'AXY'
        res = ['PC=%s' % hexaddr(self.cpu.PC, show_dollar=False)]
        for char in 'AXY':
            res.append('%s=%s' % (char, hexbyte(getattr(self.cpu, char ))))

        if addresses is not None:
            for address in addresses:
                res.append('%s=%s' % (hexaddr(address), hexbyte(self.cpu.memory._mem[address])))

        show_stack = True
        if show_stack:
            res.append('SP=%s' % hexbyte(self.cpu.SP))
            s = self.cpu.STACK_PAGE + self.cpu.SP + 1
            sp_address = self.cpu.memory.read_word(s)
            res.append('(SP)=%s' % hexbyte(self.cpu.memory._mem[sp_address]) if sp_address <= 0xFFFF else '?')

        show_status = True
        if show_status:
            res.append( 'F=%s' % ''.join([
                'C' if self.cpu.carry_flag else '_',
                'Z' if self.cpu.zero_flag else '_',
                'I' if self.cpu.interrupt_disable_flag else '_',
                'D' if self.cpu.decimal_mode_flag else '_',
                'B' if self.cpu.break_flag else '_',
                'O' if self.cpu.overflow_flag else '_',
                'S' if self.cpu.sign_flag else'_'
            ]))
        print(' '.join(res))


    def test_chromatix01(self):
        byte_array = self.compile( """
                ; Levenstein 1, 8-10
                multiplier = $e0
                multiplicand = $e1
                HResult = $e2

                *=$4C4F
                STA multiplier
                STX multiplicand
                LDA #$00            ; L-result
                STA HResult
                LDX #$08            ; go through all 8 bits
        .L8     ASL                 ; A is L-result (for now, finally X), "Product = 2x Product"
                ROL HResult
                ASL multiplier
                BCC .L7             ; "no addition if next bit is zero"
        .L9     CLC                 ; "add multiplicand to product"
                ADC multiplicand
                BCC .L7
                INC HResult         ; "with carry if necessary"
        .L7     DEX
                BNE .L8             ; "loop until 8 bits are multiplied"
        .L10    TAX                 ; L-result in X
                LDA HResult
                RTS
        """)

        test = self.beautify_byte_array("""
            85 e0 86 e1 a9 00 85 e2 a2 08 0a 26 e2 06 e0 90
            07 18 65 e1 90 02 e6 e2 ca d0 ef aa a5 e2 60
        """)
        self.assertEqual(test, self.asm.byte_array_to_text(byte_array))

        self.cpu.A = 6
        self.cpu.X = 3
        # self.run_to_RTS( cpu, byte_array, pc=0x4C4F, dump=self.dump_chromatix01_state )
        self.run_to_RTS( byte_array, pc=0x4C4F )
        self.assertEqual( self.cpu.X, 0x12 )  # decimal 18
        self.assertEqual( self.cpu.A, 0x00 )
        self.assertEqual(self.cpu.cycles, 197)


    def test_8bit_multiply_02(self):
        byte_array = self.compile( """
                ; Scanlon 120
                multiplier = $20
                multiplicand = $21
                LResult = $22

                *=$2000
                STA multiplier
                STX multiplicand
        MLT8    LDA #$00            ; "clear MSBY of product"
                STA LResult
                LDX #$08            ; "multiplier bit count = 8"
        NXTBT   LSR multiplier      ; "get next multiplier bit"
                BCC ALIGN           ; "multiplier = 1?"
                CLC                 ; "yes, add multiplicand"
                ADC multiplicand
        ALIGN   ROR                 ; "shift product right" - - this was LSR, wrong because we need the carry from ADC
                ROR LResult
                DEX                 ; "decrement bit count"
                BNE NXTBT           ; "loop until 8 bits are done"
                LDX LResult         ; L-result, H-result in A
                RTS
        """)

        self.cpu.reset()
        a = 0x02
        x = 0xEA
        self.cpu.A = a
        self.cpu.X = x
        self.run_to_RTS( byte_array, pc=0x2000 )
        # self.run_to_RTS( byte_array, pc=0x2000, dump=self.dump_chromatix01_state )
        self.assertEqual( (self.cpu.A << 8) + self.cpu.X, a * x )
        self.assertEqual(self.cpu.cycles, 185)

    def test_8bit_multiply_03(self):
        byte_array = self.compile( """
                ; https://www.lysator.liu.se/~nisse/misc/6502-mul.html
                ; http://6502org.wikidot.com/software-math-intmul
                ; This is basically Scanlon's version but using A as the LResult which is faster and saves a zp var

                multiplier = $e0
                multiplicand = $e1

                *=$2000
                STA multiplier
                STX multiplicand
                LDA #$00
                LDX #$08
                LSR multiplier
        loop    BCC no_add
                CLC
                ADC multiplicand
        no_add  ROR
                ROR multiplier
                DEX
                BNE loop
                LDX multiplier     ; L-result, H-result in A
                RTS
        """)

        self.cpu.A = 0xFF
        self.cpu.X = 0xFF
        self.run_to_RTS( byte_array, pc=0x2000 )
        ## self.assertEqual(cpu.x_index, 0x12)  # decimal 18

        cycle_counts = []

        x = 0xFF
        for a in range(0x00, 0x100):
            self.cpu.reset()
            self.cpu.A = a
            self.cpu.X = x
            self.run_to_RTS( byte_array, pc=0x2000 )
            # print(a, x, a*x, cpu.accumulator, cpu.accumulator << 8, cpu.x_index, (cpu.accumulator << 4) + cpu.x_index, a * x)
            self.assertEqual( (self.cpu.A << 8) + self.cpu.X, a * x )
            cycle_counts.append(self.cpu.cycles)

        self.assertEqual( sum(cycle_counts) / float(len(cycle_counts)), 159.0 )

    def test_8bit_bitcount(self):
        byte_array = self.compile( """
                    *=$2000
            ;======================================================
            ; Bit Counting Via a Lookup Table
            ;------------------------------------------------------
            ; The fastest way of figuring out how many bits are set
            ; in a byte is to use a precalculated table and index
            ; into it using either X or Y.
            ;
            ; This method is so simple that you don't need to put
            ; the code in a subroutine for reuse.
            ;
            ; The only downside to this is that it needs a whole
            ; 256 byte page to hold the lookup table.
            ;
            ; Time: 6 cycles (+1 if data table crosses page)
            ; Size: 256 bytes (for data)

            ; Look up table of bit counts in the values $00-$FF

            ;------------------------------------------------------

            ByteAtATime:
                ; x contains value to count the bits in
                LDA ByteBitCounts,X     ; A contains it's bit count
                RTS

            ByteBitCounts:
                .BYTE 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
                .BYTE 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
                .BYTE 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
                .BYTE 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
                .BYTE 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
                .BYTE 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
                .BYTE 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
                .BYTE 4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8
        """)

        self.cpu.A = 0x01
        self.cpu.X = 0x04
        self.run_to_RTS( byte_array, pc=0x2000 )
