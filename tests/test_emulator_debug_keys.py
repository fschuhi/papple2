import contextlib
import io
from pysm import Event
from papple2.core.emulator import Emulator
from papple2.util import hexaddr, hexbyte


def make_zeropage_dump_handler(addresses):
    """
    Returns a pysm handler function -- takes (state, event), prints the
    given addresses. This is "on_l from the outside": nothing here is part
    of papple2's core. papple2's own `on_l` was removed from
    `EmulatorStoppedState` for exactly this reason -- the address list it
    printed was specific to one disassembly project, not core-emulator
    behavior. Any project using papple2 can attach a handler like this one
    to look at whatever memory a particular routine touches.
    """
    def dump(state, event):
        emulator = state.emulator
        for address in addresses:
            print("%s=%s" % (hexaddr(address), hexbyte(emulator.mem[address])))
    return dump


def test_zeropage_dump_handler_reports_given_addresses():
    """
    Attaches a dump handler to the 'l' key on `EmulatorStoppedState`,
    the way `on_l` used to work before it moved out of the core. The
    handler only fires in the 'Stopped' state, so the test drives the
    state machine there first via 'ctrlx' -- the same event a real
    Ctrl-X keypress sends -- before dispatching 'l'.
    """
    emulator = Emulator(no_display=True)
    emulator.mem[0x00] = 0x42
    emulator.mem[0x150a] = 0xff

    emulator.states.stopped_state.handlers['l'] = make_zeropage_dump_handler(
        [0x00, 0x150a]
    )

    emulator.states.dispatch(Event('ctrlx'))  # Running -> Stopped

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        emulator.states.dispatch(Event('l'))

    assert captured.getvalue() == "$0000=42\n$150a=ff\n"
