# papple2 -- Routine

What a routine is in `papple2`, where one starts and where it stops, and what the tools show of it. The words are those of the glossary in [`workbench.md`](workbench.md); positions in code are named by address (lower, higher, before, after, backward, forward). The examples come from Lode Runner's attract play, as recorded in `docs/reports/lr_basic_blocks_analysis/`. The code is `find_routines()` in `src/papple2/workbench/basic_blocks_analysis.py`; the names in brackets below are its helpers.

---

## What a routine is

A routine is the code reachable from an entry, without following calls. It is made of basic blocks that ran: a routine is found from one run, so code that never ran belongs to no routine, and another run may show more of it.

The **entry** is the address where a routine starts. Every block of a run lies in exactly one routine.

A routine is a result of the run, not of the source. It usually matches a subroutine of Xekri's listing, but not always: `make lr-grade` grades the routines against `docs/lr_answer_key.csv` and lists where they differ.

## Where a routine starts

A block is an entry in one of six ways:

- **The run's start.** `0800`, where Lode Runner is loaded and started.
- **A `JSR` target.** `MOVE_GUARD` (`6cdb`), called 112 times by the `JSR` at `6c9b` in `MOVE_GUARDS`.
- **A stack jump's target** (`stack_jumps()`). `TRY_GUARD_MOVE_DOWN` (`6f39`), reached 76 times by the `RTS` at `6e96` in `MOVE_GUARD`, which dispatches through a table.
- **Code that two routines reach** (`shared_entries()`). `CLEAR_PAGE` (`7a5b`): `CLEAR_HGR2` glides into it, and `CLEAR_HGR1` branches forward into it. `TRY_DIGGING_LEFT_check_can_dig_left` (`67e7`) is the same case: `TRY_DIGGING_LEFT` glides into it, and `MOVE_PLAYER` jumps forward into it. Xekri's listing holds it inside `TRY_DIGGING_LEFT`; `papple2` differs there on purpose.
- **Code that one routine glides into and another jumps backward into** (`shared_by_jump_back()`). `PUT_STATUS_BYTE` (`7a74`): `PUT_STATUS_LIVES` glides into it, and `PUT_STATUS_LEVEL` branches backward into it. A jump backward past an entry is not followed (see "Where a routine stops"), so the case before would miss it; the direction of the jump makes no difference to the result.
- **An orphan** (`orphans()`): a block an edge leads to, but that no routine holds. Of the orphans, the one with the lowest address becomes an entry. `TRY_GUARD_MOVE_UP_check_for_gold` (`6f26`): `TRY_GUARD_MOVE_DOWN` jumps backward into the tail of `TRY_GUARD_MOVE_UP`, whose own entry never ran. `CHECK_FOR_MODE_1_INPUT` (`69b8`) is the same case: `CHECK_FOR_INPUT` branches backward into it, 79 times.

The last three kinds are found in rounds. `find_routines()` builds the routines from the entries it has, looks for shared code and orphans, makes them entries, and builds again, until every block lies in exactly one routine.

## Where a routine stops

A routine is followed along the edges between its blocks. It stops in three ways:

- **At another routine's entry.** A `JMP`, a branch or a glide into another entry is not followed. It is an exit of this routine, and a way into the other one.
- **At a call.** A `JSR` is not followed into the routine it calls. Instead, a call fall-through edge leads to the instruction directly after the `JSR`. If the call came back past that instruction, as after `PUT_STRING`, which returns past the bytes it read (`redirected_returns()`), the edge leads to where it landed: the `JSR` at `7a05` in `PUT_STATUS` comes back at `7a25`, which stays in `PUT_STATUS`.
- **At a jump backward past its own entry** (`stops_before()`). The code before the entry belongs to someone else, e.g. the tail of `TRY_GUARD_MOVE_UP` that `TRY_GUARD_MOVE_DOWN` jumps into.

There is one exception to the last rule, the **exit at the door**: the block directly before the entry that ends right at it. A routine's "give up early" branches often lead there, so it belongs to the routine. In `SHOULD_GUARD_MOVE_LEFT`, the `BEQ` at `71a6` goes backward 110 times to the `RTS` at `71a1`:

```
71a1  60                                RTS                      ; the exit at the door
71a2  a4 5a     SHOULD_GUARD_MOVE_LEFT  LDY GUARD_LEFT_COL_LIMIT
71a4  c4 55                             CPY SHARED_55
71a6  f0 f9                             BEQ $71a1
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
- **`u` in `edit()`, and `show_callers()` at the prompt,** list every way into the routine shown: a `JSR`, a `JMP`, a branch, a glide, the `RTS` of a dispatch, and a `JMP` into the middle of the routine. A routine's own loop is not one of them.
- **`show_routine_graph()`** draws the routines as boxes, with the calls and the other ways in as arrows.

## What is still open

- `TRY_MOVING_LEFT` lies inside `MOVE_PLAYER`. The `JMP` at `65c8` goes forward to `65d3`, no other routine reaches it, and no entry lies between them, so nothing in the run separates it. Parked until a run where the player moves in all four directions (`TODO.md`, "Routine structure", group B).
- The start-up code is one routine, `routine_0800`: the two relocations, `MAIN`, `LONG_DELAY` and `INIT_GAME_DATA`, joined by `JMP`s while no call is open (`TODO.md`, "Routine structure", group E).
