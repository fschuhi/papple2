"""Boot Lode Runner in papple2.

Loads Xekri's golden_source.bin -- the `LODE RUNNER` B file from the disk,
33024 bytes -- at $0800 and starts there, which is what DOS's BRUN does.
The file begins with JMP $2800, the relocation routine; it moves the game
into place ($0000-$1FFF and $5F00-$BFFF) and starts it.

Run from the repo root, like `make run` (papple2.toml's data_dir is read
relative to the current working directory):

    python boot_lode_runner.py path/to/golden_source.bin
    python boot_lode_runner.py path/to/golden_source.bin --headless

Default: opens the pygame window and runs until you close it or Ctrl-X.
Not tried by me -- my sandbox has no display.

--headless: the run from our session. Runs N instructions without a window,
watching every instruction through a papple2 checkpoint: counts executions
per address, notes the first jump into ROM ($D000 and up), keeps the last
40 instructions with registers, and renders both hi-res pages to PNG files
with a simple monochrome renderer (no NTSC color).

Needs the stack wrap and decimal mode fixes in cpu.py (2026-09-23 patch).
"""

import argparse
import collections
import time
from pathlib import Path

from papple2.core.emulator import Emulator, after_instructions
from papple2.util import load_data_dir

LOAD_ADDRESS = 0x0800


def boot(binary: str, headless: bool) -> Emulator:
    emulator = Emulator(no_display=headless, data_dir=load_data_dir())
    emulator.load_image(LOAD_ADDRESS, binary)
    emulator.cpu.PC = LOAD_ADDRESS
    return emulator


def hires_row_address(page_base: int, y: int) -> int:
    # the three-level interleave of the 192 hi-res rows
    return page_base + (y % 8) * 0x400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28


def save_hires_png(emulator: Emulator, page_base: int, filename: str) -> None:
    import pygame

    surface = pygame.Surface((560, 384))
    for y in range(192):
        row = hires_row_address(page_base, y)
        for column in range(40):
            byte = emulator.mem[row + column]
            # bit 7 selects the palette, bits 0-6 are pixels, bit 0 leftmost
            colour = (255, 160, 40) if byte & 0x80 else (60, 200, 255)
            for bit in range(7):
                if byte >> bit & 1:
                    x = column * 7 + bit
                    surface.fill(colour, (x * 2, y * 2, 2, 2))
    # the folder may not exist yet, e.g. on a fresh clone or after `make clean`
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, filename)
    print("saved", filename)


def run_headless(emulator: Emulator, instructions: int) -> None:
    executions = collections.Counter()
    first_rom_entry = []
    last = collections.deque(maxlen=40)

    def watch(em: Emulator) -> tuple[bool, bool]:
        cpu = em.cpu
        executions[cpu.PC] += 1
        if cpu.PC >= 0xD000 and not first_rom_entry:
            first_rom_entry.append((cpu.PC, em.instructions))
        last.append((em.instructions, cpu.PC, cpu.A, cpu.X, cpu.Y, cpu.SP))
        return True, True  # stay active, keep executing

    emulator.checkpoints.append((True, watch))

    start = time.time()
    try:
        emulator.run(until=after_instructions(instructions))
    except AssertionError:
        print("CPU stopped with an assertion -- last instructions:")
        for count, pc, a, x, y, sp in last:
            print(f"  {count:>9}  PC=${pc:04X} A=${a:02X} X=${x:02X} Y=${y:02X} SP=${sp:02X}")
    seconds = time.time() - start

    print(f"{emulator.instructions} instructions in {seconds:.1f} s")
    print(f"PC at the end: ${emulator.cpu.PC:04X}")
    print(f"distinct addresses executed: {len(executions)}")
    print("hot spots:", ", ".join(f"${a:04X}x{n}" for a, n in executions.most_common(10)))
    if first_rom_entry:
        pc, count = first_rom_entry[0]
        print(f"first jump into ROM: ${pc:04X} after {count} instructions")
    else:
        print("never jumped into ROM")

    save_hires_png(emulator, 0x2000, "tmp/lode_runner_page1.png")
    save_hires_png(emulator, 0x4000, "tmp/lode_runner_page2.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to golden_source.bin")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--instructions", type=int, default=4_000_000,
                        help="headless only (default: 4000000)")
    args = parser.parse_args()

    emulator = boot(args.binary, args.headless)
    if args.headless:
        run_headless(emulator, args.instructions)
    else:
        emulator.run()


if __name__ == "__main__":
    main()
