#!/usr/bin/env python3

# Papple is based on ApplePy, see LICENSE

# ApplePy - an Apple ][ emulator in Python
# James Tauber / http://jtauber.com/
# originally written 2001, updated 2011

# https://stackoverflow.com/questions/51464455/why-when-import-pygame-it-prints-the-version-and-welcome-message-how-delete-it
import contextlib
with contextlib.redirect_stdout(None):
    import pygame

import time
from pathlib import Path

import numpy
from papple2.core.cpu import CPU
from papple2.core.memory import Memory

# Toggle this to False to restore the original "scanline" look with black gaps
# So far, affects text output only.
SOLID_PIXELS = True

# The Apple II's ROM fills memory from here to $FFFF.
ROM_ADDRESS = 0xD000


def rom_path(data_dir: str | None) -> Path:
    """Where Apple2 reads the ROM from: A2ROM.BIN in the bin/ folder of
    data_dir, or of data/ without one. The tests replace this function with
    one that gives a ROM of zeros (tests/conftest.py), so they need no
    A2ROM.BIN."""
    return Path(data_dir if data_dir is not None else "data") / "bin" / "A2ROM.BIN"

class Display:

    characters = [
        [0b00000, 0b01110, 0b10001, 0b10101, 0b10111, 0b10110, 0b10000, 0b01111],
        [0b00000, 0b00100, 0b01010, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
        [0b00000, 0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
        [0b00000, 0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
        [0b00000, 0b01111, 0b10000, 0b10000, 0b10000, 0b10011, 0b10001, 0b01111],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
        [0b00000, 0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        [0b00000, 0b00001, 0b00001, 0b00001, 0b00001, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
        [0b00000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
        [0b00000, 0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
        [0b00000, 0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b11000, 0b11000, 0b11000, 0b11000, 0b11000, 0b11111],
        [0b00000, 0b00000, 0b10000, 0b01000, 0b00100, 0b00010, 0b00001, 0b00000],
        [0b00000, 0b11111, 0b00011, 0b00011, 0b00011, 0b00011, 0b00011, 0b11111],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b01010, 0b10001, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b11111],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
        [0b00000, 0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010],
        [0b00000, 0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
        [0b00000, 0b11000, 0b11001, 0b00010, 0b00100, 0b01000, 0b10011, 0b00011],
        [0b00000, 0b01000, 0b10100, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101],
        [0b00000, 0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00100, 0b01000, 0b10000, 0b10000, 0b10000, 0b01000, 0b00100],
        [0b00000, 0b00100, 0b00010, 0b00001, 0b00001, 0b00001, 0b00010, 0b00100],
        [0b00000, 0b00100, 0b10101, 0b01110, 0b00100, 0b01110, 0b10101, 0b00100],
        [0b00000, 0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b00100, 0b01000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100],
        [0b00000, 0b00000, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b00000],
        [0b00000, 0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
        [0b00000, 0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        [0b00000, 0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00110, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
        [0b00000, 0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b00111, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b11100],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b00000, 0b00100, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b00000, 0b00100, 0b00100, 0b01000],
        [0b00000, 0b00010, 0b00100, 0b01000, 0b10000, 0b01000, 0b00100, 0b00010],
        [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000],
        [0b00000, 0b01000, 0b00100, 0b00010, 0b00001, 0b00010, 0b00100, 0b01000],
        [0b00000, 0b01110, 0b10001, 0b00010, 0b00100, 0b00100, 0b00000, 0b00100]
    ]

    lores_colours = [
        (0, 0, 0),  # black
        (208, 0, 48),  # magenta / dark red
        (0, 0, 128),  # dark blue
        (255, 0, 255),  # purple / violet
        (0, 128, 0),  # dark green
        (128, 128, 128),  # gray 1
        (0, 0, 255),  # medium blue / blue
        (96, 160, 255),  # light blue
        (128, 80, 0),  # brown / dark orange
        (255, 128, 0),  # orange
        (192, 192, 192),  # gray 2
        (255, 144, 128),  # pink / light red
        (0, 255, 0),  # light green / green
        (255, 255, 0),  # yellow / light orange
        (64, 255, 144),  # aquamarine / light green
        (255, 255, 255),  # white
    ]

    def __init__( self, apple2: "Apple2", no_display: bool ) -> None:
        self.apple2 = apple2
        self.no_display = no_display

        # https://www.pygame.org/wiki/SettingWindowPosition
        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (800, 400)

        self.mix = False
        self.flash_time = time.time()
        self.flash_on = False
        self.flash_chars = [[0] * 0x400 for _ in range(2)]

        self.page = 1
        self.text = False
        self.colour = False
        self.high_res = True

        if no_display:
            return

        apple_width = 280 * 2
        apple_height = 192 * 2
        if False:
            mem_width = 256 * 2 # bytes per page, each byte is a single pixel
            mem_height = 208 * 2 # pages 0000-CFFF, each page is a single pixel line
        else:
            mem_width = 0
            mem_height = 0
        status_bar_height = 20
        self.screen = pygame.display.set_mode((apple_width + mem_width, max(apple_height, mem_height) + status_bar_height))

        pygame.font.init()
        self.status_font = pygame.font.SysFont("Lucida Console", 12)
        self.clear_status()

        self.init_chars()

        pygame.display.set_caption("Apple ][")

        # TODO: turn on text
        if False:
            self.init_chars()

    def clear_status(self, flip: bool = True) -> None:
        if self.no_display:
            return

        r = pygame.Rect(0,384,560,384+20)
        self.screen.fill((50,50,50), r)
        if flip:
            pygame.display.flip()

    def show_status(self, text: str, flip: bool = True) -> None:
        if self.no_display:
            return

        self.clear_status()
        surface = self.status_font.render(text, True, (255,255,255))
        self.screen.blit(surface, (0,384))
        if flip:
            pygame.display.flip()

    def init_chars(self) -> None:
        self.chargen = []
        for c in self.characters:
            chars = [[pygame.Surface((14, 16)), pygame.Surface((14, 16))],
                     [pygame.Surface((14, 16)), pygame.Surface((14, 16))]]
            for colour in (0, 1):
                hue = (255, 255, 255) if colour else (0, 200, 0)
                for inv in (0, 1):
                    pixels = pygame.PixelArray(chars[colour][inv])
                    off = hue if inv else (0, 0, 0)
                    on = (0, 0, 0) if inv else hue
                    for row in range(8):
                        b = c[row] << 1
                        for col in range(7):
                            bit = (b >> (6 - col)) & 1
                            pixels[2 * col][2 * row] = on if bit else off
                            pixels[2 * col + 1][2 * row] = on if bit else off
                            if SOLID_PIXELS:
                                pixels[2 * col][2 * row + 1] = on if bit else off
                                pixels[2 * col + 1][2 * row + 1] = on if bit else off
                    del pixels
            self.chargen.append(chars)


    def txtclr(self) -> None:
        self.text = False

    def txtset(self) -> None:
        self.text = True
        self.colour = False

    def mixclr(self) -> None:
        self.mix = False

    def mixset(self) -> None:
        self.mix = True
        self.colour = True

    def lowscr(self) -> None:
        self.page = 1

    def hiscr(self) -> None:
        self.page = 2

    def lores(self) -> None:
        self.high_res = False

    def hires(self) -> None:
        self.high_res = True

    def update(self, address: int, value: int) -> None:

        def update_text() -> None:
            base = address - start_text
            self.flash_chars[self.page - 1][base] = value
            hi, lo = divmod(base, 0x80)
            row_group, column = divmod(lo, 0x28)
            row = hi + 8 * row_group

            if row_group == 3:
                return

            if self.text or (self.mix and row >= 20):
                mode, ch = divmod(value, 0x40)

                if mode == 0:
                    inv = True
                elif mode == 1:
                    inv = self.flash_on
                else:
                    inv = False

                self.screen.blit(self.chargen[ch][self.colour][inv], (2 * (column * 7), 2 * (row * 8)))
            else:
                pixels = pygame.PixelArray(self.screen)
                if not self.high_res:
                    lower, upper = divmod(value, 0x10)

                    for dx in range(14):
                        for dy in range(8):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            pixels[x][y] = self.lores_colours[upper]
                        for dy in range(8, 16):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            pixels[x][y] = self.lores_colours[lower]
                del pixels

        def update_hires() -> None:
            # Map the linear address to Apple II's interleaved screen memory coordinates
            base = address - start_hires
            row8, b = divmod(base, 0x400)
            hi, lo = divmod(b, 0x80)
            row_group, column = divmod(lo, 0x28)
            row = 8 * (hi + 8 * row_group) + row8

            # Skip drawing if we are in mixed mode and in the text area at the bottom
            if self.mix and row >= 160:
                return

            # Sanity check to avoid drawing out of bounds
            if row >= 192 or column >= 40:
                return

            # Lock the pygame surface once to allow fast pixel manipulation
            pixels = pygame.PixelArray(self.screen)

            def render_byte(render_addr, col):
                # Fetch the byte. Apple II hi-res uses the lowest 7 bits for pixels.
                # Bit 7 (MSB) shifts the color palette (Orange/Blue vs Green/Violet).
                val = self.apple2.memory._mem[render_addr]
                msb = val // 0x80
                bits = [(val >> i) & 1 for i in range(7)]

                # To simulate NTSC artifacting (where colors smear horizontally),
                # we need to know the state of the pixels immediately to the left.
                # Since pixels cross byte boundaries, we peek at the previous byte.
                prev_bit = 0
                prev_prev_bit = 0
                if col > 0:
                    prev_val = self.apple2.memory._mem[render_addr - 1]
                    prev_bit = (prev_val >> 6) & 1
                    prev_prev_bit = (prev_val >> 5) & 1

                # We also need to know if a pixel is immediately followed by another 'on' pixel.
                next_bit = 0
                if col < 39:
                    next_bit = self.apple2.memory._mem[render_addr + 1] & 1

                # Loop through the 7 printable bits in the byte
                for i in range(7):
                    xx = col * 7 + i  # Absolute horizontal pixel index (0 to 279)
                    x = 2 * xx  # Scaled x coordinate for the 2x2 display
                    y = 2 * row  # Scaled y coordinate

                    c = bits[i]
                    # Determine immediate neighbors, crossing byte boundaries if necessary
                    left_c = bits[i - 1] if i > 0 else prev_bit
                    right_c = bits[i + 1] if i < 6 else next_bit

                    # Determine the pixel two spots to the left (needed to detect lone pixels vs white blocks)
                    if i > 1:
                        left_left_c = bits[i - 2]
                    elif i == 1:
                        left_left_c = prev_bit
                    else:
                        left_left_c = prev_prev_bit

                    color = (0, 0, 0)

                    if c:
                        # In NTSC artifacting, any two adjacent '1' bits bleed together to form solid white.
                        if left_c or right_c:
                            color = (255, 255, 255)
                        else:
                            # A lone '1' bit gets a color depending on its x-coordinate (even or odd)
                            # and the MSB palette shift of its parent byte.
                            if msb:
                                # First line for `color =` are old colors, the new ones look nicer but might not be legit.
                                #color = (255, 192, 0) if xx % 2 else (0, 192, 255)
                                color = (255, 128, 0) if xx % 2 else (0, 165, 255)
                            else:
                                #color = (0, 255, 0) if xx % 2 else (255, 0, 255)
                                color = (0, 230, 0) if xx % 2 else (255, 0, 255)
                    else:
                        # If the current bit is '0', it is usually black.
                        # However, NTSC signals take time to drop. If the pixel to the left was a lone colored pixel,
                        # its color smears into this empty space.
                        # We specifically check `not left_left_c` to ensure we don't smear color out of a solid white block.
                        if left_c and not left_left_c:
                            left_msb = msb
                            # If we are at bit 0, the smeared color comes from the MSB of the previous byte
                            if i == 0 and col > 0:
                                left_msb = self.apple2.memory._mem[render_addr - 1] // 0x80

                            # Apply the same color logic based on the left pixel's coordinate
                            if left_msb:
                                #color = (255, 192, 0) if (xx - 1) % 2 else (0, 192, 255)
                                color = (255, 128, 0) if (xx - 1) % 2 else (0, 165, 255)
                            else:
                                #color = (0, 255, 0) if (xx - 1) % 2 else (255, 0, 255)
                                color = (0, 230, 0) if (xx - 1) % 2 else (255, 0, 255)

                    # Draw the top row of the 2x2 scaled block with our resolved color
                    pixels[x][y] = color
                    pixels[x + 1][y] = color

                    # Force the bottom row of the 2x2 block to black.
                    # This creates the distinctive horizontal CRT scanline effect.
                    pixels[x][y + 1] = (0, 0, 0)
                    pixels[x + 1][y + 1] = (0, 0, 0)

            # Because a single byte write can change how its neighbors are rendered
            # (due to the left/right smear artifacting crossing byte boundaries),
            # we must always render the target byte AND its immediate left/right neighbors.
            render_byte(address, column)
            if column > 0:
                render_byte(address - 1, column - 1)
            if column < 39:
                render_byte(address + 1, column + 1)

            del pixels  # Release the surface lock so pygame can update the screen

        if self.page == 1:
            start_text = 0x400
            start_hires = 0x2000
        elif self.page == 2:
            start_text = 0x800
            start_hires = 0x4000
        else:
            assert False

        if self.no_display:
            return

        if start_text <= address <= start_text + 0x3FF:
            update_text()

        if start_hires <= address <= start_hires + 0x1FFF and self.high_res:
            update_hires()


    def refresh_hires(self) -> None:
        if self.no_display:
            return

        start_hires = 0x2000 if self.page == 1 else 0x4000
        for address in range(start_hires, start_hires + 0x2000):
            value = self.apple2.memory._mem[address]
            self.update(address,value)
        pygame.display.flip()


    def flash(self) -> None:
        if self.no_display:
            return

        if time.time() - self.flash_time >= 0.5:
            self.flash_on = not self.flash_on
            for offset, char in enumerate(self.flash_chars[self.page - 1]):
                if (char & 0xC0) == 0x40:
                    self.update(0x400 + offset, char)
            self.flash_time = time.time()


    def save_hires_image(self, fn: str) -> None:
        self.refresh_hires()
        import re
        if not re.search(r'\.(png|jpg) *$', fn.lower()):
            fn = fn.strip() + '.png'
        print(fn)
        pygame.image.save(self.screen, fn)

    def clear_hires(self) -> None:
        start_hires = 0x2000 if self.page == 1 else 0x4000
        end_hires = start_hires + 0x2000
        self.apple2.memory._mem[start_hires:end_hires] = 0x2000 * [0x00]


class Speaker:

    CPU_CYCLES_PER_SAMPLE = 60
    CHECK_INTERVAL = 1000

    def __init__(self, quiet: bool) -> None:
        self.quiet = quiet
        self.last_toggle = None
        self.buffer = []
        self.polarity = False
        self.reset()

    def toggle(self, cycle: int) -> None:
        if not self.quiet:
            if self.last_toggle is not None:
                l = (cycle - self.last_toggle) / Speaker.CPU_CYCLES_PER_SAMPLE
                # https://youtu.be/EhK5JNx0irA?t=1329
                # ACHTUNG: missing speaker toggle, keine Ahnung was er da mit buffer.extend() macht
                # self.buffer.extend([0, 26000] if self.polarity else [0, -2600])
                # self.buffer.extend((l - 2) * [16384] if self.polarity else [-16384])
                self.polarity = not self.polarity
            self.last_toggle = cycle

    def reset(self) -> None:
        self.last_toggle = None
        self.buffer = []
        self.polarity = False

    def play(self) -> None:
        if not self.quiet:
            sample_array = numpy.int16(self.buffer)
            sound = pygame.sndarray.make_sound(sample_array)
            sound.play()
            self.reset()

    def update(self, cycle: int) -> None:
        if self.buffer and (cycle - self.last_toggle) > self.CHECK_INTERVAL:
            self.play()


class SoftSwitches:

    def __init__(self, display: Display, speaker: Speaker) -> None:
        self.kbd = 0x00
        self.display = display
        self.speaker = speaker

    def read_byte(self, address: int) -> int:
        assert 0xC000 <= address <= 0xCFFF
        if address == 0xC000:
            return self.kbd
        elif address == 0xC010:
            # "clearing the keyboard strobe"
            self.kbd &= 0x7F
        elif address == 0xC030:
            # TODO: speaker cycle missing 05.03.19
            cycle = 0
            self.speaker.toggle(cycle)
        elif address == 0xC050:
            self.display.txtclr()
        elif address == 0xC051:
            self.display.txtset()
        elif address == 0xC052:
            self.display.mixclr()
        elif address == 0xC053:
            self.display.mixset()
        elif address == 0xC054:
            self.display.lowscr()
        elif address == 0xC055:
            self.display.hiscr()
        elif address == 0xC056:
            self.display.lores()
        elif address == 0xC057:
            self.display.hires()
        elif address == 0xC060:
            # no cassette support anymore
            pass
        else:
            pass  # print "%04X" % address
        return 0x00

    def write_byte(self, address: int, value: int) -> None:
        # disregard value - - softswitches is ROM
        self.read_byte(address)


class Apple2:

    def __init__(self, no_display: bool = False, quiet: bool = True, data_dir: str | None = None) -> None:
        if not no_display:
            if not quiet:
                pygame.mixer.pre_init(11025, -16, 1)
            pygame.init()

        self.display = Display(self, no_display)
        self.speaker = Speaker(quiet)
        self.softswitches = SoftSwitches(self.display, self.speaker)

        self.memory = Memory(self)
        self.memory.load_image(ROM_ADDRESS, str(rom_path(data_dir)))
        self.cpu = CPU(self.memory, program_counter=None)
