"""Read sectors from an Apple II disk image in DOS 3.3 order (a `.do` file).

A `.do` file holds the 35 tracks of a 5.25" floppy, 16 sectors per track,
256 bytes per sector: 143,360 bytes, with no header. Sectors are stored in
DOS 3.3 logical order, the same numbering a program puts into the IOB when
it calls RWTS. So sector S of track T starts at byte offset

    (T * 16 + S) * 256

Checked 2026-09-26 against XekriRedmane's track files for Lode Runner: all
224 sectors of the 14 tracks they cover are identical to these slices.

This module stands in for the disk only, not for the drive: no nibbles, no
disk controller, no timing. Whoever intercepts a program's disk access (for
Lode Runner, a checkpoint in `scripts/boot_lode_runner.py`) asks it for
sectors. Reading only, for now.
"""

from pathlib import Path

TRACKS = 35
SECTORS_PER_TRACK = 16
SECTOR_SIZE = 256
IMAGE_SIZE = TRACKS * SECTORS_PER_TRACK * SECTOR_SIZE  # 143,360 bytes


class DiskImage:
    """A `.do` disk image, read into memory as a whole."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data = self.path.read_bytes()
        # a wrong size means a different format (e.g. a nibble image) or a
        # damaged download; either way the offsets would be meaningless
        if len(self.data) != IMAGE_SIZE:
            raise ValueError(
                f"{self.path} has {len(self.data)} bytes, "
                f"expected {IMAGE_SIZE} for a DOS-order disk image"
            )

    def read_sector(self, track: int, sector: int) -> bytes:
        """Return the 256 bytes of one sector."""
        if not 0 <= track < TRACKS:
            raise ValueError(f"Track must be 0 to {TRACKS - 1}, got {track}")
        if not 0 <= sector < SECTORS_PER_TRACK:
            raise ValueError(
                f"Sector must be 0 to {SECTORS_PER_TRACK - 1}, got {sector}"
            )
        offset = (track * SECTORS_PER_TRACK + sector) * SECTOR_SIZE
        return self.data[offset : offset + SECTOR_SIZE]
