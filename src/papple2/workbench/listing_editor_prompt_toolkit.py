#!/usr/bin/env python3
"""
src/papple2/workbench/listing_editor_prompt_toolkit.py

A purely visual prototype of the new modal listing editor.
Run via `make prototype` to see prompt_toolkit in action.
Use Up/Down arrows, Page Up/Page Down, and 'q' to quit.
"""

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText

# Dummy data from r_11x2_1.asm
DUMMY_LISTING = [
    "      8336  84 1b     r_11x2_1  STY row_num             ; A = sprite, Y = row, X = shift",
    "      8338  85 1e               STA sprite_num",
    "      833a  20 72 88            JSR load_ax_from_table  ; returns A, X",
    "      833d  85 1c               STA col_num",
    "      833f  86 71               STX col_shift_amount",
    "      8341  20 38 84            JSR routine_8438",
    "      8344  a2 0b               LDX #$0b",
    "      8346  86 1d               STX ix_sprite_row",
    "      8348  a2 00               LDX #$00",
    "      834a  a5 71               LDA col_shift_amount",
    "      834c  c9 05               CMP #$05",
    "+---- 834e  b0 26               BCS .loop2",
    "| +-> 8350  a4 1b     .loop1    LDY row_num",
    "| |   8352  20 3e 7a            JSR lookup_hgr          ; with Y",
    "| |   8355  a4 1c               LDY col_num",
    "| |   8357  b5 df               LDA block_data,X",
    "| |   8359  49 7f               EOR #$7f",
    "| |   835b  31 0c               AND (zp_hgr1_row_ptr),Y",
    "| |   835d  11 0e               ORA (zp_hgr2_row_ptr),Y",
    "| |   835f  91 0c               STA (zp_hgr1_row_ptr),Y",
    "| |   8361  e8                  INX",
    "| |   8362  c8                  INY",
    "| |   8363  b5 df               LDA block_data,X",
    "| |   8365  49 7f               EOR #$7f",
    "| |   8367  31 0c               AND (zp_hgr1_row_ptr),Y",
    "| |   8369  11 0e               ORA (zp_hgr2_row_ptr),Y",
    "| |   836b  91 0c               STA (zp_hgr1_row_ptr),Y",
    "| |   836d  e8                  INX",
    "| |   836e  e8                  INX",
    "| |   836f  e6 1b               INC row_num",
    "| |   8371  c6 1d               DEC ix_sprite_row",
    "| +-- 8373  d0 db               BNE .loop1",
    "|     8375  60                  RTS",
    "+-+-> 8376  a4 1b     .loop2    LDY row_num",
    "  |   8378  20 3e 7a            JSR lookup_hgr",
    "  |   837b  a4 1c               LDY col_num",
    "  |   837d  b5 df               LDA block_data,X"
]

class EditorState:
    def __init__(self):
        self.cursor_idx = 0

state = EditorState()

def get_listing_text():
    result = []
    for i, line in enumerate(DUMMY_LISTING):
        if i == state.cursor_idx:
            # Highlight the active row by reversing background/foreground
            result.append(("reverse", line + "\n"))
        else:
            result.append(("", line + "\n"))
    return FormattedText(result)

def get_status_text():
    # Extract just the hex address from the dummy text for the status bar
    current_addr = DUMMY_LISTING[state.cursor_idx][12:16].strip()
    return FormattedText([
        ("bold", f" Address: ${current_addr.upper()} "),
        ("", " | [Enter] Leap  [Backspace] Return  [L]abel  [C]omment  [Q]uit")
    ])

breadcrumbs_window = Window(
    content=FormattedTextControl(FormattedText([("bold bg:ansiblue fg:white", " papple2 > LOAD_LEVEL > routine_8438 > r_11x2_1 ")])),
    height=1
)

listing_window = Window(
    content=FormattedTextControl(get_listing_text),
    cursorline=False,
    wrap_lines=False
)

status_window = Window(
    content=FormattedTextControl(get_status_text),
    height=1,
    style="bg:ansigray fg:black"
)

root_container = HSplit([
    breadcrumbs_window,
    listing_window,
    status_window
])

layout = Layout(root_container)

kb = KeyBindings()

@kb.add("q")
def exit_app(event):
    event.app.exit()

@kb.add("up")
def move_up(event):
    state.cursor_idx = max(0, state.cursor_idx - 1)

@kb.add("down")
def move_down(event):
    state.cursor_idx = min(len(DUMMY_LISTING) - 1, state.cursor_idx + 1)

@kb.add("pageup")
def page_up(event):
    state.cursor_idx = max(0, state.cursor_idx - 10)

@kb.add("pagedown")
def page_down(event):
    state.cursor_idx = min(len(DUMMY_LISTING) - 1, state.cursor_idx + 10)

app = Application(
    layout=layout,
    key_bindings=kb,
    full_screen=True,
    mouse_support=True
)

def main():
    app.run()

if __name__ == "__main__":
    main()
