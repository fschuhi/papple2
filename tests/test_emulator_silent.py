from pysm import Event
from papple2.debug.checkpoints import KeyScript
from papple2.core.emulator import Emulator, after_instructions, at_address


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
    emulator.run(until=after_instructions(1000))
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

    `KeyScript` is a checkpoint: a function `Emulator.run` calls before
    every instruction. It waits until `emulator.instructions` reaches a
    scheduled count, then calls `emulator.press_key`, the same call the
    pygame window makes on a real keypress. The CPU never learns this
    happened directly; it only sees the effect on its next read of
    $C000, wherever in the polling loop that happens to land.
    """
    asm, emulator = make_emulator("""
            *=$6000

    loop:   LDA $C000       ; read the keyboard data line: bit 7 set = key waiting
            BPL loop        ; bit 7 clear -> keep polling
            STA $0300       ; store the raw byte (high bit still on)
            LDA $C010       ; clear the keyboard strobe
    halt:   JMP halt        ; spin here forever -- our known address
    """)

    keys = KeyScript([(300, 'A')])
    emulator.add_checkpoint(keys.press_keys)

    emulator.run(until=at_address(asm.labels['HALT']))

    assert emulator.mem[0x0300] == ord('A') | 0x80


def test_checkpoint_stop_halts_headless_run():
    """
    A checkpoint-requested stop (execute=False) has to act like a real
    halt when there's no window to resume it from -- otherwise `run()`
    never returns. This exercises that path directly, with no `until`
    involved at all: the checkpoint below is the only thing stopping it.
    """
    emulator = Emulator(no_display=True)
    emulator.load_image(0x2dfd, 'data/bin/ROBOTRON.BIN')

    def stop_after_10(e):
        return (True, e.instructions < 10)  # (active, execute)

    emulator.add_checkpoint(stop_after_10)
    emulator.run()  # no `until` -- only the checkpoint can stop this

    assert emulator.instructions == 10
    assert emulator.states.leaf_state.name == 'Stopped'


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
