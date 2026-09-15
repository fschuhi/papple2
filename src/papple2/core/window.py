import time
import pygame
from pysm import Event


def determine_states_from_kmods():
    mods = pygame.key.get_mods()
    if mods & pygame.KMOD_SHIFT:
        states = 200
    elif mods & pygame.KMOD_CTRL:
        states = 20
    elif mods & pygame.KMOD_ALT:
        states = 1
    else:
        states = 2000
    return states


class PygameWindow:

    def __init__(self, emulator):
        self.emulator = emulator
        self.display = emulator.display

    def poll(self):
        events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events.append(Event('halt'))

            elif event.type == pygame.KEYDOWN:
                key = ord(event.unicode.upper()) if event.unicode != '' else 0
                # D and L are debug hotkeys (EmulatorStoppedState.on_d, and
                # whatever gets externally attached to 'l' -- see
                # tests/test_emulator_debug_keys.py). They only take over
                # the key while execution is Stopped; while Running, D and
                # L must reach press_key() like any other letter, or typing
                # LIST, LOAD, DEL, or a variable name containing D/L into
                # the Monitor or BASIC silently loses those letters.
                debug_hotkeys_active = not self.emulator.is_executing()

                if event.key == pygame.K_x and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    events.append(Event('ctrlx'))

                elif event.key == pygame.K_LEFT:  # A2 0x08
                    events.append(Event('left', kbd_states=determine_states_from_kmods()))

                elif event.key == pygame.K_RIGHT:  # A2 0x15
                    events.append(Event('right', kbd_states=determine_states_from_kmods()))

                elif event.key == pygame.K_PRINT:
                    events.append(Event('halt'))

                elif event.key == pygame.K_d and debug_hotkeys_active:
                    events.append(Event('d'))

                elif event.key == pygame.K_l and debug_hotkeys_active:
                    events.append(Event('l'))

                elif key != 0:
                    events.append(Event('key', key=key))
        return events

    def present(self):
        elapsed_time = time.monotonic() - self.emulator.last_ticks
        if elapsed_time > self.emulator.elapsed_frame:
            self.display.flash()
            pygame.display.flip()
            self.emulator.last_ticks = time.monotonic()

    def status(self, text):
        self.display.show_status(text)


class NoWindow:

    def poll(self):
        return []

    def present(self):
        pass

    def status(self, text):
        pass
