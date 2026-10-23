# papple2 -- Example

This file and `example.html` are a pair: `example.html` is this file translated into HTML by following `style-guide.md`. It shows each element of the markdown files once: prose, lists, a table, a code fence, a listing and a diagram.

---

## Prose

A paragraph is one line in the markdown; the page wraps it. Inline code marks names from the code and the files, such as `find_routines()` or `lr_listing.tsv`. A link: [`routine.md`](../routine.md). **Bold** marks a word as it is defined, *emphasis* a word to stress.

### A heading of the third level

Positions in code are named by address:

- A lower address comes before, a higher one after.
- A jump to a lower address goes backward, to a higher one forward.

A routine stops in three ways:

1. At another routine's entry.
2. At a call.
3. At a jump backward past its own entry.

## A table

The branches the run took in the listing below, as `lr_split_transitions.csv` counts them:

| Branch at | Goes to | Direction | Taken |
|-----------|---------|-----------|------:|
| `6286`    | `628c`  | forward   | 224   |
| `628a`    | `6292`  | forward   | 224   |
| `6298`    | `629c`  | forward   | 448   |
| `62a6`    | `627e`  | backward  | 432   |
| `62ae`    | `6269`  | backward  | 15    |
| `62b3`    | `62c3`  | forward   | 1     |

## A code fence that is not a listing

How the listing below was made, at the prompt:

```
make lr-current
clip(listing("LOAD_LEVEL"))
```

## A listing

The end of `LOAD_LEVEL`, from `6267` to its `RTS` at `62c3`, as `listing()` shows it. Two loops: the outer one goes through the 16 rows of the level, the inner one through the 28 columns of each row, so the `STA` at `629c` stores 448 values.

```
          6267  a4 86                 LDY GAME_ROWNUM
+-------> 6269  b9 05 1c              LDA CURR_LEVEL_ROW_SPRITES_PTR_OFFSETS,Y
|         626c  85 06                 STA PTR1
|         626e  85 08                 STA PTR2
|         6270  b9 15 1c              LDA CURR_LEVEL_ROW_SPRITES_PTR_PAGES,Y
|         6273  85 07                 STA $07
|         6275  b9 25 1c              LDA CURR_LEVEL_ROW_SPRITES_PTR_PAGES2,Y
|         6278  85 09                 STA $09
|         627a  a9 00                 LDA #$00
|         627c  85 85                 STA GAME_COLNUM
| +-----> 627e  a5 1a                 LDA TMP            ; parity of $1a: even -> low nibble, odd -> high nibble
| |       6280  4a                    LSR
| |       6281  a4 92                 LDY LEVEL_DATA_INDEX
| |       6283  b9 00 0d              LDA DISK_BUFFER,Y  ; byte from the buffer at $0d00, two values per byte
| |   +-- 6286  b0 04                 BCS $628c
| |   |   6288  29 0f                 AND #$0f           ; even: low nibble; BPL always jumps
| | +---- 628a  10 06                 BPL $6292
| | | +-> 628c  4a                    LSR                ; odd: high nibble, then on to the next byte
| | |     628d  4a                    LSR
| | |     628e  4a                    LSR
| | |     628f  4a                    LSR
| | |     6290  e6 92                 INC LEVEL_DATA_INDEX
| | +---> 6292  e6 1a                 INC TMP
| |       6294  a4 85                 LDY GAME_COLNUM
| |       6296  c9 0a                 CMP #$0a           ; values 10-15 are invalid: read as 0
| |   +-- 6298  90 02                 BCC $629c
| |   |   ... 629a-629c: 2 bytes never ran ...
| |   +-> 629c  91 06                 STA (PTR1),Y
| |       629e  91 08                 STA (PTR2),Y
| |       62a0  e6 85                 INC GAME_COLNUM
| |       62a2  a5 85                 LDA GAME_COLNUM
| |       62a4  c9 1c                 CMP #$1c
| +------ 62a6  90 d6                 BCC $627e
|         62a8  e6 86                 INC GAME_ROWNUM
|         62aa  a4 86                 LDY GAME_ROWNUM
|         62ac  c0 10                 CPY #$10
+-------- 62ae  90 b9                 BCC $6269
          62b0  20 b3 63              JSR DRAW_LEVEL_PAGE2
      +-- 62b3  90 0e                 BCC $62c3
      |   ... 62b5-62c3: 14 bytes never ran ...
      +-> 62c3  60                    RTS
```

## A diagram

A tail call: `TRY_GUARD_MOVE_LEFT` ends with `JMP STORE_GUARD_DATA` instead of `JSR STORE_GUARD_DATA` and `RTS`. So the `RTS` at the end of `STORE_GUARD_DATA` returns straight to `MOVE_GUARDS`, which called `MOVE_GUARD`. In the attract play, 26 of the 112 guard moves went this way.

```
MOVE_GUARDS --JSR (6c9b)--> MOVE_GUARD --dispatch (6e96)--> TRY_GUARD_MOVE_LEFT
                                                               |
                                                               JMP STORE_GUARD_DATA (7044)
                                                               v
MOVE_GUARDS <-------------- RTS (75cd) -------------------- STORE_GUARD_DATA
            lands at 6c9e, after the JSR at 6c9b
```
