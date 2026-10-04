"""Lode Runner's setup: how papple2 loads and starts the game.

Loads Xekri's golden_source.bin -- the `LODE RUNNER` B file from the disk,
33024 bytes -- at $0800 and starts there, which is what DOS's BRUN does.
The file begins with JMP $2800, the relocation routine; it moves the game
into place ($0000-$1FFF and $5F00-$BFFF) and starts it.

RWTS hook: every disk access of the game ends in DISABLE_INTS_CALL_RWTS
at $B7B5 (main.nw, "disk routines"). A trap there serves reads from the
disk image in data_dir/do/: it copies the sector straight into the
buffer, clears carry, and returns to the caller as RTS would. Anything
else (the high-score write at game over, format) prints the request and
stops the emulator.

Used by scripts/boot_lode_runner.py (the window and the headless run)
and by the lr_* recipes.

Needs the stack wrap and decimal mode fixes in cpu.py (2026-09-23 patch).
"""

from pathlib import Path

from papple2.core.disk_image import SECTOR_SIZE, DiskImage
from papple2.core.emulator import Emulator
from papple2.util import load_data_dir

LOAD_ADDRESS = 0x0800

# Relative to the repo root, where make and IPython are started.
DEFAULT_BINARY = "data/bin/LODE_RUNNER.BIN"

# The game's disk, from the Internet Archive; see README.md, "Data files".
DISK_IMAGE = "Lode_Runner_1983_Broderbund_cr_Reset_Vector.do"

# DOS's RWTS entry as the game calls it: Y/A point to the IOB, carry clear
# on return means success. Offsets into the IOB from main.nw's defines.
DISABLE_INTS_CALL_RWTS = 0xB7B5
IOB_TRACK_NUMBER = 0x04
IOB_SECTOR_NUMBER = 0x05
IOB_READ_WRITE_BUFFER_PTR = 0x08
IOB_COMMAND_CODE = 0x0C
IOB_RETURN_CODE = 0x0D
RWTS_READ = 1
RWTS_COMMANDS = {0: "seek", 1: "read", 2: "write", 4: "format"}


class RwtsHook:
    """Serve the game's RWTS reads from a .do disk image.

    The sector appears in the buffer "deus ex machina": written straight
    into memory, past the CPU's write hook, so no write hook sees it. The
    fake RTS moves SP and PC outside the instruction stream. `log` records
    every read served, for looking into both later.
    """

    def __init__(self, disk: DiskImage) -> None:
        self.disk = disk
        # (instructions, command, track, sector, buffer, return address)
        self.log: list[tuple[int, int, int, int, int, int]] = []

    def serve(self, em: Emulator) -> bool:
        cpu = em.cpu
        mem = em.mem
        iob = cpu.A << 8 | cpu.Y
        command = mem[iob + IOB_COMMAND_CODE]
        track = mem[iob + IOB_TRACK_NUMBER]
        sector = mem[iob + IOB_SECTOR_NUMBER]
        buffer = mem[iob + IOB_READ_WRITE_BUFFER_PTR] | mem[iob + IOB_READ_WRITE_BUFFER_PTR + 1] << 8

        if command != RWTS_READ:
            # only JMPs lead here from the caller's JSR, so the top of the
            # stack is the caller's return address minus one; peek, don't pull
            low = mem[0x100 + (cpu.SP + 1 & 0xFF)]
            high = mem[0x100 + (cpu.SP + 2 & 0xFF)]
            caller = (high << 8 | low) + 1
            print("RWTS: stopping, only reads are served -- "
                  + describe(em.instructions, command, track, sector, buffer, caller))
            return False  # not served: the game freezes here

        mem[buffer : buffer + SECTOR_SIZE] = self.disk.read_sector(track, sector)
        mem[iob + IOB_RETURN_CODE] = 0
        cpu.carry_flag = 0
        # what CPU.RTS() does, including the stack wrap within page 1
        caller = cpu.pull_word() + 1
        cpu.PC = caller
        self.log.append((em.instructions, command, track, sector, buffer, caller))
        return True  # served: continue in the caller


def describe(instructions: int, command: int, track: int, sector: int, buffer: int, caller: int) -> str:
    name = RWTS_COMMANDS.get(command, "unknown")
    return (f"after {instructions} instructions: {name} ({command}) "
            f"track ${track:02X} sector ${sector:02X} buffer ${buffer:04X}, "
            f"returns to ${caller:04X}")


def boot(binary: str, headless: bool, speed: float | None = None) -> tuple[Emulator, RwtsHook]:
    data_dir = load_data_dir()
    emulator = Emulator(no_display=headless, data_dir=data_dir, speed=speed)
    emulator.load_image(LOAD_ADDRESS, binary)
    emulator.cpu.PC = LOAD_ADDRESS
    rwts = RwtsHook(DiskImage(Path(data_dir) / "do" / DISK_IMAGE))
    emulator.add_trap(DISABLE_INTS_CALL_RWTS, rwts.serve)
    return emulator, rwts
