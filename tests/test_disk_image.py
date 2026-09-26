from pathlib import Path

import pytest

from papple2.core.disk_image import (
    IMAGE_SIZE,
    SECTOR_SIZE,
    SECTORS_PER_TRACK,
    TRACKS,
    DiskImage,
)


# The tests build their own image in a temporary folder, so they need no
# copyrighted disk image and run on a fresh clone. Every sector is filled
# with its own address: the first byte is the track, all others the sector.
# A sector read from the wrong place then shows where it came from.


def fake_sector(track: int, sector: int) -> bytes:
    return bytes([track]) + bytes([sector]) * (SECTOR_SIZE - 1)


@pytest.fixture
def image_path(tmp_path: Path) -> Path:
    path = tmp_path / "fake.do"
    path.write_bytes(
        b"".join(
            fake_sector(track, sector)
            for track in range(TRACKS)
            for sector in range(SECTORS_PER_TRACK)
        )
    )
    return path


@pytest.mark.parametrize("track, sector", [(0, 0), (3, 0), (12, 15), (34, 15)])
def test_read_sector_returns_the_addressed_sector(
    image_path: Path, track: int, sector: int
) -> None:
    assert DiskImage(image_path).read_sector(track, sector) == fake_sector(track, sector)


@pytest.mark.parametrize("size", [0, IMAGE_SIZE - 1, IMAGE_SIZE + 1])
def test_wrong_file_size_is_refused(tmp_path: Path, size: int) -> None:
    path = tmp_path / "wrong.do"
    path.write_bytes(bytes(size))

    with pytest.raises(ValueError, match="expected 143360"):
        DiskImage(path)


@pytest.mark.parametrize("track", [-1, TRACKS])
def test_track_out_of_range_is_refused(image_path: Path, track: int) -> None:
    with pytest.raises(ValueError, match="Track"):
        DiskImage(image_path).read_sector(track, 0)


@pytest.mark.parametrize("sector", [-1, SECTORS_PER_TRACK])
def test_sector_out_of_range_is_refused(image_path: Path, sector: int) -> None:
    with pytest.raises(ValueError, match="Sector"):
        DiskImage(image_path).read_sector(0, sector)
