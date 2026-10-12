# Lode Runner case studies

A case study reads a piece of Lode Runner's real code with `papple2`'s tools, the way the walkthrough (`tests/test_walkthrough.py`) reads its tiny programs: from the run, through the routines and their callers, to the listing in the editor, with the dossier's labels, comments and colors. It need not explain the code completely. XekriRedmane's literate source, in the HTML edition at https://fschuhi.github.io/a2-lode-runner/, is the oracle: it grades what we find, and it is where to look when we are stuck.

The names come first, since everything we read is read through them.

---

## Names

The labels in `dossiers/lode_runner/annotations.json` follow the rules below. One name, one thing: a word means the same in every label, comment and document.

### Units of position

| Word | What it is | Range |
|---|---|---|
| `cell` | A place in the grid of sprites, 28 across and 17 down. A cell is 10 pixels wide and 11 rows tall. Row 16 is the status line. | `col` 0-27, `row` 0-16 |
| `col`, `row` | The column and the row of a cell, never of a pixel. | as above |
| `y` | A pixel row on the screen. | 0-191 |
| `hx` | A pixel column halved: the pixel column is `x = 2 * hx`. It fits in one register, which 0-279 does not. Only even pixel columns can be reached this way, so a sprite always starts on an even column, and its colors never change as it moves sideways. | 0-139 |
| `byte`, `shift` | Where a pixel column lies in a screen row: `byte = x div 7`, `shift = x mod 7`. A screen byte shows 7 pixels, bits 0-6; bit 7 picks the color pair and is no pixel. | 0-39, 0-6 |
| `ptr` | The address of a screen row, on page 1 or page 2. | |

### Patterns

| Kind | Pattern | Example |
|---|---|---|
| Routine | verb, `_at_`, the unit it takes | `draw_at_hx`, `draw_at_cell` |
| Converter | from `_to_` to | `hx_to_byte_shift`, `cell_to_y_hx` |
| Table | `tbl_`, the key, what it holds | `tbl_hx_byte`: hx -> byte |
| Zero page | `zp_` and what it holds | `zp_y`, `zp_shift` |
| Local label | a short word for what the loop does | `draw_at_hx.two`, `draw_at_hx.three` |
| Apple II | as in `STANDARD_LABELS`: `r:`, `w:` or `rw:` and the name | `rw:HIRES`, `r:KBD:w:CLR80COL` |

Color ranges in `colors.json` that cover exactly one table or one routine carry its label.

### The labels for drawing sprites

| Address | Label | What it is |
|---|---|---|
| `000c` | `zp_ptr1` | Address of a screen row, two bytes (`zp_ptr1_hi` at `000d`). `y_to_ptrs` puts the row on page 1 here, `y_to_ptr` the row on the page in `$1f`. |
| `000e` | `zp_ptr2` | The same row on page 2 (`zp_ptr2_hi` at `000f`), from `y_to_ptrs`. |
| `001b` | `zp_y` | The pixel row of the sprite row being drawn; one higher after each row. |
| `001c` | `zp_byte` | The byte in the screen row where the sprite starts. |
| `001d` | `zp_rows_todo` | Sprite rows still to draw: 11 at the start, 0 at the end. |
| `001e` | `zp_sprite` | The sprite's number, 0-103. |
| `0071` | `zp_shift` | How far the sprite is shifted right within `zp_byte`, 0-6. |
| `00df` | `zp_shifted` | The shifted sprite, 33 bytes: 11 rows of 3 bytes. |
| `1a85` | `tbl_y_offs_lo` | y -> low byte of the row's offset in a page. |
| `1b45` | `tbl_y_offs_hi` | y -> high byte of the row's offset; the page is ORed in. |
| `1c9a` | `tbl_hx_byte` | hx -> byte, `2 * hx div 7`. 140 entries. |
| `1d26` | `tbl_hx_shift` | hx -> shift, `2 * hx mod 7`. 140 entries. |
| `7a31` | `y_to_ptr` | Y = y -> `zp_ptr1`, on the page in `$1f`. |
| `7a3e` | `y_to_ptrs` | Y = y -> `zp_ptr1` on page 1 and `zp_ptr2` on page 2. |
| `82aa` | `draw_at_cell1` | Draws sprite A at the cell in `$85`/`$86`, on page 1. |
| `82b0` | `draw_at_cell2` | The same on page 2. |
| `82b4` | `draw_at_cell` | The code both share, from here on. |
| `8336` | `erase_at_hx` | Erases sprite A at Y = y, X = hx on page 1, filling the hole from page 2. |
| `83a7` | `draw_at_hx` | Draws sprite A at Y = y, X = hx on page 1, and notes whether page 1 and page 2 differed under it. |
| `8438` | `shift_sprite` | X = shift, sprite in `zp_sprite` -> `zp_shifted`. Changes its own instructions (`shift_sprite.selfmod1` to `8`). |
| `885d` | `cell_to_y_hx` | Y = row, X = col -> Y = y, X = hx. |
| `8868` | `col_to_byte_shift` | X = col -> A = byte, X = shift. |
| `8872` | `hx_to_byte_shift` | X = hx -> A = byte, X = shift. |

In each drawing routine, `.two` is the loop for 2 bytes per row, `.three` the loop for 3.

Not labelled yet: the tables for cells at `1c35` (col -> hx), `1c51` (row -> y), `1c62` (col -> byte) and `1c7e` (col -> shift), and the page at `$1f`.

---

## Case study 1: drawing and erasing a sprite

### Draw: `draw_at_hx`

### Moving the box

A sprite is 10 pixels wide. Each line moves it one hx, two pixels, to the right. `#` is the sprite, the pixel columns are grouped by screen bytes, and byte and shift come from `tbl_hx_byte` and `tbl_hx_shift`:

```
            byte 0   byte 1   byte 2
x           0123456  7890123  4567890
hx 0 (x 0)  #######  ###....  .......   byte 0, shift 0: 2 bytes
hx 1 (x 2)  ..#####  #####..  .......   byte 0, shift 2: 2 bytes
hx 2 (x 4)  ....###  #######  .......   byte 0, shift 4: 2 bytes
hx 3 (x 6)  ......#  #######  ##.....   byte 0, shift 6: 3 bytes
hx 4 (x 8)  .......  .######  ####...   byte 1, shift 1: 2 bytes
```

Shifted by s, the 10 pixels cover s to s+9 of the first byte and the ones after it. The third byte starts at pixel 14, so it is reached when s is 5 or more: then the routine takes `.three` instead of `.two`.

### Erase: `erase_at_hx`, the twin

### Draw by cell: `draw_at_cell`
