from pysm import Event
from papple2.core.emulator import Emulator
from papple2.debug.stop_conditions import instruction_count_reaches, at_address, instruction_count_reaches


def test_create_no_display():
    # 2026-09-11 This results in `AttributeError: 'Display' object has no attribute 'screen'`
    # see `TODO.md` for details on M2.5
    emulator = Emulator(no_display=True)


def test_constructs_without_window():
    emulator = Emulator(no_display=True)
    emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')


def test_run_stops_after_n_instructions():
    emulator = Emulator(no_display=True)
    emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')
    emulator.run(until=instruction_count_reaches(1000))
    assert emulator.instructions == 1000


def test_run_stops_at_address():
    emulator = Emulator(no_display=True)
    emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')
    emulator.run(until=at_address(0x2dfd))
    assert emulator.cpu.PC == 0x2dfd
    assert emulator.instructions == 0


def test_ctrlx_toggles_state():
    emulator = Emulator(no_display=True)
    assert emulator.states.leaf_state.name == 'Running'
    emulator.states.dispatch(Event('ctrlx'))
    assert emulator.states.leaf_state.name == 'Stopped'
    emulator.states.dispatch(Event('ctrlx'))
    assert emulator.states.leaf_state.name == 'Running'


def test_executing_follows_the_state_from_the_start():
    # `executing` mirrors the state machine (a plain flag is cheaper than
    # asking for the state's name). Running's entry and exit actions set it;
    # the entry action also runs on initialize, so the mirror is right from
    # construction on.
    emulator = Emulator(no_display=True)
    assert emulator.executing is True
    emulator.states.dispatch(Event('ctrlx'))
    assert emulator.executing is False
    emulator.states.dispatch(Event('ctrlx'))
    assert emulator.executing is True


def test_keypress_reaches_program(make_emulator):
    """
    Walkthrough: driving papple2 purely from code, no pygame window.

    The assembled program below is a minimal Apple II key reader. It
    polls $C000 (the keyboard data line) until bit 7 is set, stores the
    raw byte at $0300, clears the keyboard strobe by touching $C010,
    then spins forever at `halt` -- a second, separate loop used as the
    known stopping point (the polling loop itself is not a safe `until`
    target, since the emulator passes through it before any key has
    been pressed).

    The key takes the same path as a real keypress in the window: after
    300 instructions `until` stops the run (the state machine goes to
    Stopped via 'breakpoint'), 'ctrlx' resumes it, and a 'key' event
    reaches the Running state's on_key(), which calls press_key(). The
    CPU never learns this happened directly; it only sees the effect on
    its next read of $C000, wherever in the polling loop that happens to
    land.
    """
    asm, emulator = make_emulator("""
            *=$6000

    loop:   LDA $C000       ; read the keyboard data line: bit 7 set = key waiting
            BPL loop        ; bit 7 clear -> keep polling
            STA $0300       ; store the raw byte (high bit still on)
            LDA $C010       ; clear the keyboard strobe
    halt:   JMP halt        ; spin here forever -- our known address
    """)

    emulator.run(until=instruction_count_reaches(300))
    assert emulator.states.leaf_state.name == 'Stopped'
    emulator.states.dispatch(Event('ctrlx'))              # Stopped -> Running
    emulator.states.dispatch(Event('key', key=ord('A')))  # the window's path
    emulator.run(until=at_address(asm.labels['HALT']))

    assert emulator.mem[0x0300] == ord('A') | 0x80


def test_unserved_trap_halts_headless_run(make_emulator):
    """
    A trap that doesn't serve its address (returns False) stops the
    emulator before the instruction there. Without a window there's nothing
    to resume from, so the stop has to act like a real halt -- otherwise
    `run()` never returns. No `until` is involved: the trap is the only
    thing stopping this run.
    """
    asm, emulator = make_emulator("""
            *=$6000

    start:  LDA #$00
            INX
    trap:   NOP             ; the trap sits here
    spin:   JMP spin        ; never reached
    """)

    emulator.add_trap(asm.labels['TRAP'], lambda em: False)
    emulator.run()  # no `until` -- only the trap can stop this

    assert emulator.cpu.PC == asm.labels['TRAP']
    assert emulator.instructions == 2
    assert emulator.states.leaf_state.name == 'Stopped'


def test_served_trap_continues_where_the_handler_points(make_emulator):
    """
    A served trap (returns True) lets the run go on at whatever PC the
    handler set -- the way the disk stand-ins return to their caller.
    Here the handler jumps over the LDA #$FF, so $0300 keeps the $42.
    """
    asm, emulator = make_emulator("""
            *=$6000

    start:  LDA #$42
    skip:   LDA #$FF        ; the trap jumps over this
    store:  STA $0300
    halt:   JMP halt
    """)

    def jump_over(em):
        em.cpu.PC = asm.labels['STORE']
        return True  # served

    emulator.add_trap(asm.labels['SKIP'], jump_over)
    emulator.run(until=at_address(asm.labels['HALT']))

    assert emulator.mem[0x0300] == 0x42


def test_rts_without_matching_jsr_does_not_crash(make_emulator):
    """
    The classic 6502 "computed jump" trick pushes a target address by hand
    (PHA/PHA) and uses RTS to jump to it, with no JSR involved at all. This
    program does exactly that: it never executes a JSR, only two PHAs and an
    RTS, and should land at `landed`. (It began as a regression test for the
    emulator's old JSR/RTS bookkeeping, removed after tag pre-redesign.)
    """
    asm, emulator = make_emulator("""
            *=$6000

    start:  LDA #$60       ; high byte of (landed - 1)
            PHA
            LDA #$06       ; low byte of (landed - 1)
            PHA
            RTS             ; "jumps" to landed via the stack, no JSR involved
    landed: JMP landed
    """)

    emulator.run(until=at_address(asm.labels['LANDED']))

    assert emulator.cpu.PC == asm.labels['LANDED']
