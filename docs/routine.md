# papple2 -- Routine

What a routine is in `papple2`, where one starts and where it stops, and what the tools show of it. The words are those of [`glossary.md`](glossary.md); positions in code are named by address (lower, higher, before, after, backward, forward). The examples come from Lode Runner's attract play, as recorded in `docs/reports/lr_basic_blocks_analysis/`. The code is `find_routines()` in `src/papple2/workbench/basic_blocks_analysis.py`; the names in brackets below are its helpers.

---

## What a routine is

A routine is the code reachable from an entry, without following calls. It is made of basic blocks that ran: a routine is found from one run, so code that never ran belongs to no routine, and another run may show more of it.

The **entry** is the address where a routine starts. Every block of a run lies in exactly one routine.

A routine is a result of the run, not of the source. It usually matches a subroutine of Xekri's listing, but not always: `make lr-grade` grades the routines against `docs/lr_answer_key.csv` and lists where they differ.

## Where a routine starts

A block is an entry in one of six ways:

- **The run's start.** `0800`, where Lode Runner is loaded and started.
- **A `JSR` target.** `MOVE_GUARD` (`6cdb`), called 112 times by the `JSR` at `6c9b` in `MOVE_GUARDS`.

  ```
  6c9b  20 db 6c  JSR MOVE_GUARD
  6c9e  a5 9a     LDA ALIVE
  ```

- **A stack jump's target** (`stack_jumps()`). `TRY_GUARD_MOVE_DOWN` (`6f39`), reached 76 times by the `RTS` at `6e96` in `MOVE_GUARD`, which dispatches through a table.

  ```
  6e89  20 d8 70  JSR DETERMINE_GUARD_MOVE
  6e8c  0a        ASL
  6e8d  a8        TAY
  6e8e  b9 98 6e  LDA $6e98,Y
  6e91  48        PHA
  6e92  b9 97 6e  LDA GUARD_FN_TABLE,Y
  6e95  48        PHA
  6e96  60        RTS
  ```

- **Code that two routines reach** (`shared_entries()`). `CLEAR_PAGE` (`7a5b`): `CLEAR_HGR2` glides into it, and `CLEAR_HGR1` branches forward into it. `TRY_DIGGING_LEFT_check_can_dig_left` (`67e7`) is the same case: `TRY_DIGGING_LEFT` glides into it, and `MOVE_PLAYER` jumps forward into it. Xekri's listing holds it inside `TRY_DIGGING_LEFT`; `papple2` differs there on purpose.

  ```
      7a51  a9 20     CLEAR_HGR1  LDA #$20
      7a53  a2 40                 LDX #$40
  +-- 7a55  d0 04                 BNE CLEAR_PAGE
  |   7a57  a9 40     CLEAR_HGR2  LDA #$40
  |   7a59  a2 60                 LDX #$60
  +-> 7a5b  85 0b     CLEAR_PAGE  STA $0b
  ```

- **Code that one routine glides into and another jumps backward into** (`shared_by_jump_backward()`). `PUT_STATUS_BYTE` (`7a74`): `PUT_STATUS_LIVES` glides into it, and `PUT_STATUS_LEVEL` branches backward into it. A jump backward past an entry is not followed (see "Where a routine stops"), so the case before would miss it; the direction of the jump makes no difference to the result.

  ```
      7a70  a5 98     PUT_STATUS_LIVES  LDA LIVES
      7a72  a2 10                       LDX #$10
  +-> 7a74  86 85     PUT_STATUS_BYTE   STX GAME_COLNUM
  |   7a76  20 f8 7a                    JSR TO_DECIMAL3
  |   7a79  a9 10                       LDA #$10
  |   7a7b  85 86                       STA GAME_ROWNUM
  |   7a7d  a5 89                       LDA HUNDREDS
  |   7a7f  20 15 7b                    JSR PUT_DIGIT
  |   7a82  a5 8a                       LDA TENS
  |   7a84  20 15 7b                    JSR PUT_DIGIT
  |   7a87  a5 8b                       LDA UNITS
  |   7a89  4c 15 7b                    JMP PUT_DIGIT
  |   7a8c  a5 a6     PUT_STATUS_LEVEL  LDA LEVELNUM
  |   7a8e  a2 19                       LDX #$19
  +-- 7a90  d0 e2                       BNE PUT_STATUS_BYTE
  ```

- **An orphan** (`orphans()`): a block an edge leads to, but that no routine holds. Of the orphans, the one with the lowest address becomes an entry. `TRY_GUARD_MOVE_UP_check_for_gold` (`6f26`): `TRY_GUARD_MOVE_DOWN` jumps backward into the tail of `TRY_GUARD_MOVE_UP`, whose own entry never ran. `CHECK_FOR_MODE_1_INPUT` (`69b8`) is the same case: `CHECK_FOR_INPUT` branches backward into it, 79 times.

  ```
  +---> 69b8  ad 00 c0  CHECK_FOR_MODE_1_INPUT  LDA KBD
  |     69bb  30 10                             BMI $69cd
  |     69bd  a5 95                             LDA INPUT_MODE
  |     69bf  c9 cb                             CMP #$cb
  |     69c1  f0 13                             BEQ $69d6
  |     69c3  ad 62 c0                          LDA BUTN1
  |     69c6  30 05                             BMI $69cd
  |     69c8  ad 61 c0                          LDA BUTN0
  | +-- 69cb  10 09                             BPL $69d6
  | |   ... 69cd-69d6: 9 bytes never ran ...
  | +-> 69d6  a5 ab                             LDA $ab
  | +-- 69d8  d0 18                             BNE $69f2
  | |   69da  a0 00                             LDY #$00
  | |   69dc  b1 a8                             LDA ($a8),Y
  | |   69de  85 aa                             STA $aa
  | |   69e0  c8                                INY
  | |   69e1  b1 a8                             LDA ($a8),Y
  | |   69e3  85 ab                             STA $ab
  | |   69e5  a5 a8                             LDA $a8
  | |   69e7  18                                CLC
  | |   69e8  69 02                             ADC #$02
  | |   69ea  85 a8                             STA $a8
  | |   69ec  a5 a9                             LDA $a9
  | |   69ee  69 00                             ADC #$00
  | |   69f0  85 a9                             STA $a9
  | +-> 69f2  a5 aa                             LDA $aa
  |     69f4  29 0f                             AND #$0f
  |     69f6  aa                                TAX
  |     69f7  bd 0b 6a                          LDA VALID_KEY_COMMANDS,X
  |     69fa  85 9e                             STA KEY_COMMAND
  |     69fc  a5 aa                             LDA $aa
  |     69fe  4a                                LSR
  |     69ff  4a                                LSR
  |     6a00  4a                                LSR
  |     6a01  4a                                LSR
  |     6a02  aa                                TAX
  |     6a03  bd 0b 6a                          LDA VALID_KEY_COMMANDS,X
  |     6a06  85 9f                             STA KEY_COMMAND_LR
  |     6a08  c6 ab                             DEC $ab
  |     6a0a  60                                RTS
  |     ... 6a0b-6a12: 7 bytes never ran ...
  |     6a12  a5 a7     CHECK_FOR_INPUT         LDA GAME_MODE
  |     6a14  c9 01                             CMP #$01
  +---- 6a16  f0 a0                             BEQ CHECK_FOR_MODE_1_INPUT
  ```

The last three kinds are found in rounds. `find_routines()` builds the routines from the entries it has, looks for shared code and orphans, makes them entries, and builds again, until every block lies in exactly one routine.

## Where a routine stops

A routine is followed along the edges between its blocks. It stops in three ways:

- **At another routine's entry.** A `JMP`, a branch or a glide into another entry is not followed. It is an exit of this routine, and a way into the other one.
- **At a call.** A `JSR` is not followed into the routine it calls. Instead, a call fall-through edge leads to the instruction directly after the `JSR`. If the call came back past that instruction, as after `PUT_STRING`, which returns past the bytes it read (`redirected_returns()`), the edge leads to where it landed: the `JSR` at `7a05` in `PUT_STATUS` comes back at `7a25`, which stays in `PUT_STATUS`.
- **At a jump backward past its own entry** (`stops_before()`). The code before the entry belongs to someone else, e.g. the tail of `TRY_GUARD_MOVE_UP` that `TRY_GUARD_MOVE_DOWN` jumps into.

There is one exception to the last rule, the **exit at the door**: the block directly before the entry that ends right at it. A routine's "give up early" branches often lead there, so it belongs to the routine. In `SHOULD_GUARD_MOVE_LEFT`, the `BEQ` at `71a6` goes backward 110 times to the `RTS` at `71a1`:

```
+-> 71a1  60                                RTS
|   71a2  a4 5a     SHOULD_GUARD_MOVE_LEFT  LDY GUARD_LEFT_COL_LIMIT
|   71a4  c4 55                             CPY SHARED_55
+-- 71a6  f0 f9                             BEQ $71a1
```

`GUARD_FIND_CANDIDATE_ROW_BELOW` (`739a` before its entry `739d`) and `SHOULD_GUARD_MOVE_RIGHT` (`720b` before `720c`) have the same shape.

## Span

The span of a routine runs from its block with the lowest address to the end of its block with the highest, gaps included. It is what `listing()`, `edit()` and `lr_listing.tsv` show.

- The span can start before the entry: `SHOULD_GUARD_MOVE_LEFT`'s span starts at `71a1`, the exit at the door, one byte before its entry.
- The span can hold code of other routines, or code that never ran, between the routine's own blocks. `listing()` and `edit()` show code that never ran as one row, e.g. `... 6d64-6e85: 289 bytes never ran ...` in `MOVE_GUARD`.

## What the tools show

- **`show_routines()`** lists every routine of the run, with its entry, label, blocks and how often it was entered.
- **`listing(entry)` and `edit(entry)`** show a routine over its span.
- **The last row of a routine that runs on into another one** says where, e.g. `... runs on into CLEAR_PAGE ...` at the end of `CLEAR_HGR2`. In `edit()`, Enter goes there.
- **Enter in `edit()`** follows a `JSR`, a `JMP` or a branch. Into another routine, it opens that routine with the bar on the target, also when the target is not the routine's entry (`Session.routine_of()`).
- **`u` in `edit()`, and `show_ways_in()` at the prompt,** list every way into the routine shown: a `JSR`, a `JMP`, a branch, a glide, the `RTS` of a dispatch, and a jump through a door (an address inside the routine other than its entry). A routine's own loop is not one of them.
- **`show_routine_graph()`** draws the routines as boxes, with the calls and the other ways in as arrows.

## What is still open

- `TRY_MOVING_LEFT` lies inside `MOVE_PLAYER`. The `JMP` at `65c8` goes forward to `65d3`, no other routine reaches it, and no entry lies between them, so nothing in the run separates it. Parked until a run where the player moves in all four directions (`TODO.md`, "Routine structure", group B).
- The start-up code is one routine, `routine_0800`: the two relocations, `MAIN`, `LONG_DELAY` and `INIT_GAME_DATA`, joined by `JMP`s while no call is open (`TODO.md`, "Routine structure", group E).
