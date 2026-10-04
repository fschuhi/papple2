"""Boot Lode Runner in papple2.

How the game is loaded and started, including the RWTS hook that serves
its disk reads, is Lode Runner's setup in papple2.programs.lode_runner.
This script runs it, in a window or headless.

Run from the repo root, like `make run` (papple2.toml's data_dir is read
relative to the current working directory):

    python boot_lode_runner.py path/to/golden_source.bin
    python boot_lode_runner.py path/to/golden_source.bin --headless
    python boot_lode_runner.py path/to/golden_source.bin --speed 1.0
    python boot_lode_runner.py path/to/golden_source.bin --instructions 4000000

Default: opens the pygame window and runs until you close it or Ctrl-X,
as fast as the emulator can. --speed 1.0 throttles the window to the speed
of a real Apple II (`make boot-lode-runner-throttled`). With --instructions N
the window stops after N instructions, as if Ctrl-X had been pressed; the
next Ctrl-X continues.
Not tried by me -- my sandbox has no display.

--headless: the run from our session. Runs N instructions without a window
and renders both hi-res pages to PNG files with a simple monochrome
renderer (no NTSC color).

Both modes install the RWTS hook; at the end of a run the script prints
every read it served.
"""

import argparse
import time
from pathlib import Path

from papple2.core.emulator import Emulator
from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.programs.lode_runner import boot, describe


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
    start = time.time()
    emulator.run(until=instruction_count_reaches(instructions))
    seconds = time.time() - start

    print(f"{emulator.instructions} instructions in {seconds:.2f} s")
    print(f"PC at the end: ${emulator.cpu.PC:04X}")

    save_hires_png(emulator, 0x2000, "tmp/lode_runner_page1.png")
    save_hires_png(emulator, 0x4000, "tmp/lode_runner_page2.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", help="path to golden_source.bin")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--instructions", type=int, default=None,
                        help="headless: stop after N (default: 4000000); "
                             "window: stop after N, Ctrl-X continues (default: no stop)")
    parser.add_argument("--speed", type=float, default=None,
                        help="window only: 1.0 = a real Apple II (default: unthrottled)")
    args = parser.parse_args()

    emulator, rwts = boot(args.binary, args.headless, args.speed)
    if args.headless:
        run_headless(emulator, args.instructions if args.instructions is not None else 4_000_000)
    elif args.instructions is not None:
        emulator.run(until=instruction_count_reaches(args.instructions))
    else:
        emulator.run()

    print(f"RWTS reads served: {len(rwts.log)}")
    for entry in rwts.log:
        print("  " + describe(*entry))


if __name__ == "__main__":
    main()
