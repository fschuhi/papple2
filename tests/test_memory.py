from pathlib import Path

import pytest

from papple2.core.memory import Memory


def test_load(memory: Memory) -> None:
    memory.load_test_data(0x1000, [0x01, 0x02, 0x03])
    assert memory.read_byte(0x1000) == 0x01
    assert memory.read_byte(0x1001) == 0x02
    assert memory.read_byte(0x1002) == 0x03


def test_write(memory: Memory) -> None:
    memory.write_byte(0x1000, 0x11)
    memory.write_byte(0x1001, 0x12)
    memory.write_byte(0x1002, 0x13)
    assert memory.read_byte(0x1000) == 0x11
    assert memory.read_byte(0x1001) == 0x12
    assert memory.read_byte(0x1002) == 0x13


def test_load_image_fills_memory_up_to_ffff(tmp_path: Path) -> None:
    # An image that ends exactly at $FFFF must still load: this is the edge
    # right next to the "does not fit" guard, like the 12K ROM at $D000.
    image = tmp_path / "image.bin"
    image.write_bytes(bytes(range(1, 17)))  # 16 bytes: $01..$10
    memory = Memory()

    memory.load_image(0xFFF0, str(image))

    assert memory.read_byte(0xFFEF) == 0x00  # untouched, just before the image
    assert memory.read_byte(0xFFF0) == 0x01
    assert memory.read_byte(0xFFFF) == 0x10
    assert len(memory._mem) == 0x10000


def test_load_image_refuses_an_image_that_does_not_fit(tmp_path: Path) -> None:
    image = tmp_path / "too_big.bin"
    image.write_bytes(bytes(17))  # one byte more than fits at $FFF0
    memory = Memory()

    with pytest.raises(ValueError):
        memory.load_image(0xFFF0, str(image))

    # the guard fires before anything is copied: memory stays 64K
    assert len(memory._mem) == 0x10000


# Every kind of access reaches the same memory; the kind only says why the
# CPU accesses a byte (docs/instrumentation-design.md, section 3). Hook lists
# per kind will build on this.

READ_KINDS = ["read_opcode", "read_operand", "read_pointer", "read_data", "read_immediate", "read_stack", "read_vector"]
WRITE_KINDS = ["write_data", "write_stack"]


@pytest.mark.parametrize("method", READ_KINDS)
def test_every_kind_of_read_returns_what_read_byte_returns(memory: Memory, method: str) -> None:
    memory.load_test_data(0x1000, [0x42])

    assert getattr(memory, method)(0x1000) == memory.read_byte(0x1000) == 0x42


@pytest.mark.parametrize("method", WRITE_KINDS)
def test_every_kind_of_write_lands_where_write_byte_would(memory: Memory, method: str) -> None:
    getattr(memory, method)(0x1000, 0x42)

    assert memory.read_byte(0x1000) == 0x42


WORD_KINDS = ["read_operand_word", "read_pointer_word", "read_vector_word"]


@pytest.mark.parametrize("method", WORD_KINDS)
def test_word_reads_take_the_low_byte_first(memory: Memory, method: str) -> None:
    memory.load_test_data(0x1000, [0x34, 0x12])

    assert getattr(memory, method)(0x1000) == 0x1234


def test_read_pointer_word_wraps_within_the_page(memory: Memory) -> None:
    # like JMP ($10FF) on the 6502: the high byte comes from $1000, not $1100
    memory.load_test_data(0x10FF, [0x34])
    memory.load_test_data(0x1000, [0x12])
    memory.load_test_data(0x1100, [0x99])

    assert memory.read_pointer_word(0x10FF) == 0x1234
