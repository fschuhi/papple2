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

from papple2.util import hexaddr, hexbyte, Ascii2Apple2Ascii, Apple2Ascii2Ascii
from papple2.core.apple import Apple2
from papple2.core.cpu import CPU, JMP_indirect, JMP_absolute, RTS, JSR
from papple2.debug.memory_map import MemoryMap, OpInfo
from papple2.core.hooks import TimeMachine, MemAccessCollector
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

    def action(self, state: State, event: Event) -> None:
        print("action!!!! we are in state '%s', handling event '%s'" % (state.name, event.name))

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
            'left': self.on_left,
            'right': self.on_right,
            'd': self.on_d,
        }

    def on_enter(self, state: State, event: Event) -> None:
        # formerly known as suspend_execution()
        self.emulator.executing = False
        print("on_enter")
        self.window.status("execution stopped, %s" % str(self.cpu))
        self.emulator.time_machine.enable_restoring( )

    def on_exit(self, state: State, event: Event) -> None:
        # formerly known as resume_execution()
        self.emulator.executing = True
        print("on_exit")
        self.emulator.time_machine.disable_restoring( )
        self.window.status("execution resumed, %s" % str(self.cpu))

    def on_left(self, state: State, event: Event) -> None:
        kbd_states = event.cargo['kbd_states']
        print("restore")
        self.emulator.time_machine.restore_prev_state(kbd_states)

    def on_right(self, state: State, event: Event) -> None:
        kbd_states = event.cargo['kbd_states']
        self.emulator.time_machine.restore_next_state(kbd_states)

    def on_d(self, state: State, event: Event) -> None:
        self.window.status(str(self.cpu))


class EmulatorStates:

    def __init__(self, emulator: "Emulator") -> None:
        self.emulator = emulator
        self.apple2 = self.emulator.apple2
        self.display = self.apple2.display
        self.cpu: CPU = self.apple2.cpu
        self.mem: list[int] = self.apple2.memory._mem
        self.map = self.emulator.map

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

        self.sm.initialize()


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


class Emulator:

    def __init__(self, no_display: bool = False, quiet: bool = True, frame_rate: int = 20, time_machine: bool = False, mem_access: bool = False, data_dir: str | None = None) -> None:
        self.apple2: Apple2 = Apple2( no_display, quiet, data_dir )
        self.display = self.apple2.display
        self.cpu: CPU = self.apple2.cpu
        self.mem: list[int] = self.apple2.memory._mem
        self.map: MemoryMap = MemoryMap( self.cpu.memory )
        self.window = NoWindow() if no_display else PygameWindow( self )

        self.states = EmulatorStates( self )

        # Emulator is not stateless => Timemachine would need to save these
        # TODO: disallow tiling and further analysis w/ the memory map if we have used the TimeMachine
        self.jsr_stack = []
        self.prev_info = None

        self.elapsed_frame = 1 / int(frame_rate)
        self.last_ticks = time.monotonic()

        self.checkpoints = []
        self._until_checkpoint = None
        # self.add_checkpoint( RandomTesterCheckpoint(self).checkpoint)
        # self.add_checkpoint( RecordedKeys( ).press_keys )
        # self.add_checkpoint( PrintCharTester( ).LDA_indirect )

        # self.cpu.write_hook = self.write_hook
        self.write_hook_enabled = False

        # TODO: time machine cannot work together w/ tiling (not reliably at least)
        self.time_machine = TimeMachine(self)
        if time_machine:
            self.time_machine.enable_write_hook( )

        self.mem_access = MemAccessCollector(self)
        if mem_access:
            self.mem_access.enable_hooks()

        self.executing = False
        self.instructions = 0
        self.stepsize = 10000


    def pickle(self, pickler: Pickler) -> None:
        # pickle apple2, including all parts of Apple2 (e.g. Memory, CPU)
        self.apple2.pickle( pickler )

        # MemoryMap is the static execution trace capture, not part of the Apple2
        self.map.pickle( pickler )

        pickler.dump(self.elapsed_frame)
        pickler.dump(self.last_ticks)
        pickler.dump(self.jsr_stack)
        pickler.dump(self.prev_info)

    def unpickle(self, unpickler: Unpickler) -> None:
        self.apple2.unpickle( unpickler )
        self.map.unpickle( unpickler )
        self.elapsed_frame = unpickler.load()
        self.last_ticks = unpickler.load()
        self.jsr_stack = unpickler.load()
        self.prev_info = unpickler.load()

    """
    BIN loading
    """

    def load_image(self, start_address: int, fn: str) -> None:
        self.apple2.memory.load_image(start_address, fn)
        if self.apple2.cpu.PC is None:
            self.apple2.cpu.PC = start_address

        # TODO: add exceptions from connecting tiles to stretches in Emulator.load_image(), i.e. before entering the event_loop

    """
    event loop
    """

    def write_hook(self, address: int, newvalue: int) -> bool:
        if not self.write_hook_enabled: return True
        #if address != 0x1407: return True
        #print("PC=%s" % hexaddr(self.cpu.PC))
        #return False
        return True


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
        self.stepsize = 10000
        self.executing = True

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
                self.post_op()

                self.instructions += 1

            passes += 1
            if passes % WINDOW_POLL_INTERVAL == 0:
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


    def event_loop(self) -> None:
        return self.run()


    def post_op(self) -> OpInfo:
        # ASSUMPTION: we are emulating on the execution path, i.e. there CPU is running
        op_address = self.cpu.last_PC
        operand_length = self.cpu.operand_length
        cycles = self.cpu.cycles
        info = self.map.post_op( op_address, operand_length, cycles, self.prev_info )

        # execution_count can be increased because we are executing (see comment above)
        if info.execution_count is None:
            info.execution_count = 1
        else:
            info.execution_count += 1

        opcode = info.opcode
        if info.is_leap():
            if info.is_branch():
                self.handle_branching(info)
            elif opcode == RTS:
                self.handle_rts(info)
            elif opcode == JSR:
                self.handle_jsr(info)
            elif opcode == JMP_absolute or opcode == JMP_indirect:
                self.handle_jmp(info)

        # save info about which path we have taken
        # currently only the last op, but could be reasonably expanded to trap e.g. SEC/BCS
        # TODO: maybe store prev_info in timemachine state, so that we can do tiling even if using the timemachine
        self.prev_info = info

        if self.time_machine:
            self.time_machine.post_op()

        if self.mem_access:
            self.mem_access.post_op()

        return info


    """
    register leaps with MemoryMap
    """

    def handle_branching(self, leap_from_info: OpInfo) -> None:
        branched = self.cpu.branched
        self.map.register_branch( leap_from_info, self.cpu.PC, branched )

    def handle_jmp(self, leap_from_info: OpInfo) -> None:
        self.map.register_jmp( leap_from_info, self.cpu.PC )

    def handle_jsr(self, leap_from_info: OpInfo) -> None:
        self.jsr_stack.append( self.cpu.last_PC )
        self.map.register_jsr( leap_from_info, self.cpu.PC )

    def handle_rts(self, leap_from_info: OpInfo) -> None:
        pc = self.cpu.PC
        assumed_jsr = pc - 3

        # an empty jsr_stack here is not a bug: e.g. tail-call-style code, or the
        # classic PHA/PHA + RTS "computed jump" trick, does an RTS without a
        # matching JSR we tracked. Treat it as an unmatched return, don't crash.
        if len(self.jsr_stack) > 0:
            jsr_on_stack = self.jsr_stack[-1]
            if assumed_jsr == jsr_on_stack:
                # normal case: return to calling JSR (i.e. op after it)
                matched_jsr = jsr_on_stack
                self.jsr_stack.pop()
            else:
                matched_jsr = None
        else:
            matched_jsr = None
        self.map.register_rts( leap_from_info, self.cpu.PC, matched_jsr )  # caller can be None
