import pytest
from papple2.core.apple import Apple2


@pytest.fixture
def apple2():
    return Apple2(no_display=True)


def test_hires_page1_write_read_roundtrip(apple2):
    for address in (0x2000, 0x2abc, 0x3fff):
        apple2.memory.write_byte(address, 0x55)
        assert apple2.memory.read_byte(address) == 0x55


def test_hires_page2_write_read_roundtrip(apple2):
    for address in (0x4000, 0x4abc, 0x5ffe):
        apple2.memory.write_byte(address, 0xAA)
        assert apple2.memory.read_byte(address) == 0xAA


def test_write_outside_hires_range_does_not_call_display_update(apple2):
    # Spies on display.update to confirm the range check in Memory.write_byte
    # is what keeps rendering out of the way -- not just an accident of no_display.
    calls = []
    apple2.display.update = lambda address, value: calls.append((address, value))

    apple2.memory.write_byte(0x5fff, 0x11)  # just above Memory's checked range
    assert calls == []

    apple2.memory.write_byte(0x5ffe, 0x11)  # last address inside it
    assert calls == [(0x5ffe, 0x11)]


def test_no_display_write_across_full_hires_span_does_not_raise(apple2):
    for address in range(0x2000, 0x6000):
        apple2.memory.write_byte(address, address & 0xFF)

def test_text_page1_write_calls_display_update(apple2):
    calls = []
    apple2.display.update = lambda address, value: calls.append((address, value))

    apple2.memory.write_byte(0x0400, 0xA0)

    assert calls == [(0x0400, 0xA0)]


def test_text_page2_write_calls_display_update(apple2):
    calls = []
    apple2.display.update = lambda address, value: calls.append((address, value))

    apple2.memory.write_byte(0x0800, 0xA0)

    assert calls == [(0x0800, 0xA0)]
