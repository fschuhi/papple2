import pytest
from papple2.core.apple import Display, Speaker, SoftSwitches, Apple2


@pytest.fixture
def display():
    return Display(apple2=None, no_display=True)


@pytest.fixture
def speaker():
    return Speaker(quiet=True)


@pytest.fixture
def switches(display, speaker):
    return SoftSwitches(display, speaker)


def test_keyboard_strobe(switches):
    switches.kbd = 0xC1  # e.g. 'A' with the high bit set, as the real keyboard would deliver it
    assert switches.read_byte(0xC000) == 0xC1
    assert switches.read_byte(0xC010) == 0x00
    assert switches.kbd == 0x41  # strobe cleared: high bit gone


def test_txtclr_txtset(switches, display):
    switches.read_byte(0xC051)  # txtset first, so txtclr has something to undo
    switches.read_byte(0xC050)
    assert not display.text

    switches.read_byte(0xC051)
    assert display.text
    assert not display.colour


def test_mixclr_mixset(switches, display):
    switches.read_byte(0xC052)
    assert not display.mix

    switches.read_byte(0xC053)
    assert display.mix
    assert display.colour


def test_lowscr_hiscr(switches, display):
    switches.read_byte(0xC054)
    assert display.page == 1

    switches.read_byte(0xC055)
    assert display.page == 2


def test_lores_hires(switches, display):
    switches.read_byte(0xC056)
    assert not display.high_res

    switches.read_byte(0xC057)
    assert display.high_res


def test_write_byte_ignores_value_but_triggers_same_effect(switches, display):
    # SoftSwitches is "ROM": writing doesn't store a value, it just triggers
    # the same read-side effect, regardless of what's written.
    switches.write_byte(0xC051, 0x00)
    assert display.text


def test_read_byte_out_of_range_raises(switches):
    with pytest.raises(AssertionError):
        switches.read_byte(0xD000)


def test_memory_mapped_write_reaches_softswitches():
    # One level up from the unit tests above: proves the $C0-page routing
    # in Memory.write_byte actually dispatches to SoftSwitches, not just
    # that SoftSwitches works when called directly.
    apple2 = Apple2(no_display=True)
    apple2.memory.write_byte(0xC051, 0x00)
    assert apple2.display.text
