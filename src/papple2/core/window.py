import time
from typing import TYPE_CHECKING

import pygame
from pysm import Event

if TYPE_CHECKING:
    from papple2.core.emulator import Emulator


def determine_states_from_kmods() -> int:
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

    def __init__(self, emulator: "Emulator") -> None:
        self.emulator = emulator
        self.display = emulator.display

    def poll(self) -> list[Event]:
        events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events.append(Event('halt'))

            elif event.type == pygame.KEYDOWN:
                key = ord(event.unicode.upper()) if event.unicode != '' else 0
                debug_event = self.debug_hotkey_event(
                    event.key, not self.emulator.is_executing()
                )

                if event.key == pygame.K_x and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    events.append(Event('ctrlx'))

                elif event.key == pygame.K_LEFT:  # A2 0x08
                    events.append(Event('left', kbd_states=determine_states_from_kmods()))

                elif event.key == pygame.K_RIGHT:  # A2 0x15
                    events.append(Event('right', kbd_states=determine_states_from_kmods()))

                elif event.key == pygame.K_PRINT:
                    events.append(Event('halt'))

                elif debug_event is not None:
                    events.append(debug_event)

                elif key != 0:
                    events.append(Event('key', key=key))
        return events

    @staticmethod
    def debug_hotkey_event(pygame_key: int, debug_hotkeys_active: bool) -> Event | None:
        # D and L are debug hotkeys (EmulatorStoppedState.on_d, and
        # whatever gets externally attached to 'l' -- see
        # tests/test_emulator_debug_keys.py). They only take over the key
        # while execution is Stopped; while Running, D and L must reach
        # press_key() like any other letter, or typing LIST, LOAD, DEL, or
        # a variable name containing D/L into the Monitor or BASIC
        # silently loses those letters.
        #
        # Kept as a plain method (pygame.K_* constants and a bool in,
        # an Event or None out -- no pygame.event/pygame.display touched)
        # so this gating can be tested without opening a pygame window.
        # See README.md's testing strategy for why the window path itself
        # stays manual-only.
        if not debug_hotkeys_active:
            return None
        if pygame_key == pygame.K_d:
            return Event('d')
        if pygame_key == pygame.K_l:
            return Event('l')
        return None

    def present(self) -> None:
        elapsed_time = time.monotonic() - self.emulator.last_ticks
        if elapsed_time > self.emulator.elapsed_frame:
            self.display.flash()
            pygame.display.flip()
            self.emulator.last_ticks = time.monotonic()

    def status(self, text: str) -> None:
        self.display.show_status(text)


class NoWindow:

    def poll(self) -> list[Event]:
        return []

    def present(self) -> None:
        pass

    def status(self, text: str) -> None:
        pass
