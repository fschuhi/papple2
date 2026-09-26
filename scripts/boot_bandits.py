"""Boot Bandits (the Total Replay version) in papple2.

Total Replay (4am and qkumba) ships Bandits as ProDOS files: the main
program BANDITS, which loads at $0800, and twelve data files BANDITS.A to
BANDITS.Z. The main program asks ProDOS for everything it needs through a
single entry point, the MLI ("Machine Language Interface") at $BF00. Each
call looks like this:

    JSR $BF00
    .byte command          ; which service, e.g. $C8 = OPEN
    .word parameter_block  ; address of a small table: what exactly to do

ProDOS returns to the byte after these three, so the caller's code goes on
behind them.

papple2 has no ProDOS, so nothing answers at $BF00. A checkpoint there, the
MLI hook, stands in for it, one command at a time:

- GET_PREFIX: writes the prefix /BANDITS/ into the caller's buffer. With a
  non-empty prefix the game skips ON_LINE (see $0812 in BANDITS).
- OPEN, READ, CLOSE: serve the files in data_dir/tr/bandits/.
- anything else: prints the request and stops the emulator.

Run from the repo root:

    python scripts/boot_bandits.py
    python scripts/boot_bandits.py --headless

With the window, the emulator stays stopped at $BF00 after the hook stops
it (Ctrl-X only stops it again); close the window to end the run.

MemoryMap asserts that an instruction never starts on a byte it saw earlier
as part of another instruction. Code loaded over code breaks that rule, and
Bandits does exactly that early on. The script catches the assertion and
prints which instruction tripped it and which earlier instruction owned the
byte, to find out where it happens.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from papple2.core.emulator import Emulator
from papple2.util import load_data_dir

LOAD_ADDRESS = 0x0800

# the files extracted from Total Replay with CiderPress II, below data_dir
BANDITS_DIR = Path("tr") / "bandits"
MAIN_PROGRAM = "BANDITS"

MLI_ENTRY = 0xBF00

# The commands found in BANDITS so far (2026-09-26); names from the ProDOS 8
# Technical Reference Manual. GET_PREFIX and OPEN confirmed by running.
MLI_COMMANDS = {
    0xC5: "ON_LINE",
    0xC7: "GET_PREFIX",
    0xC8: "OPEN",
    0xCA: "READ",
    0xCC: "CLOSE",
}
MLI_GET_PREFIX = 0xC7
MLI_OPEN = 0xC8
MLI_READ = 0xCA
MLI_CLOSE = 0xCC

# the answer to GET_PREFIX; the game opens its files by short names like
# BANDITS.A, so the text itself does not matter, only that it is not empty
PREFIX = "/BANDITS/"

# The reference number OPEN hands out: ProDOS's "handle" for an open file,
# used by READ and CLOSE. Bandits' READ block already holds 1 before any
# OPEN, so the game counts on getting 1; we only ever have one file open.
REFERENCE_NUMBER = 1

# how many bytes of a parameter block to print; the first byte is the number
# of parameters, the rest depends on the command
PARAMETER_BYTES_SHOWN = 8


def read_word(mem: list[int], address: int) -> int:
    # the 6502 stores addresses low byte first
    return mem[address] | mem[address + 1] << 8


def write_word(mem: list[int], address: int, value: int) -> None:
    mem[address] = value & 0xFF
    mem[address + 1] = value >> 8


def read_pathname(mem: list[int], address: int) -> str:
    # ProDOS pathnames start with a length byte, then the characters
    length = mem[address]
    return "".join(chr(mem[address + 1 + i] & 0x7F) for i in range(length))


@dataclass
class OpenFile:
    name: str
    data: bytes
    position: int = 0  # where the next READ starts


class MliHook:
    """Stand in for ProDOS at $BF00: serve the commands we know, stop at the rest.

    Like RwtsHook in boot_lode_runner.py, answers go into memory past the
    CPU's write hook, and the return to the caller is faked by moving SP and
    PC outside the instruction stream. Unlike RWTS, the return goes three
    bytes further than a plain RTS: behind the command byte and the
    parameter block address. `log` records every call seen, served or not,
    for printing after the run.

    Each served command has a method that returns a short description of
    what it did, or None if it cannot serve this request; then the hook
    prints the request and stops, as for an unknown command.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.open_files: dict[int, OpenFile] = {}
        # (instructions, JSR address, command, parameter block address)
        self.log: list[tuple[int, int, int, int]] = []
        self.commands: dict[int, Callable[[Emulator, int], str | None]] = {
            MLI_GET_PREFIX: self.get_prefix,
            MLI_OPEN: self.open,
            MLI_READ: self.read,
            MLI_CLOSE: self.close,
        }

    def checkpoint(self, em: Emulator) -> tuple[bool, bool]:
        cpu = em.cpu
        if cpu.PC != MLI_ENTRY:
            return True, True  # stay active, keep executing
        mem = em.mem

        # JSR pushed the address of its own last byte; one more is the first
        # of the three bytes behind the JSR. Peek for now: only a served
        # command takes the address off the stack.
        low = mem[0x100 + (cpu.SP + 1 & 0xFF)]
        high = mem[0x100 + (cpu.SP + 2 & 0xFF)]
        inline = (high << 8 | low) + 1
        jsr_address = inline - 3

        command = mem[inline]
        parameters = read_word(mem, inline + 1)
        self.log.append((em.instructions, jsr_address, command, parameters))

        serve = self.commands.get(command)
        served = serve(em, parameters) if serve is not None else None
        if served is not None:
            print(describe(em.instructions, jsr_address, command, parameters)
                  + " -- served: " + served)
            self.return_to_caller(em, inline)
            return True, True  # continue in the caller

        print(describe(em.instructions, jsr_address, command, parameters))
        block = mem[parameters : parameters + PARAMETER_BYTES_SHOWN]
        print("  parameter block: " + " ".join(f"{b:02X}" for b in block))
        if command == MLI_OPEN:
            pathname_address = read_word(mem, parameters + 1)
            name = read_pathname(mem, pathname_address)
            print(f"  pathname at ${pathname_address:04X}: {name!r}")
        return True, False  # breakpoint: stop here, not served

    def get_prefix(self, em: Emulator, parameters: int) -> str | None:
        # parameter block: count, buffer address
        mem = em.mem
        buffer = read_word(mem, parameters + 1)
        mem[buffer] = len(PREFIX)
        mem[buffer + 1 : buffer + 1 + len(PREFIX)] = [ord(c) for c in PREFIX]
        return f"{PREFIX!r} at ${buffer:04X}"

    def open(self, em: Emulator, parameters: int) -> str | None:
        # parameter block: count, pathname address, I/O buffer address (ProDOS's
        # own working space, ignored here), reference number (the answer)
        mem = em.mem
        pathname = read_pathname(mem, read_word(mem, parameters + 1))
        # a full pathname would start with the prefix; we only need the name
        name = pathname.rsplit("/", 1)[-1]
        path = self.directory / name
        if not path.is_file():
            print(f"  OPEN: no file {path}")
            return None
        if self.open_files:
            print("  OPEN: a file is still open; only one at a time is served")
            return None
        data = path.read_bytes()
        self.open_files[REFERENCE_NUMBER] = OpenFile(name, data)
        mem[parameters + 5] = REFERENCE_NUMBER
        return f"{name}, {len(data)} bytes, reference number {REFERENCE_NUMBER}"

    def read(self, em: Emulator, parameters: int) -> str | None:
        # parameter block: count, reference number, buffer address, request
        # count, transfer count (the answer: how many bytes were read)
        mem = em.mem
        reference = mem[parameters + 1]
        file = self.open_files.get(reference)
        if file is None:
            print(f"  READ: no open file with reference number {reference}")
            return None
        buffer = read_word(mem, parameters + 2)
        request = read_word(mem, parameters + 4)
        chunk = file.data[file.position : file.position + request]
        if not chunk:
            # ProDOS would report an error here; not served until we know
            # what the game expects
            print(f"  READ: nothing left in {file.name}")
            return None
        # through Memory.write_byte, so the window redraws what lands on a
        # hi-res page; still past the CPU's write hook
        memory = em.apple2.memory
        for offset, value in enumerate(chunk):
            memory.write_byte(buffer + offset, value)
        file.position += len(chunk)
        # fewer bytes than requested is fine: the rest of the file (general
        # knowledge of ProDOS, unconfirmed); Bandits always asks for $FFFF
        write_word(mem, parameters + 6, len(chunk))
        last = buffer + len(chunk) - 1
        return f"{len(chunk)} bytes of {file.name} at ${buffer:04X}-${last:04X}"

    def close(self, em: Emulator, parameters: int) -> str | None:
        # parameter block: count, reference number; 0 means all open files
        reference = em.mem[parameters + 1]
        if reference == 0:
            names = ", ".join(file.name for file in self.open_files.values())
            self.open_files.clear()
            return f"all files ({names or 'none open'})"
        file = self.open_files.pop(reference, None)
        if file is None:
            print(f"  CLOSE: no open file with reference number {reference}")
            return None
        return file.name

    @staticmethod
    def return_to_caller(em: Emulator, inline: int) -> None:
        cpu = em.cpu
        # success as ProDOS reports it: error code 0 in A, carry clear, and
        # (from general knowledge, unconfirmed) the zero flag set
        cpu.A = 0
        cpu.carry_flag = 0
        cpu.zero_flag = 1
        # take the JSR's return address off the stack, as CPU.RTS() would,
        # then skip the command byte and the parameter block address
        cpu.pull_word()
        cpu.PC = inline + 3


def describe(instructions: int, jsr_address: int, command: int, parameters: int) -> str:
    name = MLI_COMMANDS.get(command, "unknown")
    return (
        f"after {instructions} instructions: MLI {name} (${command:02X}) "
        f"called from ${jsr_address:04X}, parameters at ${parameters:04X}"
    )


def report_memory_map_assertion(em: Emulator) -> None:
    # Emulator.post_op() runs after the instruction, so last_PC is the
    # instruction MemoryMap refused, and it has already executed
    address = em.cpu.last_PC
    print(
        f"MemoryMap assertion after {em.instructions} instructions "
        f"(cycle {em.cpu.cycles}): instruction at ${address:04X}, "
        f"opcode ${em.mem[address]:02X}, PC now ${em.cpu.PC:04X}"
    )
    # which earlier instruction had this byte as its first or second operand
    for distance in (1, 2):
        owner = address - distance
        info = em.map.get_info(owner)
        if (
            em.map.is_op(owner)
            and info is not None
            and info.operand_length is not None
            and info.operand_length >= distance
        ):
            print(
                f"  ${address:04X} was operand byte {distance} of the instruction "
                f"at ${owner:04X}: opcode then ${info.opcode:02X}, byte there "
                f"now ${em.mem[owner]:02X}, last executed at cycle {info.last_cycles}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    data_dir = load_data_dir()
    directory = Path(data_dir) / BANDITS_DIR
    main_program = directory / MAIN_PROGRAM

    emulator = Emulator(no_display=args.headless, data_dir=data_dir)
    emulator.load_image(LOAD_ADDRESS, str(main_program))
    emulator.cpu.PC = LOAD_ADDRESS

    mli = MliHook(directory)
    emulator.add_checkpoint(mli.checkpoint)
    try:
        emulator.run()
    except AssertionError:
        report_memory_map_assertion(emulator)

    print(f"MLI calls seen: {len(mli.log)}")
    for entry in mli.log:
        print("  " + describe(*entry))


if __name__ == "__main__":
    main()
