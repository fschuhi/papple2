import unittest
from pathlib import Path

import pytest

from papple2.core.memory import Memory


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()

    def test_load(self):
        self.memory.load_test_data(0x1000, [0x01, 0x02, 0x03])
        self.assertEqual(self.memory.read_byte(0x1000), 0x01)
        self.assertEqual(self.memory.read_byte(0x1001), 0x02)
        self.assertEqual(self.memory.read_byte(0x1002), 0x03)

    def test_write(self):
        self.memory.write_byte(0x1000, 0x11)
        self.memory.write_byte(0x1001, 0x12)
        self.memory.write_byte(0x1002, 0x13)
        self.assertEqual(self.memory.read_byte(0x1000), 0x11)
        self.assertEqual(self.memory.read_byte(0x1001), 0x12)
        self.assertEqual(self.memory.read_byte(0x1002), 0x13)


# The two load_image tests below are plain pytest functions, next to the older
# unittest class above; pytest runs both styles in one file. The class moves
# over when we redo the pytest conversion (TODO.md).


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
