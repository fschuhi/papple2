import unittest
import re
from papple2.debug.Assembler import *
from papple2.debug.Disassembler import *
from papple2.core.Apple import *


class TestWaves(unittest.TestCase):

    def setUp(self):
        self.apple2 = Apple2(no_display=True)
        self.apple2.memory.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN' )
        self.cpu = self.apple2.cpu  # type: CPU
        self.dis = Disassembler(self.cpu, None, None)
        self.asm = Assembler()

    def store( self, byte_array, target ):
        for index, byte in enumerate(byte_array):
            self.cpu.memory._mem[target + index] = byte

    def compile(self, program):
        tokens = self.asm.tokenize( program, verbose=False )
        code = self.asm.generate_code( tokens, verbose=False )
        return self.asm.to_byte_array( code )

    def run_to_PC( self, end_pc, dump=None ):
        while True:
            if isinstance(end_pc, int):
                if self.cpu.PC == end_pc:
                    break
            else:
                if self.cpu.PC in end_pc:
                    break
            if dump is not None:
                dump(self.cpu)
            self.cpu.do_next_step()

    def run_to_RTS(self, pc, dump=None):
        self.cpu.PC = pc
        while self.cpu.last_opcode != 0x60:
            self.cpu.do_next_step()
            if dump is not None:
                dump(self.cpu)

    def disassemble( self, address):
        instruction, length = self.dis.collect_op_info( address )
        bytes = instruction['bytes']

        operand = '' if 'operand' not in instruction else instruction['operand']

        mnemonic = instruction['mnemonic']
        str_bytes = hexbyte(bytes[0])
        str_bytes += ' ' + hexbyte(bytes[1]) if len(bytes) > 1 else ''
        str_bytes += ' ' + hexbyte(bytes[2]) if len(bytes) > 2 else ''

        return (length, "{0:<5}  {1:<8}    {2:<5} {3:<10}".format(
            hexaddr(address),
            str_bytes,
            mnemonic,
            operand
        ))

    def disassemble_instructions( self, address, instructions=1 ):
        i = 0
        pc = address
        while i != instructions:
            length, disassembled = self.disassemble(pc)
            print(disassembled)
            i += 1
            pc += length

    def label_2byte_address(self, label):
        address = self.asm.labels[label.upper()]
        hi = address >> 8
        lo = address & 0x00ff
        return lo, hi

    @unittest.skip("WIP: wave-input patch experiment; ends in sys.exit(0) with unreachable code after")
    def test_input_wave(self):
        byte_array = self.compile( """
                *=$8600

        ; Robotron defines
                prepScreen = $4f25      ; clear screen
                showText = $51b8        ; show text in stash below JSR
                waitKbdControls = $4242 ; wait for key input
                wave_in_game = $1407    ; wave number (zero-based)

        ; zp variables
                state = $50
                event = $51
                first_digit = $52
                second_digit = $53
                wave = $54

        ; keys (high bit 0)
                ch_0 = #$30
                ch_colon = #$3A         ; comes after <9> in Apple, see check_is_number
                ch_left = #$08
                ch_return = #$0d
                ch_escape = #$1b
                ch_space = #$20

        ; state indexes into rts_table
                s_hasNone = #$00
                s_hasOne = #$01
                s_hasTwo = #$02
                s_exit = #$03

        choose_wave:                    ; ENTRY POINT
                LDA s_hasNone
                STA state

                LDA ch_space            ; start w/ empty input field
                STA first_digit
                STA second_digit

                JSR	prepScreen
                JSR	showText

                .byte	0D,09,28
                .byte   "CHOOSE WAVE (1-99): "
                .byte   00

        next_char:                      ; main loop
                JSR show_digits
                JSR	waitKbdControls

                CMP ch_escape           ; <Escape> breaks
                BEQ break

                CMP ch_return           ; <Return> is a valid char, concludes input (if possible)
                BEQ .send_event

                CMP ch_left             ; <Left> removes last digit
                BEQ .send_event

                check_is_number         ; only chars <0> to <9> allowed
                BCC next_char           ; carry cleared if not in <0> to <9>

            .send_event:
                STA event               ; dispatch event
                JSR dispatch_event

                LDA state               ; check if we should exit, i.e. user has entered a number
                CMP s_exit
                BEQ exit

                JMP next_char

        exit:
                DEC wave                ; wave input was 1-99, internally the waves start w/ 0
                LDX wave                ; returned wave is != $ff, i.e. valid
        halt0:  RTS

        break:
                LDA wave_in_game        ; sync internal wave zp var w/ ingame var
                STA wave
                LDX #$ff                ; break indicated by $ff
        halt1:  RTS

        show_digits:
                LDA first_digit         ; modify the 2 .byte below, at .digits
                STA .digits
                LDA second_digit
                STA .digits+1
                JSR showText            ; display
                .byte	0d,1d,28        ; X=1d (character #$00-27, 40 chars), Y=28 (of 192 pixel lines)
            .digits
                .byte   20,20           ; <space><space>
                .byte   00
                RTS

        check_is_number:
                ; http://6502.org/tutorials/compare_instructions.html
                ;    N Z C
                ; <: * 0 0
                ; =: 0 1 1
                ; >: * 0 1
                CMP ch_0                ; <0>
                BCS .greater_than_zero
                RTS                     ; is less than <0>, carry cleared
            .greater_than_zero:
                CMP ch_colon
                BCC .is_number          ; check if less than <:> (i.e. is less than <9>)
                CLC                     ; indicate it's not a number (carry cleared)
                RTS
            .is_number:
                SEC                     ; indicate it's a number (carry set)
                RTS

        dispatch_event:
                LDA state               ; state index into RTS table
                ASL                     ; table has 16bit addresses
                TAX
                LDA rts_table+1,X       ; push hibyte first
                PHA
                LDA rts_table,X         ; push lobyte second, will be popped first by RTS
                PHA
                LDA event               ; state subroutines get the event in A
                RTS

        state_hasNone:
                CMP ch_return           ; ignore Return
                BEQ .hasNone_done
                CMP ch_left
                BEQ .hasNone_done       ; ignore Left Arrow

                STA first_digit         ; ASSUMPTION (enforced by main loop): <0> - <9>
                LDA s_hasOne            ; we now have exactly 1 digit
                STA state               ; next state called by dispatch_event will be state_hasOne

            .hasNone_done:
                RTS

        state_hasOne:
                CMP ch_return
                BNE .hasOne_check_left

                LDA first_digit         ; <Return>, so calculate wave
                SEC
                SBC ch_0                ; first_digit in A from above, convert to number, sets Z if zero
                BEQ .hasOne_done        ; user entered <0> which is an invalid wave number - ignored
                STA wave
                LDA s_exit              ; main loop will exit with success
                STA state
            .hasOne_done
                RTS

            .hasOne_check_left
                CMP ch_left
                BNE .hasOne_add_digit
                LDA ch_space            ; clear the digit as shown on screen
                STA first_digit
                LDA s_hasNone           ; we don't have any digits anymore
                STA state
                RTS

            .hasOne_add_digit
                STA second_digit
                LDA s_hasTwo            ; we now have exactly 2 digits
                STA state
                RTS

        state_hasTwo:
                CMP ch_return
                BNE .hasTwo_check_left

                LDA first_digit         ; multiply first digit by 10
                SEC
                SBC ch_0
                ASL                     ; http://6502.org/source/integers/fastx10.htm
                STA wave
                ASL
                ASL
                CLC
                ADC wave
                STA wave

                LDA second_digit        ; add second digit
                SEC
                SBC ch_0
                CLC
                ADC wave                ; sets Z if zero
                BEQ .hasTwo_done        ; user entered <0><0> which is an invalid wave number - ignored

                STA wave                ; it's a valid wave number ...
                LDA s_exit
                STA state               ; ... so exit the main loop with success
                RTS

            .hasTwo_check_left
                CMP ch_left
                BNE .hasTwo_replace
                LDA ch_space            ; clear 2nd digit as shown on screen
                STA second_digit
                LDA s_hasOne            ; we now have exactly 1 digit
                STA state
                RTS

            .hasTwo_replace
                STA second_digit        ; replace second digit, no state change

            .hasTwo_done
                RTS

        state_exit:
                RTS                     ; we do nothing here, just a state to indicate success

        hook_4071:                      ; $4071	8D 07 14	STA	$1407 => overwrite w/ JSR hook_4071
                LDX wave                ; X is intentional, A used for other init stuff
                STX wave_in_game
                RTS

        hook_4b67:                      ; $4B67	20 25 4F	JSR	$4F25 => overwrite w/ JMP hook_4b67
                JSR choose_wave
                CPX #$ff                ; did we break?
                BNE continue_controls
                JMP $4be6               ; use chooseControl break (PLA / PLA / JMP $4060)

        continue_controls:
                JSR prepScreen          ; overwritten by hook
                JMP $4b6a               ; continue immediately behind the prep_screen

        rts_table:
                .word   state_hasNone-1
                .word   state_hasOne-1
                .word   state_hasTwo-1
                .word   state_exit-1
            """)

        self.store(byte_array, 0x8600)  # was 0x8600, 0x7e8d, 0x1e00
        print(len(byte_array))

        mem = self.apple2.memory._mem

        lo, hi = self.label_2byte_address('hook_4b67')
        mem[0x4b67] = 0x4c
        mem[0x4b68] = lo
        mem[0x4b69] = hi

        lo, hi = self.label_2byte_address('hook_4071')
        mem[0x4071] = 0x20
        mem[0x4072] = lo
        mem[0x4073] = hi

        self.apple2.memory.save_image(0x2dfd, 0x9000, "tmp/ROBOTRON#062DFD.BIN")
        #self.apple2.memory.save_image(0x1e00, 0x9000, r"tmp\ROBOTRON#061E00.BIN")
        sys.exit(0)

        self.run_to_PC(0x4063)
        assert self.cpu.PC == 0x4063
        self.cpu.PC = 0xB000

        self.disassemble_instructions(0xb000, 145)

        self.labels_by_address = {}
        for key, value in self.asm.labels.items():
            self.labels_by_address[value] = key

        do_exit = self.asm.labels['HALT0']
        do_break = self.asm.labels['HALT1']
        self.kbd = [
            0x0d,   # return on empty digits, does nothing
            0x31,   # first digit
            0x15,   # clear first digit
            0x30,   # enter 0 as 10-digit
            0x30,   # second digit
            0x0d,   # nothing should happen
            0x39,   # enter 9 as 2nd digit
            0x0d,
        ]
        self.cpu.op_hook = self.op_hook
        if '.TEST' in self.asm.labels:
            do_test = self.asm.labels['.TEST']
            self.run_to_PC( [do_exit, do_break, do_test], self.dump)
        else:
            self.run_to_PC( [do_exit, do_break], self.dump)

        self.apple2.display.refresh_hires()
        time.sleep(1)

        # compile from hook.asm file
        # TDO: more test methods
        # TODO: https://www.tutorialspoint.com/python/python_reg_expressions.htm


    def op_hook(self, cpu):
        if cpu.PC == 0x4242: # waitKbdControls
            char = self.kbd[0]
            print("op_hook (waitKbdControls)", hexbyte(char))
            cpu.A = char
            del self.kbd[0]
            cpu.RTS()
            return True

    def dump(self, cpu):
        return
        # print(hexaddr(cpu.PC), hexaddr(cpu.last_PC))
        if cpu.last_PC >= 0xB000:
            if cpu.last_PC in self.labels_by_address:
                print(self.labels_by_address[cpu.last_PC])

            length, disassembled = self.disassemble(cpu.last_PC)
            matchObj = re.match(r'PC=[a-f0-9]+ (.+)', str(self.cpu))
            print(disassembled, ";", matchObj.group(1))


if __name__ == "__main__":
    unittest.main()
