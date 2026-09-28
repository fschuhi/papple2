#!/usr/bin/env python3

# http://rogerdudler.github.io/git-guide/

# snippets
# http://www.obelisk.me.uk/6502/maclib.inc

# http://wilsonminesco.com/StructureMacros/
# http://wilsonminesco.com/6502primer/PgmWrite.html
# http://wilsonminesco.com/6502primer/PgmTips.html
# http://wilsonminesco.com/stacks/index.html

# https://www.lysator.liu.se/~nisse/misc/6502-mul.html
# http://nparker.llx.com/a2/mult.html

# https://news.ycombinator.com/item?id=11661313
# http://www.capstone-engine.org/documentation.html
# https://bitbucket.org/mihaila/bindead/wiki/Home
# https://www.hopperapp.com
# https://www.hex-rays.com/products/ida/

import time
from collections.abc import Callable
from pickle import Pickler, Unpickler

from papple2.util import hexbyte, Ascii2Apple2Ascii, Apple2Ascii2Ascii
from papple2.core.apple import Apple2
from papple2.core.cpu import CPU
from papple2.core.window import PygameWindow, NoWindow
from pysm import State, StateMachine, Event

# The two kinds of functions Emulator.run() calls on every instruction.
# A checkpoint returns (stay active, execute this instruction); an `until`
# condition returns True when run() should stop. `type` aliases are lazy,
# so they can name Emulator before the class is defined below.
type Checkpoint = Callable[[Emulator], tuple[bool, bool]]
type Until = Callable[[Emulator], bool]

class EmulatorRunningState( StateMachine ):
    def __init__(self, emulator_states: "EmulatorStates") -> None:
        super().__init__('Running')
        self.emulator_states = emulator_states
        self.emulator = self.emulator_states.emulator
        self.apple2 = self.emulator.apple2
        self.cpu = self.emulator.cpu
        self.window = self.emulator.window

    def register_handlers(self) -> None:
        self.handlers = {
            'enter': self.on_enter,
            'exit': self.on_exit,
            'breakpoint': self.on_breakpoint,
            'key': self.on_key,
        }

    def on_enter(self, state: State, event: Event) -> None:
        self.emulator.executing = True

    def on_exit(self, state: State, event: Event) -> None:
        self.emulator.executing = False

    def on_breakpoint( self, state: State, event: Event ) -> None:
        self.window.status("execution stopped (breakpoint), %s" % str(self.cpu))

    def on_key(self, state: State, event: Event) -> None:
        key = event.cargo['key']
        self.emulator.press_key(key)


class EmulatorStoppedState( StateMachine ):
    def __init__(self, emulator_states: "EmulatorStates") -> None:
        super().__init__('Stopped')
        self.emulator_states = emulator_states
        self.emulator = self.emulator_states.emulator
        self.window = self.emulator.window
        self.cpu = self.emulator_states.cpu
        self.mem = self.emulator_states.mem

    def register_handlers(self) -> None:
        self.handlers = {
            'enter': self.on_enter,
            'exit': self.on_exit,
            'd': self.on_d,
        }

    def on_enter(self, state: State, event: Event) -> None:
        # formerly known as suspend_execution()
        self.window.status("execution stopped, %s" % str(self.cpu))

    def on_exit(self, state: State, event: Event) -> None:
        # formerly known as resume_execution()
        self.window.status("execution resumed, %s" % str(self.cpu))

    def on_d(self, state: State, event: Event) -> None:
        self.window.status(str(self.cpu))


class EmulatorStates:

    def __init__(self, emulator: "Emulator") -> None:
        self.emulator = emulator
        self.apple2 = self.emulator.apple2
        self.display = self.apple2.display
        self.cpu: CPU = self.apple2.cpu
        self.mem: list[int] = self.apple2.memory._mem

        self.sm = StateMachine('emulator')

        running = EmulatorRunningState(self)
        stopped = EmulatorStoppedState(self)

        # kept around so code outside EmulatorStates can attach its own
        # handlers, e.g. `emulator.states.stopped_state.handlers['l'] = ...`
        self.running_state = running
        self.stopped_state = stopped

        self.sm.add_state(running, initial=True)
        self.sm.add_state(stopped)

        halt = State('halt')
        self.sm.add_state(halt)

        self.sm.add_transition(running, stopped, events=['ctrlx'])
        self.sm.add_transition(stopped, running, events=['ctrlx'])
        self.sm.add_transition(running, stopped, events=['breakpoint'])

        self.sm.add_transition(running, halt, events=['halt'])
        self.sm.add_transition(stopped, halt, events=['halt'])

        # fire_events_on_init: the initial state's entry action runs, as
        # Harel's statecharts demand -- pysm's default would skip it
        self.sm.initialize(fire_events_on_init=True)


    @property
    def leaf_state(self) -> State:
        return self.sm.leaf_state

    def dispatch(self, event: Event) -> None:
        return self.sm.dispatch(event)


def after_instructions(n: int) -> Until:
    def until(emulator: "Emulator") -> bool:
        return emulator.instructions >= n
    return until


def at_address(address: int) -> Until:
    def until(emulator: "Emulator") -> bool:
        return emulator.cpu.PC == address
    return until


# Emulator.run() asks the window for keyboard/window events and redraws only
# every WINDOW_POLL_INTERVAL loop passes, not on every instruction: calling
# pygame.event.get() once per instruction took about a third of the windowed
# run time (cProfile, Lode Runner, 2026-09-23). Checkpoints still run on
# every instruction, so breakpoints and `until` stop exactly where they did.
WINDOW_POLL_INTERVAL = 1000

# The Apple II's 6502 runs at about 1.023 MHz. Windowed runs are throttled
# to `speed` times this clock (see throttle_delay); headless runs and tests
# are never throttled.
APPLE_II_CYCLES_PER_SECOND = 1_023_000


def throttle_delay(cycles: int, elapsed: float, speed: float) -> float:
    """Seconds to sleep so that `cycles` emulated cycles take at least as
    long as on an Apple II running at `speed` times its real clock.
    `elapsed` is the wall-clock time those cycles actually took. Returns 0.0
    when emulation is already slower than that."""
    due = cycles / (APPLE_II_CYCLES_PER_SECOND * speed)
    return max(0.0, due - elapsed)


class Emulator:

    def __init__(self, no_display: bool = False, quiet: bool = True, frame_rate: int = 40, data_dir: str | None = None, speed: float | None = 1.0) -> None:
        self.apple2: Apple2 = Apple2( no_display, quiet, data_dir )
        self.display = self.apple2.display
        self.cpu: CPU = self.apple2.cpu
        self.mem: list[int] = self.apple2.memory._mem
        self.window = NoWindow() if no_display else PygameWindow( self )

        self.states = EmulatorStates( self )

        self.elapsed_frame = 1 / int(frame_rate)
        self.last_ticks = time.monotonic()

        # 1.0 = a real Apple II, 3.0 = three times as fast, None = unthrottled
        self.speed = speed

        self.checkpoints = []
        self._until_checkpoint = None

        self.instructions = 0


    def pickle(self, pickler: Pickler) -> None:
        # pickle apple2, including all parts of Apple2 (e.g. Memory, CPU)
        self.apple2.pickle( pickler )

        pickler.dump(self.elapsed_frame)
        pickler.dump(self.last_ticks)

    def unpickle(self, unpickler: Unpickler) -> None:
        self.apple2.unpickle( unpickler )
        self.elapsed_frame = unpickler.load()
        self.last_ticks = unpickler.load()

    """
    BIN loading
    """

    def load_image(self, start_address: int, fn: str) -> None:
        self.apple2.memory.load_image(start_address, fn)
        if self.apple2.cpu.PC is None:
            self.apple2.cpu.PC = start_address

    """
    event loop
    """

    def add_checkpoint( self, func: Checkpoint ) -> None:
        active = True
        self.checkpoints.append( (active, func) )


    def press_key(self, ascii_code: str | int) -> None:
        # high bit always set
        apple2key = Ascii2Apple2Ascii(ascii_code)
        self.apple2.softswitches.kbd = apple2key
        print(self.cpu.cycles, "pressed (pygame)", hexbyte(Apple2Ascii2Ascii(apple2key)))


    def is_executing(self) -> bool:
        return self.states.leaf_state.name == 'Running'


    def run(self, until: Until | None = None) -> None:

        self.instructions = 0

        if self._until_checkpoint is not None:
            self.checkpoints.remove(self._until_checkpoint)
            self._until_checkpoint = None

        if until is not None:
            def check_until(emulator: "Emulator") -> tuple[bool, bool]:
                return (False, False) if until(emulator) else (True, True)
            self._until_checkpoint = (True, check_until)
            self.checkpoints.append(self._until_checkpoint)

        # exit event loop via setting exit_while, to do cleanup afterwards
        exit_while = False
        # counts loop passes, not instructions: while Stopped no instruction
        # runs, but the window must still be polled, or Ctrl-X could never
        # resume execution
        passes = 0
        # (wall-clock time, cycles) when throttling last (re)started; reset
        # while execution is stopped, so a resumed run doesn't race to catch up
        throttle_start = None
        while not exit_while:

            if self.is_executing():
                for index, (active, func) in enumerate(self.checkpoints):
                    if active:
                        (continue_active, execute) = func(self)
                        if not execute:
                            self.states.dispatch(Event('breakpoint'))
                            if isinstance(self.window, NoWindow):
                                # no window means no keyboard: nothing can ever
                                # send ctrlx or halt, so a checkpoint-requested
                                # stop has to be a real halt here, not a pause
                                exit_while = True
                        else:
                            if not continue_active:
                                self.checkpoints[index] = False, func

            if self.is_executing():
                # IMPORTANT: we first execute the current opcode (i.e. where pc points to)...
                self.cpu.do_next_step()

                self.instructions += 1

            passes += 1
            if passes % WINDOW_POLL_INTERVAL == 0:
                if self.speed is not None and not isinstance(self.window, NoWindow):
                    if not self.is_executing():
                        throttle_start = None
                    elif throttle_start is None:
                        throttle_start = (time.monotonic(), self.cpu.cycles)
                    else:
                        start_time, start_cycles = throttle_start
                        delay = throttle_delay(
                            self.cpu.cycles - start_cycles,
                            time.monotonic() - start_time,
                            self.speed,
                        )
                        if delay > 0:
                            time.sleep(delay)

                # empty the window's pending events
                for event in self.window.poll():
                    if event.name == 'halt':
                        self.states.dispatch(event)
                        exit_while = True
                        break
                    self.states.dispatch(event)

                # after we've emptied the event queue we can update the screen
                self.window.present()

            if until is not None and not self.is_executing():
                exit_while = True

        # do some cleanup here
        print(self.states.leaf_state.name)
