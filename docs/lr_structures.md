# The structures of Lode Runner, read from Xekri's source

Started 2026-10-15, base commit `dc2d967`. Read from Xekri's literate source (`main.nw`) and its listing (`docs/listings/listing_clean.tsv`), with the counts from the attract play's split reports (`docs/reports/lr_basic_blocks_analysis/lr_split_tiles.csv` and `lr_split_transitions.csv`). Continued 2026-10-17 in one go (one-shot session): the answer key, Part 1 completed, Part 2 entries 2 to 6, Part 3.

---

## How to read this document

- **Purpose**: a target for `papple2`'s routine detection (`find_routines()` in `src/papple2/workbench/basic_blocks_analysis.py`). The detection only sees what ran, so this document keeps apart what ran in the attract play (counts from the split reports) and what only exists in Xekri's source (marked "0", "never ran", or "read").
- **The answer key** is `docs/lr_answer_key.csv`: one row per block that ran, with the Xekri subroutine whose span it lies within. Part 3 grades against it. How it was built: "The answer key" below.
- **Order**: Status, Terms, the map of guard movement, the answer key, Part 1 (the table of Xekri's subroutines for the pilot), Part 2 (the catalogue of structures), Part 3 (the grading and a rule). Open questions and side findings are appendices at the end.
- **Marks**: "computed" means a script counted or checked it against the reports or the listing; "read" means it was read from the code by eye and not checked by a tool.

---

## Status (2026-10-17)

- **The answer key**: done, computed, for the whole run: 642 blocks, 79 of Xekri's units with blocks that ran, plus one block that lies outside Xekri's listing (`0800`).
- **Part 1**, the table of Xekri's subroutines for the pilot: all 22 rows done, including the 7 helpers of the guard AI.
- **Part 2**, the catalogue of structures: all six entries written with their eight parts, plus one structure met while grading (the return behind a payload). Part 6 of every entry lists alternatives, no decision yet. The explain-back of entry 1 is answered; those of entries 2 to 6 are open.
- **Part 3**: `find_routines()` graded for the whole run (57 of 79 units agree, 42 blocks in more than one routine), and a rule proposed and graded by a throwaway script (77 of 79 units agree, no block in more than one routine). The rule was built and graded on the same run; see Part 3, "Caveats".
- **Done**, as the handover defines it: Part 1 covers the pilot, Part 2 holds the six structures with all eight parts each, Part 3 has a rule graded on the pilot (here: on the whole run). Open: the explain-back checks of entries 2 to 6, and the decisions in part 6 of every entry.

---

## Terms

The terms as of 2026-10-17. The current ones are in [`glossary.md`](glossary.md).

- **Xekri's subroutine**: a unit of Xekri's source, from his `SUBROUTINE` mark to its last instruction. Static: it holds its code whether that code ran or not.
- **routine**: `papple2`'s word. The blocks that ran, found from one run. A routine is a hypothesis: another run can show blocks this run never reached.
- **part of a routine**: a block that ran and that the rule for routines assigns to it. Code that never ran is part of no routine.
- **span**: from the first address up to the end. For a Xekri subroutine: from its start to the first address behind its last instruction. For a routine: from its lowest block to the end of its highest block, gaps included.
- **lies within**: position only. Data, payload or code that lies within a span is not claimed as belonging to it. Whether it belongs is a question for stretches (`GOALS.md`, "Routines as stretches").
- **label**: what an address is called. This document uses Xekri's labels; the dossier's labels are not touched by it.
- **stack jump**: an `RTS` to an address that is not right behind a `JSR`, i.e. not an ordinary return. The mechanism, whatever it is used for (`papple2`'s `stack_jumps()`).
- **dispatch by `RTS`**: one use of a stack jump: pushing an address taken from a table and doing `RTS` to choose among several subroutines (`MOVE_GUARD`, `6e96`). The returns behind a payload are stack jumps too, but no dispatch.
- **Addresses**: a pair like `6f26-6f39` includes the first address and excludes the second.

### Names added on 2026-10-17

- **unit**: what the answer key assigns a block to: a Xekri subroutine, or an unmarked unit.
- **unmarked unit**: an `ORG` chunk of Xekri's source that starts with a global code label but has no `SUBROUTINE` mark: `MAIN` (`5f7d`), `INIT_GAME_DATA` (`6056`), `LONG_DELAY` (`618e`), and, never run, the code at `6000` (no label), `ANIM0` (`8b7a`) and `FORMAT_PATCH` (`8e00`).
- **door**: an address where control enters a Xekri subroutine from outside other than at its entry, e.g. `TRY_GUARD_MOVE_UP_check_for_gold` (`6f26`). Already used in this sense in the notes of Part 1.
- **return behind a payload**: an `RTS` that returns for a `JSR` but lands further on than 3 bytes behind it, because the subroutine read the bytes behind the `JSR` (`LOAD_SOUND_DATA`, `PUT_STRING`). A stack jump, but no dispatch.
- **range** (of a routine, in the rule of Part 3): from the routine's entry up to the next entry above it in address order. Not the same as its span: the range is fixed by the entries, the span by the blocks.
- **orphan**: a block that an edge leads to, but that no routine takes in under the rule of Part 3.

---

## Where guard movement sits

Only the jumps between Xekri's subroutines are shown. Counts are from the attract play.

```
game loop (60e4), 84 rounds in the attract play
   |  JSR MOVE_GUARDS
   v
MOVE_GUARDS (6c82)             picks which guards move this round
   |  JSR MOVE_GUARD                                        112x
   v
MOVE_GUARD (6cdb)              moves one guard, the next in turn
   |  JSR LOAD_GUARD_DATA      the guard's bytes -> working copy in zero page
   |  JSR DETERMINE_GUARD_MOVE    -> A = 0 to 4   (the guard AI: where to go)
   |  PHA / PHA / RTS          the dispatch, through GUARD_FN_TABLE
   |
   +-- 4  TRY_GUARD_MOVE_DOWN (6f39)   76x --JMP--> tail of TRY_GUARD_MOVE_UP --JMP--+
   +-- 1  TRY_GUARD_MOVE_LEFT (6fbc)   26x ---------------------------------JMP-------+
   +-- 2  TRY_GUARD_MOVE_RIGHT (7047)  10x ---------------------------------JMP-------+
   +-- 3  TRY_GUARD_MOVE_UP (6eac)      0x                                           |
   +-- 0  STORE_GUARD_DATA (75a8)       0x                                           |
                                                                                     v
                          STORE_GUARD_DATA (75a8)   working copy -> the guard's bytes
                             |  RTS, back in MOVE_GUARDS                       112x
```

- **Speed**: a guard moves only when `MOVE_GUARDS` says so. That is how guards move at another speed than the player: 112 guard moves in 84 rounds, one or two per round.
- **The working copy**: each guard's position, timers and the like live in tables (`$0c60`-`$0ca0`, one byte per guard per field). `MOVE_GUARD` copies one guard's bytes into zero page (`$12`-`$19`), works on that copy, and must copy it back at the end.
- **Why every path ends in `STORE_GUARD_DATA`**: whatever the guard did, the copy has to go back. So every path ends with a `JMP` to the write-back, and its one `RTS` returns to `MOVE_GUARDS`. That is the reason for most of the tail calls here.
- **One way in, one way out**: one `JSR` goes in, one `RTS` comes out. In between, control passes through three or four of Xekri's subroutines by `JMP` and dispatch, never by `JSR`/`RTS` pairs.

---

## The answer key

`docs/lr_answer_key.csv`, computed by a throwaway script from `docs/listings/listing_clean.tsv` and `lr_split_tiles.csv`. Columns: `block_start`, `block_end`, `executions` (from the split tiles), `xekri_subroutine` and `xekri_start` (the unit the block lies within, and the unit's start), `note`.

How a block gets its unit:

- **Units start** at Xekri's `SUBROUTINE` marks, and at the unmarked units (see "Names added"). A unit's name is the global label at its mark, or, where the mark lies in front of the entry (`67d8`, `689e`, `71a1`, `720b`, `72fd`, `739a`), the first global label behind it. A unit's start (`xekri_start`) is the address of its mark, also in those six cases; Part 1 does the same.
- **A block belongs to the unit** with the highest start at or below the block's start. Data labels (tables, followed by `HEX`, `BYTE` or `WORD`) start no unit: code behind a table, like `.ladder` (`6e85`) behind `GUARD_X_ADJ_TABLE`, stays in the unit in front of the table.
- **Global labels inside a span start no unit**: `DRAW_SPRITE` (`82b4`), `CLEAR_PAGE` (`7a5b`), `SOUND_DELAY1` (`86b5`), `CHECK_FOR_BUTTON_DOWN` (`619b`), `TRY_GUARD_MOVE_UP_check_for_gold` (`6f26`) and the like. The note column names them where a block starts at one.
- **Unmarked units**: `MAIN`, `INIT_GAME_DATA` and `LONG_DELAY` each get a unit of their own, because Xekri gives each its own `ORG` chunk and a name, and because folding them into the unit in front of them would make `MAIN` part of `UNUSED`. Read from the listing: by dasm's rules they share the scope of local labels with the unit in front (`MAIN` with `UNUSED`; `INIT_GAME_DATA` and `LONG_DELAY` with `RESET_GAME`, e.g. `6180 BEQ .restore_enable_sound` jumps from `INIT_GAME_DATA` to `61d0` in `LONG_DELAY`; never ran). The answer key does not follow that scope.
- **Relocation**: the five blocks at `2800-2832` ran at their load address, before relocation moved them to `5f00-5f32`, where the listing has them (`+3700`, see entry 6). They get `RELOCATE0_ALIAS`, the unit at their listing address; the note gives that address. The block at `0800` (`JMP $2800`) ran at the load address too, but its listing address `3f00` is not in Xekri's listing: it gets `-` as unit and start.
- **Notes** also mark the blocks before an entry (the exit at the door), the targets of the dispatch by `RTS`, and the two blocks where a return behind a payload lands.

Result (computed): 642 blocks; 641 in 79 units, 1 (`0800`) in none. 76 of the 79 units have a `SUBROUTINE` mark (two of them, `RELOCATE0_ALIAS` and `RELOCATE1`, are the relocation code that runs before the game is in place); 3 are unmarked units (`MAIN`, `INIT_GAME_DATA`, `LONG_DELAY`).

---

## Part 1: the subroutines of guard movement, as Xekri has them

The pilot's part of the answer key, with the ways in and out. Any rule for routines that `papple2` uses later is graded against the answer key; Part 3 does this for the whole run.

**Scope**: `MOVE_GUARD`, `GUARD_DO_NOTHING`, the four `TRY_GUARD_MOVE_*`, the six small helpers from `GET_GUARD_SPRITE_AND_COORDS` (`74df`) to `NUDGE_GUARD_TOWARDS_EXACT_ROW` (`7595`), `STORE_GUARD_DATA` and `LOAD_GUARD_DATA`. `DETERMINE_GUARD_MOVE` and its seven helpers are the guard AI, which decides where a guard goes. Everything else in the scope carries that decision out. The sprite routines `ERASE_SPRITE_AT_PIXEL_COORDS` (`8336`) and `DRAW_SPRITE_AT_PIXEL_COORDS` (`83a7`) appear only as callees.

**Columns**:

| Column | Meaning |
|---|---|
| name | Xekri's label at the start |
| start | the first address of Xekri's subroutine: its `SUBROUTINE` mark (see the notes for subroutines whose start is not their entry) |
| end | the first address behind its last instruction |
| entered by | `JSR`, `JMP`, `RTS` dispatch or falling in, each from where, with the count in the attract play |
| leaves by | `RTS`, `JMP` to which subroutine, falling into which subroutine, with the count |
| ran | yes, partly or no, in the attract play |

| name | start | end | entered by | leaves by | ran |
|---|---|---|---|---|---|
| `MOVE_GUARD` | `6cdb` | `6e97` | `JSR` from `MOVE_GUARDS` (`6c9b`): 112 | `JMP STORE_GUARD_DATA` at `6d02`, `6dbd`, `6e62`, `6e7c`: 0 each; `RTS` dispatch at `6e96`: 112, to `STORE_GUARD_DATA` 0, `TRY_GUARD_MOVE_LEFT` 26, `TRY_GUARD_MOVE_RIGHT` 10, `TRY_GUARD_MOVE_UP` 0, `TRY_GUARD_MOVE_DOWN` 76 | partly: the hole and falling paths never ran |
| `STORE_GUARD_DATA` | `75a8` | `75ce` | `JMP` from `MOVE_GUARD` (`6d02`, `6dbd`, `6e62`, `6e7c`): 0; `GUARD_DO_NOTHING` (`6ea9`): 0; `TRY_GUARD_MOVE_UP` (`6f36`): 76, all of them on the way from `TRY_GUARD_MOVE_DOWN`; `TRY_GUARD_MOVE_DOWN` (`6f60`): 0; `TRY_GUARD_MOVE_LEFT` (`6fee`): 0, (`7044`): 26; `TRY_GUARD_MOVE_RIGHT` (`707b`): 0, (`70d5`): 10. `RTS` dispatch from `MOVE_GUARD` (`6e96`, value 0): 0. No `JSR` | `RTS` at `75cd`, to the caller of `MOVE_GUARD`: `MOVE_GUARDS` behind `6c9b`, 112 | yes, whole |
| `GUARD_DO_NOTHING` | `6ea1` | `6eac` | `BEQ` from `TRY_GUARD_MOVE_UP` (`6eb4`, `6ec7`, `6ecb`, `6ecf`, `6ed3`): 0 each. Not by the dispatch | `JMP STORE_GUARD_DATA` (`6ea9`): 0 | no |
| `TRY_GUARD_MOVE_UP` | `6eac` | `6f39` | `RTS` dispatch from `MOVE_GUARD` (`6e96`, value 3): 0; `JMP` from `TRY_GUARD_MOVE_DOWN` into `TRY_GUARD_MOVE_UP_check_for_gold` (`6fb9`): 60, and into `TRY_GUARD_MOVE_UP_inc_anim_state` (`6fb6`): 16 | `BEQ` into `GUARD_DO_NOTHING` (`6eb4`, `6ec7`, `6ecb`, `6ecf`, `6ed3`): 0; `JMP STORE_GUARD_DATA` (`6f36`): 76 | partly: only `6f26-6f39`, and only on the way from `TRY_GUARD_MOVE_DOWN` |
| `TRY_GUARD_MOVE_DOWN` | `6f39` | `6fbc` | `RTS` dispatch from `MOVE_GUARD` (`6e96`, value 4): 76 | `JMP STORE_GUARD_DATA` (`6f60`): 0; `JMP TRY_GUARD_MOVE_UP_inc_anim_state` (`6fb6`): 16; `JMP TRY_GUARD_MOVE_UP_check_for_gold` (`6fb9`): 60 | partly: the "can't go down" exit (`6f60`), the brick case (`6f92`) and the kill (`6fac`) never ran |
| `TRY_GUARD_MOVE_LEFT` | `6fbc` | `7047` | `RTS` dispatch from `MOVE_GUARD` (`6e96`, value 1): 26 | `JMP STORE_GUARD_DATA` (`6fee`): 0; `JMP STORE_GUARD_DATA` (`7044`): 26 | partly: the "can't move" exit (`6fee`), the brick case (`700d`), the kill (`701a`) and the rope (`7037`) never ran |
| `TRY_GUARD_MOVE_RIGHT` | `7047` | `70d8` | `RTS` dispatch from `MOVE_GUARD` (`6e96`, value 2): 10 | `JMP STORE_GUARD_DATA` (`707b`): 0; `JMP STORE_GUARD_DATA` (`70d5`): 10 | partly: the "can't move" exit (`707b`), the brick case (`709e`), the kill (`70ab`) and the rope (`70c8`) never ran |
| `DETERMINE_GUARD_MOVE` | `70d8` | `71a1` | `JSR` from `MOVE_GUARD` (`6e89`): 112 | `RTS` "in a hole: up" (`70f6`): 0; `RTS` "right, same row" (`7146`): 2; `RTS` "left, same row" (`7185`): 0; `RTS` after the four helpers (`71a0`): 110. All to `MOVE_GUARD` (`6e8c`) | partly: the hole case (`70ee`) and the search to the left (`7147-7186`) never ran |
| `LOAD_GUARD_DATA` | `75ce` | `75f4` | `JSR` from `MOVE_GUARD` (`6ce7`): 112; from `HANDLE_TIMERS` (`76a6`): 0; from `GUARD_RESURRECTIONS` (`7724`): 0 | `RTS` (`75f3`): 112 | yes, whole |
| `GET_GUARD_SPRITE_AND_COORDS` | `74df` | `74f7` | `JSR` from `TRY_GUARD_MOVE_UP` (`6f30`): 76, (`6ed5`): 0; `TRY_GUARD_MOVE_DOWN` (`6f63`): 76; `TRY_GUARD_MOVE_LEFT` (`6ff1`, `703e`): 26 each; `TRY_GUARD_MOVE_RIGHT` (`707e`, `70cf`): 10 each; `MOVE_GUARD` (`6d64`, `6db7`, `6e5c`, `6e69`, `6e76`): 0; outside the pilot (`76a9`, `7747`, `775b`): 0 | `RTS` (`74f6`): 224 | yes, whole |
| `INC_GUARD_ANIM_STATE` | `7574` | `7582` | `JSR` from `TRY_GUARD_MOVE_UP` (`6f2d`): 76, all on the way from `TRY_GUARD_MOVE_DOWN`; `TRY_GUARD_MOVE_LEFT` (`703b`): 26; `TRY_GUARD_MOVE_RIGHT` (`70cc`): 10 | `RTS` "first picture of the group" (`757c`): 51; `RTS` "next picture" (`7581`): 61 | yes, whole |
| `GUARD_DROP_GOLD` | `753e` | `7574` | `JSR` from `TRY_GUARD_MOVE_UP` (`6ef5`): 0; `TRY_GUARD_MOVE_DOWN` (`6f87`): 16; `TRY_GUARD_MOVE_LEFT` (`7002`): 6; `TRY_GUARD_MOVE_RIGHT` (`7093`): 2 | `RTS` (`7573`): 24; tail call `JMP DRAW_SPRITE_AT_PIXEL_COORDS` (`756e`): 0 | partly: only the first test and the `RTS` ran |
| `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` | `74f7` | `753e` | `JSR` from `TRY_GUARD_MOVE_UP` (`6f26`): 60, all on the way from `TRY_GUARD_MOVE_DOWN`; `TRY_GUARD_MOVE_LEFT` (`7026`): 20; `TRY_GUARD_MOVE_RIGHT` (`70b7`): 8; `MOVE_GUARD` (`6d85`): 0. Tail call `JMP` from `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` (`758c`): 4, (`7591`): 2; from `NUDGE_GUARD_TOWARDS_EXACT_ROW` (`759f`): 0, (`75a4`): 2 | `RTS` (`753d`): 96, 8 of them for the caller of a `NUDGE_*`; tail call `JMP ERASE_SPRITE_AT_PIXEL_COORDS` (`753a`): 0 | partly: the pickup (`7517-753d`) never ran |
| `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` | `7582` | `7595` | `JSR` from `TRY_GUARD_MOVE_DOWN` (`6f69`): 76; `TRY_GUARD_MOVE_UP` (`6edb`): 0; `MOVE_GUARD` (`6d6a`): 0 | `RTS` (`7594`): 70; tail call `JMP CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (`758c`): 4, (`7591`): 2 | yes, whole |
| `NUDGE_GUARD_TOWARDS_EXACT_ROW` | `7595` | `75a8` | `JSR` from `TRY_GUARD_MOVE_LEFT` (`6ff7`): 26; `TRY_GUARD_MOVE_RIGHT` (`7084`): 10 | `RTS` (`75a7`): 34; tail call `JMP CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (`759f`): 0, (`75a4`): 2 | partly: "slightly below" (`759d-75a2`) never ran |
| `SHOULD_GUARD_MOVE_LEFT` | `71a1` | `720b` | `JSR` from `DETERMINE_GUARD_MOVE` (`7198`): 110. Its loop goes back to the entry `71a2` by `JMP SHOULD_GUARD_MOVE_LEFT` (`7208`): 408 | `RTS` at `71a1`, the exit at the door, reached by `BEQ` at `71a6`: 110, to `DETERMINE_GUARD_MOVE` behind `7198` | partly: `7200-7206` (a better distance by way of a ladder: store it) never ran |
| `SHOULD_GUARD_MOVE_RIGHT` | `720b` | `7275` | `JSR` from `DETERMINE_GUARD_MOVE` (`719b`): 110. Its loop goes back to the entry `720c` by `JMP SHOULD_GUARD_MOVE_RIGHT` (`7272`): 850 | `RTS` at `720b`, the exit at the door, reached by `BEQ` at `7210`: 110, to `DETERMINE_GUARD_MOVE` behind `719b` | partly: `726a-7270` (a better distance by way of a ladder: store it) never ran |
| `SHOULD_GUARD_MOVE_UP_OR_DOWN` | `7275` | `72d4` | `JSR` from `DETERMINE_GUARD_MOVE` (`7195`): 110 | `RTS` (`72d3`): 110, to `DETERMINE_GUARD_MOVE` behind `7195` | partly: `72cd-72d3` (choosing "up") never ran |
| `PSEUDO_DISTANCE` | `72d4` | `72fd` | `JSR` from `SHOULD_GUARD_MOVE_LEFT` (`71cd`): 161, (`71f9`): 26; `SHOULD_GUARD_MOVE_RIGHT` (`7237`): 389, (`7263`): 98; `SHOULD_GUARD_MOVE_UP_OR_DOWN` (`729a`): 76, (`72c6`): 70 | `RTS` "player's row, at or right of the guard" (`72e2`): 221; `RTS` "player's row, left of the guard" (`72ea`): 79; `RTS` "a row below the player's" (`72f3`): 0; `RTS` "a row above the player's" (`72fc`): 520 | partly: "a row below the player's" (`72ed-72f4`) never ran |
| `GUARD_FIND_CANDIDATE_ROW_ABOVE` | `72fd` | `739a` | `JSR` from `SHOULD_GUARD_MOVE_LEFT` (`71f4`): 26; `SHOULD_GUARD_MOVE_RIGHT` (`725e`): 98; `SHOULD_GUARD_MOVE_UP_OR_DOWN` (`72c1`): 70. Its loop goes back by `JMP .loop` (`7392`): 392 | `RTS` at `72ff` (`.not_ladder`, the exit at the door, reached by `BNE` at `7314`): 0; `RTS` at `7396` (`.return_Y`): 0; `RTS` at `7399` (`.return_scratch_5C`, reached by `BCC` at `7346`: 133 and at `7388`: 61): 194, to its three callers | partly: `.not_ladder` (`72fd-7300`), the `BEQ`s at `7348` and `738a`, and `.return_Y` (`7395-7397`) never ran |
| `GUARD_FIND_CANDIDATE_ROW_BELOW` | `739a` | `743e` | `JSR` from `SHOULD_GUARD_MOVE_LEFT` (`71c8`): 161; `SHOULD_GUARD_MOVE_RIGHT` (`7232`): 389; `SHOULD_GUARD_MOVE_UP_OR_DOWN` (`7295`): 76. Its loop goes back by `JMP .loop` (`7435`): 1,791 | `RTS` at `739c` (`.return_tmp_row`, the exit at the door, reached by `BEQ` at `73b1`: 626, at `73b5`: 0): 626, to its three callers; `RTS` at `743a` (`.return_max_game_row`): 0; `RTS` at `743d` (`.return_curr_tmp_row`, reached by `BCS` at `73f9` and `742b`): 0 | partly: `7438-743e` never ran |
| `DETERMINE_GUARD_LEFT_RIGHT_LIMITS` | `743e` | `74df` | `JSR` from `DETERMINE_GUARD_MOVE` (`7192`): 110 | `RTS` (`74de`): 110, to `DETERMINE_GUARD_MOVE` behind `7192` | yes, whole |

**Notes**:

- `MOVE_GUARD`: `GUARD_X_ADJ_TABLE` (`6e7f-6e85`) lies within its span; `GUARD_FN_TABLE` (`6e97-6ea1`) lies behind it.
- `MOVE_GUARD`: its only `RTS` is the dispatch. It never returns to its caller itself.
- `MOVE_GUARD`: the local label `.ladder` (`6e85`) does not mean "on a ladder". It means "not falling, not in a hole: choose a move".
- `MOVE_GUARD`: a positive `GUARD_GOLD_TIMER` seems to mean "stuck in a hole, counting down" (set at `6da2`, when the guard lands on a brick); a negative one means "carrying gold". One label for two meanings.
- `STORE_GUARD_DATA`: no `JSR` leads into it. Its `RTS` returns for `MOVE_GUARD`.
- `GUARD_DO_NOTHING`: entered only by branches, from `TRY_GUARD_MOVE_UP`'s "can't go up" tests (row 0, or a brick, stone, trap or guard above). Despite its label, it is not the dispatch's "do nothing": value 0 goes to `STORE_GUARD_DATA` directly.
- `GUARD_DO_NOTHING`: if `GUARD_GOLD_TIMER` is positive, it adds 1, taking back the 1 that `MOVE_GUARD` subtracted (`6cf0`). Read from the code, still to be checked against play: a guard in a hole whose way up is blocked stays in the "climb out" phase and tries again on his next move, while the hole fills on its own timer (`BRICK_FILL_TIMERS`, counted down in `HANDLE_TIMERS`). That would be how a blocked guard gets swallowed by the hole.
- `GUARD_DO_NOTHING` lies right in front of `TRY_GUARD_MOVE_UP` and is the target of `UP`'s "give up early" tests: the exit at the door again, here as a subroutine of its own, not as a local label as at `71a1`.
- `TRY_GUARD_MOVE_UP` and `TRY_GUARD_MOVE_DOWN` reach the tail by the same two doors. A move within the row goes to `TRY_GUARD_MOVE_UP_check_for_gold` (`6f26`); a move into the next row goes to `TRY_GUARD_MOVE_UP_inc_anim_state` (`6f29`) and skips the gold check. The check could not succeed there: `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` returns at once unless both adjustments are 2, and after changing rows the vertical one is 4 (up) or 0 (down). `UP` takes its doors by branch (`BPL` at `6ef3`, `BNE` at `6f24`), `DOWN` by `JMP` (`6fb9`, `6fb6`).
- `TRY_GUARD_MOVE_LEFT` and `TRY_GUARD_MOVE_RIGHT` are mirror images, each with an ending of its own; neither borrows from the other.
- Animation: `GUARD_ANIM_STATE` picks one of 16 pictures from `GUARD_ANIM_SPRITES` (`6ccb`), in groups: running left 0-2, rope left 3-5, falling left 6, running right 7-9, rope right 10-12, falling right 13, climbing 14-15. A move calls `INC_GUARD_ANIM_STATE` with the group's first state in `A` and its last in `X`; it steps to the next state and goes back to the first after the last, like a flip book. `TRY_GUARD_MOVE_UP` and `TRY_GUARD_MOVE_DOWN` both use climbing, 14-15.
- Unconditional branches in a mirror pair: `TRY_GUARD_MOVE_LEFT` sets `GUARD_X_ADJ` to 4 and goes on with `BNE` (`7024`); `TRY_GUARD_MOVE_RIGHT` sets it to 0 and goes on with `BEQ` (`70b5`). Each uses the branch that the value just loaded makes certain.
- `DETERMINE_GUARD_MOVE` is the guard AI, here as a closed box. It answers in one of three ways, each with an `RTS` of its own: "in a hole: up" (the order that `GUARD_DO_NOTHING` deals with when the way up is blocked); "on the player's row with nothing in between: straight at him", right or left; otherwise the answer of its helpers. All its `RTS`s return to `MOVE_GUARD`, right before the dispatch.
- `LOAD_GUARD_DATA` is the mirror of `STORE_GUARD_DATA`: tables to working copy. It starts right behind `STORE_GUARD_DATA`'s `RTS`, without a gap.
- `GUARD_DROP_GOLD`: a guard carrying gold has a negative `GUARD_GOLD_TIMER`, counted up by one each time he enters a new cell. When it reaches 0, he drops the gold if the cell is empty; the drawing is a tail call, `JMP DRAW_SPRITE_AT_PIXEL_COORDS` (`756e`), whose `RTS` returns to `GUARD_DROP_GOLD`'s caller. If the cell is not empty, the timer goes back to -1 and he tries again at the next cell. In the attract play no guard carried gold, so only the first test and the `RTS` ran.
- `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW`: two levels of tail call. `TRY_GUARD_MOVE_DOWN` calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` by `JSR` (`6f69`). If the guard is already on his column, `NUDGE` returns with its own `RTS` (70x). If not, it moves him one step toward the column and jumps to `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (6x), whose `RTS` returns to `TRY_GUARD_MOVE_DOWN` (`6f6c`), not to `NUDGE`. The same pattern as `MOVE_GUARD` and `STORE_GUARD_DATA`, one level down. The gold check follows each nudge because the step may leave the guard exactly on a cell with gold.
- `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`: on pickup, `GUARD_GOLD_TIMER` is set to `$FF - $53` (`751b-7520`). `$53` is `GUARD_RESURRECT_COL`, a counter that `HANDLE_TIMERS` steps through 0 to 27 once per round of the game loop. So the timer starts between -1 and -28, and `GUARD_DROP_GOLD` counts it up once per cell: how far a guard carries gold depends on when he picked it up. A cycling counter used as a cheap random number. Read from the code; the pickup never ran in the attract play.
- A long global label with another subroutine's label as its prefix (`TRY_GUARD_MOVE_UP_check_for_gold`) marks a door from outside: dasm makes a local label (`.check_for_gold`) visible only within its own `SUBROUTINE`, so a label reached from another subroutine has to be global.
- Start and entry: in six places, Xekri's subroutine begins with a local label in front of its entry, used by the "give up early" tests at the top: `67d8`, `689e`, `71a1`, `720b`, `72fd`, `739a` (found by reading; the listing's `SUBROUTINE` marks at these six addresses were then confirmed by a script). The "start" column gives the mark, the answer key does the same (`xekri_start`); the entry is the global label one to three bytes further on. In the pilot, the exit at the door ran at `71a1` (110), `720b` (110) and `739a` (626); at `72fd` it never ran.
- The guard AI's helpers, read from the code: `SHOULD_GUARD_MOVE_LEFT` and `_RIGHT` walk from the limit that `DETERMINE_GUARD_LEFT_RIGHT_LIMITS` found toward the guard's column, one column per round of their loop, and ask at each column what row a guard could reach from there going down (`GUARD_FIND_CANDIDATE_ROW_BELOW`) or, on a ladder, going up (`GUARD_FIND_CANDIDATE_ROW_ABOVE`). `PSEUDO_DISTANCE` rates each candidate row: on the player's row, the column distance; above it, 100 plus the rows between; below it, 200 plus the rows. The smallest rating wins (`BEST_GUARD_DIST`, `GUARD_ACTION`). Their loops go back to their own entry by `JMP` (`7208`, `7272`), and they leave by the exit at the door when the walk reaches the guard's column.
- In the attract play, computed from the counts: `PSEUDO_DISTANCE` never rated a row below the player's (`72f3`: 0), and `SHOULD_GUARD_MOVE_UP_OR_DOWN` never chose "up" (`72cd-72d3` never ran), which fits `TRY_GUARD_MOVE_UP` never being dispatched. `GUARD_FIND_CANDIDATE_ROW_BELOW` always left by the exit at the door (626 of 626), `GUARD_FIND_CANDIDATE_ROW_ABOVE` always by `.return_scratch_5C` (194 of 194).

---

## Part 2: the catalogue of structures

### Entry 1: tail call

Status: explain-back answered (2026-10-15). Part 6 is open. Part 7 has a first idea and, since 2026-10-17, a graded rule (Part 3).

**1. Name**: tail call. Xekri's term, from `main.nw`, "Programming techniques".

**2. What it is**: a subroutine ends with `JMP X` instead of `JSR X` followed by `RTS`. When `X` finishes, its `RTS` goes straight back to whoever called the first subroutine: one return is saved, together with a byte, some time and two bytes of stack.

**3. Xekri's example**: `TRY_GUARD_MOVE_LEFT` ends with `7044 JMP STORE_GUARD_DATA ; tailcall`.

```
MOVE_GUARDS --JSR (6c9b)--> MOVE_GUARD --dispatch (6e96)--> TRY_GUARD_MOVE_LEFT
                                                               |
                                                               JMP STORE_GUARD_DATA (7044)
                                                               v
MOVE_GUARDS <-------------- RTS (75cd) -------------------- STORE_GUARD_DATA
            lands at 6c9e, behind the JSR at 6c9b
```

A second example, two levels deep:

```
TRY_GUARD_MOVE_DOWN --JSR (6f69)--> NUDGE_GUARD_TOWARDS_EXACT_COLUMN
                                       |  not on the column yet:
                                       JMP CHECK_FOR_GOLD_PICKED_UP_BY_GUARD (758c, 7591)
                                       v
                                    CHECK_FOR_GOLD_PICKED_UP_BY_GUARD
                                       |  no gold here: RTS (753d)  -------------------+
                                       |  gold picked up:                              |
                                       JMP ERASE_SPRITE_AT_PIXEL_COORDS (753a)         |
                                       v                                               |
                                    ERASE_SPRITE_AT_PIXEL_COORDS                       |
                                          RTS  ---------------------------------------+
                                                                                       v
TRY_GUARD_MOVE_DOWN <---------------------------------------------- lands at 6f6c, behind the JSR
```

**4. How it shows in a run** (`lr_split_transitions.csv`):

- `7044,7044,$4C,,75a8,26`: the `JMP` into `STORE_GUARD_DATA`.
- `75a8,75cd,$60,,6c9e,112`: `STORE_GUARD_DATA`'s `RTS` lands behind the `JSR` at `6c9b`, in `MOVE_GUARDS`, not in any of the subroutines that jumped to it.
- `6f69,6f69,$20,,7582,76`, then `758a,758c,$4C,,74f7,4`, then `753d,753d,$60,,6f6c,6`: the two-level example. The `RTS` of `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` lands behind `TRY_GUARD_MOVE_DOWN`'s `JSR` into `NUDGE_GUARD_TOWARDS_EXACT_COLUMN`. The jump into `ERASE_SPRITE_AT_PIXEL_COORDS` did not run.

**5. What `papple2` does with it today**: if the target of the `JMP` is also called by `JSR` somewhere, it is an entry, and the `JMP` shows as a blue arrow between two routines: `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW` into `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` ("JMP 6" and "JMP 2" into `routine_74f7`). If it never is, the target is no entry and is absorbed into every routine that jumps there: `STORE_GUARD_DATA` is part of `routine_6f39`, `routine_6fbc` and `routine_7047` at once (`docs/structures_handover.md`, "E", removed in `1adc920`). The docs call every blue `JMP` arrow a tail call, which claims more than the code checks. In the whole run (computed, Part 3), the tail calls into code nobody calls by `JSR` that `find_routines()` absorbs are: `STORE_GUARD_DATA` (3 jumpers), `TRY_MOVING_LEFT` (`JMP` at `65c8`, from `MOVE_PLAYER`), `CHECK_FOR_MODE_1_INPUT` (a tail call by branch: `BEQ` at `6a16`, from `CHECK_FOR_INPUT`), and the top-level chain of entry 6.

**6. What I want to see**: to be decided, after discussing the alternatives. Candidates:

- **A. In the routine graph**: the target as a routine of its own (`STORE_GUARD_DATA`), with the tail calls as arrows into it. Needs a rule that makes it an entry (part 7).
- **B. In the listing**: at each tail call, a note saying where its `RTS` will return, e.g. "returns to the caller of `MOVE_GUARD`".
- **C. In a report**: a table of tail calls: site, target, how often, and where the target's `RTS` returned.
- **D. Nothing of its own**: tail calls only matter as far as they make the routines right.

**7. A rule in words**: a first idea (2026-10-15), not graded: a `JMP` is a tail call if the `RTS` that ends the code at its target returns to the caller of the subroutine the `JMP` lies in. The run can check this: the stack tracking knows which `JSR` an `RTS` returns for. Known problem: a `JMP` back to the start of its own loop (`SHOULD_GUARD_MOVE_LEFT`, `7208`) also ends in an `RTS` that returns to its caller, and must not count. See appendix A, "A jump upward past the subroutine's own entry". Graded rule (2026-10-17): parts 5, 6 and 7 of the rule in Part 3 make the targets of tail calls entries without the stack tracking: an edge into another routine's range is not followed, a target nobody else takes in becomes an entry (`STORE_GUARD_DATA`, `CHECK_FOR_MODE_1_INPUT`), and a `JMP` target right behind a block that ended in `RTS` becomes an entry (`TRY_MOVING_LEFT`).

**8. Explain-back**: `TRY_GUARD_MOVE_DOWN` calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` with `JSR`; `NUDGE` jumps to `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`. Whose `RTS` brings control back to `TRY_GUARD_MOVE_DOWN`, and why not `NUDGE`'s? Answer (2026-10-15): `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`'s, because `NUDGE` jumped there instead of calling it; and on the pickup path `ERASE_SPRITE_AT_PIXEL_COORDS`'s, because `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` ends in a tail call of its own there.

### Entry 2: jump into the middle of another subroutine

Status: written 2026-10-17. Part 6 lists alternatives, no decision. Explain-back open.

**1. Name**: jump into the middle of another subroutine.

**2. What it is**: a `JMP` (or a branch) that lands not at the entry of another Xekri subroutine but at a door further inside it, to reuse that subroutine's ending. Unlike a tail call, the target is no subroutine's start, and the subroutine it belongs to may never be entered at its start at all.

**3. Xekri's example**: `TRY_GUARD_MOVE_DOWN` ends with `6fb6 JMP TRY_GUARD_MOVE_UP_inc_anim_state` and `6fb9 JMP TRY_GUARD_MOVE_UP_check_for_gold`, two doors into `TRY_GUARD_MOVE_UP`'s tail (`6f26-6f39`). Two more that ran:

- `MOVE_PLAYER` (`64bd`), when the player is already digging left: `64c7 JMP TRY_DIGGING_LEFT_check_can_dig_left` (`67e7`), past `TRY_DIGGING_LEFT`'s entry `67db`.
- `MAIN` (`5f7d`): `5fa3 JMP CHECK_FOR_BUTTON_DOWN` (`619b`), a global label in the middle of `LONG_DELAY`, past its first lines (`JSR WAIT_KEY`, the counters).

```
TRY_GUARD_MOVE_UP (6eac) ................. never entered at 6eac in the attract play
  ...
  6f26 TRY_GUARD_MOVE_UP_check_for_gold  <--JMP (6fb9) 60x-- TRY_GUARD_MOVE_DOWN
       JSR CHECK_FOR_GOLD_PICKED_UP_BY_GUARD
  6f29 TRY_GUARD_MOVE_UP_inc_anim_state  <--JMP (6fb6) 16x-- TRY_GUARD_MOVE_DOWN
       JSR INC_GUARD_ANIM_STATE / JSR GET_GUARD_SPRITE_AND_COORDS / JSR DRAW_SPRITE_AT_PIXEL_COORDS
  6f36 JMP STORE_GUARD_DATA  ------------------------------------------> 76x
```

**4. How it shows in a run** (`lr_split_transitions.csv`):

- `6fb9,6fb9,$4C,,6f26,60` and `6fae,6fb6,$4C,,6f29,16`: the two doors into `TRY_GUARD_MOVE_UP`.
- `6f26,6f26,$20,,74f7,60` and `753d,753d,$60,,6f29,60`: the door at `6f26` falls into the one at `6f29` by its call's return.
- `64c7,64c7,$4C,,67e7,6` and `67db,,,glide,67e7,1`: `67e7` is reached both from `MOVE_PLAYER` (6x) and from `TRY_DIGGING_LEFT`'s own start (1x).
- `5f9a,5fa3,$4C,,619b,1`: the door into `LONG_DELAY`.

**5. What `papple2` does with it today**: the door is no entry (nobody `JSR`s there), so it is followed as if it were inside the jumping routine. `TRY_GUARD_MOVE_UP`'s tail (5 blocks) is part of `routine_6f39`; the 23 blocks of `TRY_DIGGING_LEFT` from `67e7` on are part of both `routine_64bd` and `routine_67db`; `LONG_DELAY`'s 10 blocks are part of `routine_0800` (computed, Part 3).

**6. What I want to see**: to be decided. Alternatives:

- **A. In the routine graph**: the code behind the door as a routine of its own, named after the Xekri subroutine whose span it lies within (`TRY_GUARD_MOVE_UP`), even if its start never ran; the doors as arrows into it, drawn differently from tail calls.
- **B. In the listing**: at the target, a mark "door into `TRY_GUARD_MOVE_UP`, from `6fb6`, `6fb9`", and at the jump, "into the middle of ...".
- **C. In a report**: a table of doors: door address, the subroutine it lies in, who jumps there, how often, and whether that subroutine's entry ran at all.
- **D. In the routine graph, as part of the routine whose range holds it**: `67e7` simply belongs to `TRY_DIGGING_LEFT`, and `MOVE_PLAYER` gets an arrow into it.

**7. A rule in words**: part 5 and part 6 of the rule in Part 3. A routine follows edges only within its range (its entry up to the next entry). A `JMP` or branch to a block beyond that range is not followed; if another routine takes that block in, it is a door into that routine (`67e7` into `TRY_DIGGING_LEFT`); if no routine does, the lowest such block starts a routine of its own, and the doors above it in the same range join it (`6f26` becomes an entry, `6f29` joins it). Graded in Part 3: `TRY_GUARD_MOVE_UP`, `TRY_DIGGING_LEFT` and `LONG_DELAY` agree with the answer key under that rule.

**8. Explain-back** (open): in the attract play, `TRY_GUARD_MOVE_UP`'s entry `6eac` never ran, yet five of its blocks did. Which `RTS` ends the work those five blocks start, and why does the rule of Part 3 make `6f26` an entry but not `6f29`?

### Entry 3: dispatch by `RTS`

Status: written 2026-10-17. Part 6 lists alternatives, no decision. Explain-back open.

**1. Name**: dispatch by `RTS` (see Terms).

**2. What it is**: a subroutine chooses where to go next by pushing an address from a table onto the stack and executing `RTS`. The `RTS` "returns" to the pushed address. Because `RTS` adds 1 to the address it pops, the table holds each target minus 1. It is a computed jump: the 6502 has `JMP (addr)`, but no jump through a table indexed by a register.

**3. Xekri's example**: `MOVE_GUARD`, `6e85-6e97`:

```
6e89  JSR DETERMINE_GUARD_MOVE      ; A = 0 to 4
6e8c  ASL                           ; A * 2: two bytes per table entry
6e8d  TAY
6e8e  LDA GUARD_FN_TABLE+1,Y        ; high byte
6e91  PHA
6e92  LDA GUARD_FN_TABLE,Y          ; low byte
6e95  PHA
6e96  RTS                           ; "returns" to the table entry + 1

GUARD_FN_TABLE (6e97): STORE_GUARD_DATA-1, TRY_GUARD_MOVE_LEFT-1, TRY_GUARD_MOVE_RIGHT-1,
                       TRY_GUARD_MOVE_UP-1, TRY_GUARD_MOVE_DOWN-1
```

Read from the listing, never ran in the attract play: the same pattern in `CHECK_FOR_INPUT` (`6a40-6a48`, `CTRL_KEY_HANDLERS`), `EDITOR_COMMAND_LOOP` (`7c44-7c4c`, `EDITOR_ROUTINE_ADDRESS`) and `EDIT_LEVEL` (`7f65-7f6d`, `LEVEL_EDIT_KEY_FUNCTIONS`).

**4. How it shows in a run**: `6e8c,6e96,$60,,6f39,76`, `6e8c,6e96,$60,,6fbc,26`, `6e8c,6e96,$60,,7047,10`. No row leads to `STORE_GUARD_DATA` (value 0) or `TRY_GUARD_MOVE_UP` (value 3): those values never came. The table itself never shows: it is read as data, not run.

**5. What `papple2` does with it today**: `stack_jumps()` finds the three `RTS` rows (the shadow stack found no frame there, and the target is not behind a `JSR`), `find_routines()` makes their targets entries, and `routine_exits()` draws them as "stack jump" arrows. This is the one structure `papple2` already gets right. But `stack_jumps()` also counts the two returns behind a payload (see "Met while grading" below), which are no dispatch.

**6. What I want to see**: to be decided. Alternatives:

- **A. In the routine graph**: a dispatch node at `6e96`, with one arrow per target, labelled with the table index and the count.
- **B. In the listing**: at the `RTS`, the name of the table and the targets that ran, with counts; at the table, each entry with its target's label (target minus 1 resolved).
- **C. In a report**: a table of dispatch sites: site, table, targets that ran, counts.
- **D. Static candidates**: the table entries whose targets never ran (here `STORE_GUARD_DATA`, `TRY_GUARD_MOVE_UP`), listed as known but unseen entries, marked as static.

**7. A rule in words**: an `RTS` is a dispatch if the shadow stack found no frame for it (the address was pushed by code, not by a `JSR`) and its target does not lie behind a `JSR`. Its target is an entry. An `RTS` whose frame does belong to a `JSR` but that lands further on is no dispatch but a return behind a payload (part 2 of the rule in Part 3). Today's `stack_jumps()` accepts "unmatched" and "redirected" alike; the difference between the two is what separates the two cases. Not checked here: `lr_returns.csv` is not in the dump, so which outcome the shadow stack gave each of the five rows is unknown.

**8. Explain-back** (open): `GUARD_FN_TABLE` stores `STORE_GUARD_DATA-1`, not `STORE_GUARD_DATA`. Why the minus 1, and why could the attract play not tell us that value 0 leads to `STORE_GUARD_DATA`?

### Entry 4: one subroutine with two doors

Status: written 2026-10-17. Part 6 lists alternatives, no decision. Explain-back open.

**1. Name**: one subroutine with two doors.

**2. What it is**: one body of code with two (or more) places that callers enter by `JSR`. Each door does a little setup of its own and then joins the shared body, by falling through or by a short branch.

**3. Xekri's example**: `SOUND_DELAY` (`86b1`), one Xekri subroutine with two doors:

```
86b1 SOUND_DELAY      LDA SOUND_DELAY_AMOUNTS,X   ; door 1: X = index into the table
86b4                  TAX
86b5 SOUND_DELAY1     LDY #$B4                    ; door 2: X = count already
     .loop            DEY / BNE .loop / DEX / BNE SOUND_DELAY1
86bd                  RTS
```

`PLAY_SOUND` calls both: `JSR SOUND_DELAY` at `8846`, `JSR SOUND_DELAY1` at `882d`.

A second shape, with the doors as separate Xekri subroutines: `DRAW_SPRITE_PAGE1` (`82aa`) does `STA SPRITE_NUM / LDA #$20 / BNE DRAW_SPRITE`; `DRAW_SPRITE_PAGE2` (`82b0`) does `STA SPRITE_NUM / LDA #$40` and falls into `DRAW_SPRITE` (`82b4`). The handover says Xekri makes all three separate subroutines; the listing has `SUBROUTINE` marks only at `82aa` and `82b0` (computed), so `DRAW_SPRITE` lies within `DRAW_SPRITE_PAGE2`'s span, and `DRAW_SPRITE_PAGE1`'s `BNE` is a door into it. `CLEAR_HGR1` (`7a51`), `CLEAR_HGR2` (`7a57`) and `CLEAR_PAGE` (`7a5b`) have the same shape and the same marks.

**4. How it shows in a run**:

- `8844,8846,$20,,86b1,156`, `882c,882d,$20,,86b5,10` and `86b1,,,glide,86b5,156`: two `JSR` targets, one gliding into the other.
- `82aa,82ae,$D0,taken,82b4,61` and `82b0,,,glide,82b4,453`: one door branches in, the other falls in.
- `7a51,7a55,$D0,taken,7a5b,1` and `7a57,,,glide,7a5b,1`: the same for the clearing of the two pages.

**5. What `papple2` does with it today**: both doors of `SOUND_DELAY` are `JSR` targets, so `find_routines()` makes two routines: `routine_86b1` (1 block) and `routine_86b5` (4 blocks), and does not follow the glide between them. In the other shape the shared body is no entry, so it is part of both routines: `DRAW_SPRITE`'s 10 blocks lie in `routine_82aa` and `routine_82b0`, `CLEAR_PAGE`'s 4 blocks in `routine_7a51` and `routine_7a57` (computed, Part 3).

**6. What I want to see**: to be decided. Alternatives:

- **A. One routine with two doors**: the routine lists both entries, and callers of either door point to it.
- **B. Follow Xekri's marks**: `SOUND_DELAY` one routine; `DRAW_SPRITE_PAGE1` a short routine of its own that branches into `DRAW_SPRITE_PAGE2`.
- **C. Three routines**: each door a routine of its own, and the shared body a third, which both enter.
- **D. In the listing**: a mark at each door ("door 2 of `SOUND_DELAY`"), whatever the routines are.

**7. A rule in words**: parts 4 and 5 of the rule in Part 3. Falling through never leaves a routine: if a block glides into another routine's entry, that entry is a second door of the routine it glides from (`86b5` joins `86b1`). A branch into the next routine's range is not followed (`82ae` into `82b4`). Graded in Part 3: `SOUND_DELAY`, `DRAW_SPRITE_PAGE1`, `DRAW_SPRITE_PAGE2`, `CLEAR_HGR1` and `CLEAR_HGR2` agree with the answer key under that rule. Note: alternative B is what the answer key asks for; whether that is what is wanted is part 6's question.

**8. Explain-back** (open): `DRAW_SPRITE_PAGE1` ends with `BNE DRAW_SPRITE` right after `LDA #$20`. Why does that branch always jump, and why might Doug have used a `BNE` there rather than a `JMP`?

### Entry 5: fall-through into the next subroutine

Status: written 2026-10-17. Part 6 lists alternatives, no decision. Explain-back open.

**1. Name**: fall-through into the next subroutine.

**2. What it is**: a subroutine has no `RTS` or `JMP` at its end and runs straight into the next one in memory, which Xekri marks as a subroutine of its own. The next one is also entered from elsewhere; otherwise it would be no subroutine of its own.

**3. Xekri's example**: the one the handover names, "Fallthrough to RESET_GAME" at `6008` (from the code at `6000`), never ran in the attract play; nor did `UNUSED` falling into `MAIN` (`5f7d`). The one that ran:

```
7a70 PUT_STATUS_LIVES   SUBROUTINE   LDA LIVES / LDX #16
                                     ; fallthrough
7a74 PUT_STATUS_BYTE    SUBROUTINE   STX GAME_COLNUM / JSR TO_DECIMAL3 / ... / JMP PUT_DIGIT
7a8c PUT_STATUS_LEVEL   SUBROUTINE   LDA LEVELNUM / LDX #25 / BNE PUT_STATUS_BYTE
```

**4. How it shows in a run**: `7a70,,,glide,7a74,2` (the fall-through) and `7a8c,7a90,$D0,taken,7a74,2` (the second way in). `PUT_STATUS_LIVES` and `PUT_STATUS_LEVEL` are each called by `JSR` twice (`7a25`, `88bd` and `7a28`, `88c8`).

**5. What `papple2` does with it today**: nobody `JSR`s `PUT_STATUS_BYTE`, so it is no entry, and its 4 blocks are part of both `routine_7a70` and `routine_7a8c` (computed, Part 3).

**6. What I want to see**: to be decided. Alternatives:

- **A. Follow Xekri's marks**: `PUT_STATUS_BYTE` a routine of its own, entered by a fall-through and by a branch.
- **B. Like two doors (entry 4)**: the body belongs to the routine that falls into it (`PUT_STATUS_LIVES`), and the other enters it by a door. That is what a run can tell; the marks are Xekri's (or Doug's) way of naming.
- **C. A routine of its own whenever the shared code has a way in other than falling through**: matches here, but would also make `DRAW_SPRITE` and `CLEAR_PAGE` routines of their own, against Xekri's marks (computed on paper from the rows in entry 4).
- **D. Show the choice**: whatever the routines are, mark a fall-through between two Xekri subroutines in the listing ("falls into `PUT_STATUS_BYTE`").

**7. A rule in words**: the run cannot tell entry 5 from entry 4: in both, one way in falls through and another branches or jumps in. `DRAW_SPRITE_PAGE2` into `DRAW_SPRITE` and `PUT_STATUS_LIVES` into `PUT_STATUS_BYTE` look the same in the reports; only Xekri's marks differ. So any rule gets one of the two wrong. The rule in Part 3 treats both as entry 4 (falling through never leaves a routine), which leaves `PUT_STATUS_LIVES` and `PUT_STATUS_BYTE` as its only disagreement.

**8. Explain-back** (open): `PUT_STATUS_LIVES` and `PUT_STATUS_LEVEL` both end up in `PUT_STATUS_BYTE`. Which of them gets there without any jump, and what does each leave in `A` and `X` for `PUT_STATUS_BYTE` to use?

### Entry 6: code that runs once and is overwritten

Status: written 2026-10-17. Part 6 lists alternatives, no decision. Explain-back open.

**1. Name**: code that runs once and is overwritten.

**2. What it is**: start-up code that runs once, before the game is in place: it moves the program to where it will run, sets the machine up, and jumps on. It is never called and never returns; it runs as a chain of `JMP`s. Part of it runs at an address where its bytes do not stay: the loader moves them, or later code writes over them.

**3. Xekri's example**: read from the listing.

```
0800  JMP $2800            ; at the load address; 0800-1FFF is overwritten later by RELOCATE1
2800  RELOCATE0_ALIAS      ; listed at 5f00: the same bytes, before they are moved (+3700)
      copies 0800-88FF to 3F00-BFFF (129 pages), itself included
282f  JMP RELOCATE1        ; to 5f32: from the old copy into the new one
5f32  RELOCATE1            ; copies the segments in RELOCATE_TABLE, by rewriting its own operands
5f66  JMP MAIN
5f7d  MAIN                 ; soft switches, LDX #$07 / TXS (a new stack)
5fa3  JMP CHECK_FOR_BUTTON_DOWN   ; into LONG_DELAY (entry 2)
61cd  JMP INIT_GAME_DATA   ; from LONG_DELAY, when it times out
```

`RELOCATE_TABLE` (`5fa7`) holds four segments: `3f00-46ff` to `0000`, `4700-5eff` to `0800`, and two that copy onto themselves (`6000-8dff`, `8e00-bfff`); read, purpose of the last two not understood. The bytes at `2800` lie in hi-res page 1 (`2000-3fff`), which `CLEAR_HGR1` fills later: the loop at `7a64` ran 16,384 times, two pages of 8,192 bytes (computed from the count; that `2800` was overwritten is read, not checked by a run).

**4. How it shows in a run**: `0800,0800,$4C,,2800,1`; `2821,2826,$D0,taken,2821,32895` (the first copy loop); `282f,282f,$4C,,5f32,1`; `5f4b,5f52,$D0,taken,5f4b,32640` (the second); `5f66,5f66,$4C,,5f7d,1`; `5f9a,5fa3,$4C,,619b,1`; `61bc,61cd,$4C,,6056,1`. Every jump in the chain runs once, and no `JSR` leads into any of it.

**5. What `papple2` does with it today**: all of it is one routine, `routine_0800`: the loader block, both relocations, `MAIN`, `LONG_DELAY` and `INIT_GAME_DATA` with the game loop, 40 blocks, span `0800-61d0`, 22,992 bytes (`lr_overview.txt`). The blocks at `2800-2832` carry their load addresses, so Xekri's labels at `5f00-5f32` do not match them. About 263,000 of the run's 4,000,000 instructions are spent in the two copy loops (the snapshot after relocation is parked in `TODO.md`).

**6. What I want to see**: to be decided. Alternatives:

- **A. Each top-level `JMP` starts a routine**: `RELOCATE0_ALIAS`, `RELOCATE1`, `MAIN`, `LONG_DELAY`, `INIT_GAME_DATA` as routines of their own, chained by arrows.
- **B. An alias mapping**: show the blocks at `2800-2832` with Xekri's labels at `+3700`, marked as run before relocation.
- **C. A start-up phase**: everything before the first `JSR` (or before relocation is done) shown apart from the game's routines, or left out by starting from the snapshot after relocation.
- **D. Mark overwritten code**: code that ran at an address that was later written to (the cross reference sees those writes), flagged in the listing.

**7. A rule in words**: part 3 of the rule in Part 3: a `JMP` taken while no call is open starts a routine at its target. The run can see this: the shadow stack holds no frame. In this run it gives exactly `2800`, `5f32`, `5f7d`, `619b` and `6056`, and all five units agree with the answer key. Risk (read): a top-level `JMP` that stays inside its unit, like `613c JMP .start_game` in `INIT_GAME_DATA` (never ran), would split that unit in a longer run. The alias is not part of the rule; the answer key handles it by hand (see "The answer key").

**8. Explain-back** (open): `RELOCATE0_ALIAS` is listed at `5f00`, but the run executed it at `2800`. Where do the `3700` bytes of difference come from, and which instruction moves control from the old copy of the code to the new one?

### Met while grading: the return behind a payload

Not one of the six structures of the handover; it decides two disagreements in Part 3, so it is noted here in short. `CHECK_FOR_GOLD_PICKED_UP_BY_PLAYER` does `6be3 JSR LOAD_SOUND_DATA` followed by 13 bytes of sound data (`6be6-6bf2`); `LOAD_SOUND_DATA` reads them through its return address and returns to `6bf3` (`880a,8810,$60,,6bf3,1`). `PUT_STATUS` does `7a05 JSR PUT_STRING` followed by the string (`7a08-7a24`), and `PUT_STRING` returns to `7a25` (`86f9,86ff,$60,,7a25,1`). `stack_jumps()` counts both as stack jumps, so `find_routines()` cuts both subroutines in two (see appendix D, "Returns behind a payload are counted as stack jumps"). Part 2 of the rule in Part 3 turns each into a return.

---

## Part 3: `find_routines()` graded, and a rule

### How it was graded

- **Computed** by throwaway scripts (not deliverables): `find_routines()` was rewritten from `src/papple2/workbench/basic_blocks_analysis.py` as it is in the dump and run on `lr_split_tiles.csv` and `lr_split_transitions.csv`. The rewrite reproduces `lr_overview.txt` exactly: 73 routines, each with the same number of blocks.
- **Approximated**: `stack_jumps()` needs `lr_returns.csv`, which is not in the dump. The script used only its second test: an `RTS` whose target does not lie right behind a `JSR` that ran. It finds five: the three dispatch rows and the two returns behind a payload. Since the routines match `lr_overview.txt`, these are the extra entries `papple2` used.
- **Partition**: does every block that ran belong to exactly one routine? **Agreement**: for each unit of the answer key, is there one routine whose blocks are exactly the unit's blocks? A unit can agree while its blocks also lie in another routine; partition catches that.

### `find_routines()` today

**Partition** (computed): 642 blocks, 0 in no routine, 42 in more than one:

| blocks | Xekri unit | routines | structure |
|---|---|---|---|
| 23 (`67e7-686e`) | `TRY_DIGGING_LEFT` | `routine_64bd`, `routine_67db` | entry 2: `MOVE_PLAYER` jumps to `67e7` |
| 10 (`82b4-8328`) | `DRAW_SPRITE_PAGE2` | `routine_82aa`, `routine_82b0` | entry 4: `DRAW_SPRITE` |
| 4 (`7a5b-7a70`) | `CLEAR_HGR2` | `routine_7a51`, `routine_7a57` | entry 4: `CLEAR_PAGE` |
| 4 (`7a74-7a8c`) | `PUT_STATUS_BYTE` | `routine_7a70`, `routine_7a8c` | entry 5 |
| 1 (`75a8-75ce`) | `STORE_GUARD_DATA` | `routine_6f39`, `routine_6fbc`, `routine_7047` | entry 1 |

**Agreement** (computed): 57 of the 79 units agree. The loader block at `0800` lies in `routine_0800` with 39 other blocks. The 22 that disagree:

| Xekri unit | what `find_routines()` makes of it | structure |
|---|---|---|
| `RELOCATE0_ALIAS`, `RELOCATE1`, `MAIN`, `INIT_GAME_DATA`, `LONG_DELAY` | all five inside `routine_0800`, with the loader block | entry 6; `619b` also entry 2 |
| `MOVE_PLAYER` | `routine_64bd` also holds `TRY_MOVING_LEFT` and 23 blocks of `TRY_DIGGING_LEFT` | entries 1 and 2 |
| `TRY_MOVING_LEFT` | absorbed into `routine_64bd` (`JMP` at `65c8`) | entry 1 |
| `CHECK_FOR_INPUT`, `CHECK_FOR_MODE_1_INPUT` | one routine, `routine_6a12` (`BEQ` at `6a16`) | entry 1, by branch |
| `CHECK_FOR_GOLD_PICKED_UP_BY_PLAYER` | cut in two: `routine_6b9d` and `routine_6bf3` | return behind a payload |
| `PUT_STATUS` | cut in two: `routine_79ad` and `routine_7a25` | return behind a payload |
| `TRY_GUARD_MOVE_UP` | its tail lies in `routine_6f39` | entry 2 |
| `TRY_GUARD_MOVE_DOWN` | `routine_6f39` also holds `UP`'s tail and `STORE_GUARD_DATA` | entries 1 and 2 |
| `TRY_GUARD_MOVE_LEFT`, `TRY_GUARD_MOVE_RIGHT` | each routine also holds `STORE_GUARD_DATA` | entry 1 |
| `STORE_GUARD_DATA` | no routine of its own, part of three | entry 1 |
| `CLEAR_HGR1`, `DRAW_SPRITE_PAGE1` | each routine also holds the shared body | entry 4 |
| `PUT_STATUS_LIVES`, `PUT_STATUS_LEVEL`, `PUT_STATUS_BYTE` | each of the two routines holds `PUT_STATUS_BYTE`; no routine of its own | entry 5 |
| `SOUND_DELAY` | cut in two: `routine_86b1` and `routine_86b5` | entry 4 |

### A rule for routines

It uses only what a run can see: the blocks, the edges with their kinds and counts, the shadow stack, and the blocks' addresses. Seven parts:

1. **Entries**: the run's start, every `JSR` target, and every target of a dispatch by `RTS` (entry 3).
2. **Returns behind a payload**: an `RTS` that the shadow stack matches to the frame of a `JSR`, but that lands further on than 3 bytes behind it, is a return. Its target is no entry; the `JSR`'s block gets an edge to it, like the edge from a call to the code behind it.
3. **Top level**: a `JMP` taken while no call is open starts a routine at its target (entry 6).
4. **Falling through never leaves a routine**: if a block glides into another routine's entry, that entry is a second door of the routine it glides from, not a routine of its own (entry 4).
5. **Range**: a routine follows edges only to blocks between its entry and the next entry above it. One exception, the exit at the door: a branch back to the block that ends right at the routine's entry is followed.
6. **Orphans**: a block that an edge leads to but that no routine takes in starts a routine. The lowest such block first, then everything is computed again, until there are none.
7. **Behind a return**: the target of a `JMP` that lies right behind a block that ran and ended in `RTS`, and that is never fallen into, starts a routine (entry 1, into the code right behind).

Part 7 needs no shadow stack and catches the one tail call that part 5 cannot see: `MOVE_PLAYER`'s `JMP` to `TRY_MOVING_LEFT` (`65d3`) stays within `MOVE_PLAYER`'s range, because no entry lies between them; but the block `65d2-65d3` (`MOVE_PLAYER`'s `RTS` at `.end`) ran, and ends right at the target.

### The rule graded

**Computed** by a throwaway script that applies the seven parts to the two split reports. Part 2 is approximated without `lr_returns.csv`: an `RTS` that does not land behind a `JSR` counts as a return behind a payload if no block ran between the 3 bytes behind the nearest `JSR` below its target and the target. That gives the two payload returns and not the dispatch.

- **Partition**: 79 routines; every one of the 642 blocks lies in exactly one.
- **Agreement**: 77 of the 79 units agree; the loader block at `0800` is a routine of its own (`0800`) and so agrees as well.
- **Entries beyond `find_routines()`'s**: `2800`, `5f32`, `5f7d`, `619b`, `6056` (part 3), `65d3` (part 7), `69b8`, `6f26` (part 6) and `75a8` (parts 6 and 7). Gone: `6bf3`, `7a25` (part 2) and `86b5` (part 4).

What each part contributes, computed by leaving it out and grading again:

| left out | routines | blocks in more than one | blocks in none | units that agree, of 80 (the 79 units and `0800`) |
|---|---|---|---|---|
| nothing | 79 | 0 | 0 | 78 |
| 2, payload | 81 | 0 | 0 | 76 |
| 3, top level | 74 | 0 | 0 | 72 |
| 4, falling through | 80 | 0 | 0 | 77 |
| 5, range | 77 | 41 | 0 | 70 |
| 5's exception, the exit at the door | 83 | 0 | 0 | 74 |
| 6, orphans | 77 | 0 | 12 | 76 |
| 7, behind a return | 78 | 0 | 0 | 76 |

**Where it still disagrees**: `PUT_STATUS_LIVES` and `PUT_STATUS_BYTE`. Under part 4, `PUT_STATUS_LIVES` falls into `PUT_STATUS_BYTE`, so they become one routine (`7a70`, 5 blocks), while Xekri marks two subroutines. The run cannot tell this fall-through (entry 5) from a second door (entry 4, `DRAW_SPRITE`); see entry 5, part 7. `PUT_STATUS_LEVEL` agrees: its branch into `PUT_STATUS_BYTE` is not followed (part 5).

### Caveats

- **One run, no hold-out**: the rule was built while looking at this run and graded on the same run. Parts 3 and 7 are each backed by one family of cases. A second run (a longer attract play, or real play) is needed before trusting it.
- **Known risks**, read from the listing: part 3 would split `INIT_GAME_DATA` at `609f` if `613c JMP .start_game` ever runs at top level. Part 7 would split a routine at a loop head that lies right behind one of its own `RTS` blocks and is reached only by `JMP`. Part 5 depends on the entries: a routine whose range holds a second, unknown subroutine absorbs it (that is how `TRY_MOVING_LEFT` needed part 7).
- **Approximations**: part 2 and the stack jumps were computed without `lr_returns.csv`. In `papple2`, part 2 should use the shadow stack's outcome (a frame that belongs to a `JSR` but a different target), not the "no block in between" test used here.
- **What the answer key decides**: the agreement numbers count the choices made in "The answer key": unmarked units, the alias of `RELOCATE0_ALIAS`, the loader block. Other choices would change the counts for those six units.

---

## Appendix A: open questions

- **A jump upward past the subroutine's own entry** is a signal that the code leaves into someone else's, but not proof. `TRY_GUARD_MOVE_DOWN` jumps up into `TRY_GUARD_MOVE_UP`'s tail (`6fb6`, `6fb9`); `SHOULD_GUARD_MOVE_LEFT` branches up to its own exit (`71a6` -> `71a1`). A rule in Part 3 has to tell the two apart. (2026-10-17: the rule in Part 3 tells them apart by part 5 and its exception: a branch back to the block that ends right at the entry is followed, any other edge out of the range is not. Graded on one run only.)
- **`GUARD_DO_NOTHING`'s timer fix-up**: does the reading in the notes of Part 1 match what is seen in play?
- **Not yet understood: the adjustments and the nudging.** How `GUARD_X_ADJ` and `GUARD_Y_ADJ` (0 to 4, 2 = exactly on the cell) place a guard between cells, and why moving in one direction nudges him toward the middle of the other. Booked as "too difficult, yet"; a picture of one cell with its five positions would be the place to start.
- **Fall-through or two doors** (2026-10-17): `PUT_STATUS_LIVES` into `PUT_STATUS_BYTE` and `DRAW_SPRITE_PAGE2` into `DRAW_SPRITE` look the same in a run; Xekri marks them differently. Should `papple2` follow the marks where it has them, or what a run can tell? (Entry 5, part 6.)
- **The two self-copying segments of `RELOCATE_TABLE`** (2026-10-17): `6000-8dff` and `8e00-bfff` are copied onto themselves. Why?
- **Which outcome the shadow stack gives the five stack jumps** (2026-10-17): "unmatched" for the dispatch and "redirected" for the payload returns is the assumption of Part 3, part 2; `lr_returns.csv` would settle it.

---

## Appendix B: traces of how the code was written

Findings that may say something about how Doug wrote the code, not about what it does. Candidates for Xekri's documentation (`a2-lode-runner`). None of them is a message from Doug to the reader: they may be left over from his development process.

- **The exit at the door**: in six places, the target of a subroutine's "give up early" tests sits right in front of its entry (`67d8`, `689e`, `71a1`, `720b`, `72fd`, `739a`), and in one more it is a subroutine of its own (`GUARD_DO_NOTHING`, `6ea1`). The byte before the entry is the closest spot to those tests. Branches reach at most 128 bytes back and 127 forward, so placing the exit there from the start keeps it in reach however long the subroutine grows. In the two digging cases it was needed: `.stop_digging` (`6892`) is 165 bytes from the `BCS` at `67eb`.
- **A branch to a `JMP` where the branch alone would reach**: in `TRY_GUARD_MOVE_DOWN`, `BCC .check_for_gold` (`6f85`) leads to `JMP TRY_GUARD_MOVE_UP_check_for_gold` (`6fb9`), but the `BCC` ends at `6f87`, only 97 bytes behind `6f26`. In `TRY_MOVING_DOWN`, `BCC .check_for_gold_` (`67ac`) leads to `JMP TRY_MOVING_UP_check_for_gold` (`67d5`), but the `BCC` ends at `67ae`, only 87 bytes behind `6757` (both computed by hand). So these are no stretchy branches as far as reach goes. Perhaps they were, in an earlier version of the code.
- **Player code and guard code with the same shape**: `TRY_MOVING_DOWN` and `TRY_GUARD_MOVE_DOWN`, compared side by side by reading: the same steps in the same order, and both borrow the tail of their `UP` by the same two doors. The guard version adds a test for a guard below, `GUARD_DROP_GOLD` and the test whether the player is killed; it leaves by `JMP STORE_GUARD_DATA` instead of `SEC` / `RTS`; and it calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` before setting the row pointers, where the player version calls it after. More guard twins of player subroutines, with the guard's zero-page bytes in place of the player's: `GET_GUARD_SPRITE_AND_COORDS` (`74df`) and `GET_SPRITE_AND_SCREEN_COORD_AT_PLAYER` (`6b85`); `INC_GUARD_ANIM_STATE` (`7574`) and `INC_ANIM_STATE` (`6bf4`); `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW` (`7582`, `7595`) and `NUDGE_PLAYER_TOWARDS_EXACT_COLUMN` and `_ROW` (`6c13`, `6c26`), down to the tail call into the gold check.
- **Sharing where the whole ending is the same**: `TRY_GUARD_MOVE_DOWN` borrows `TRY_GUARD_MOVE_UP`'s whole tail, animation included, since both climb (states 14-15). `TRY_GUARD_MOVE_LEFT` and `TRY_GUARD_MOVE_RIGHT` share nothing, although their last 12 bytes are identical (`703b-7047` and `70cc-70d8`: `JSR INC_GUARD_ANIM_STATE`, `JSR GET_GUARD_SPRITE_AND_COORDS`, `JSR DRAW_SPRITE_AT_PIXEL_COORDS`, `JMP STORE_GUARD_DATA`); only the animation groups loaded just before them differ. The player code does the same (`TRY_MOVING_LEFT`, `TRY_MOVING_RIGHT`). A guess: Doug shared an ending only where it was the same as a whole, not where only its last bytes were.
- **The double indirection in `COMPUTE_SHIFTED_SPRITE`**: the shifted sprite bytes are found through `PIXEL_SHIFT_PAGES` and `PIXEL_SHIFT_TABLE` into `PIXEL_PATTERN_TABLE`, where less would seem to do. Noted in earlier work on the sprite routines, outside this document's pilot; not checked again here.
- **Labels that say more or other than the code**: `.ladder` (`6e85`) means "not falling, not in a hole: choose a move"; `GUARD_DO_NOTHING` is not the dispatch's "do nothing"; `GUARD_GOLD_TIMER` holds two meanings, positive and negative.

---

## Appendix C: corrections and additions to Xekri's documentation

- **`9B00` is not unused**: `main.nw` ("Extra data") says that `9000-9EFF` appears to be unused. But `INIT_GAME_DATA` sets the pointer `$A8`/`$A9` to `$9B00` (`6068`: `$A8` = 0, `606c`: `$A9` = `$9B`), and `CHECK_FOR_MODE_1_INPUT` reads its key commands from there in the attract play (`69dc`, `69e1`), two bytes at a time: a command byte (low nibble: `KEY_COMMAND`, high nibble: `KEY_COMMAND_LR`, both as indexes into `VALID_KEY_COMMANDS`) and how many moves it lasts. So `9B00` holds the attract play's recorded input. In the current run, `69da-69f2` loaded 3 pairs (`16 4C`, `66 02`, `55 01`). Where the recording ends is not checked yet.
- **`$53` in `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` is `GUARD_RESURRECT_COL`**: `main.nw` writes `GUARD_GOLD_TIMER = 0xFF - $53` with the address raw. `$53` is the counter that `HANDLE_TIMERS` steps through 0 to 27 once per round of the game loop, so how far a guard carries gold depends on when he picked it up (see the notes of Part 1).

---

## Appendix D: ideas for `papple2`

Ideas that came up while reading, for the session that goes back to `papple2`. Not decisions.

- **Similarity between subroutines**: the player code and the guard code have the same shape (see appendix B), found by eye. A cheap first measure: compare two subroutines' sequences of mnemonics, e.g. with Python's `difflib`. Tools that do this properly, named from memory and not checked: Ghidra's BSim and Version Tracking, radare2's `radiff2`, BinDiff, Diaphora.
- **Returns behind a payload are counted as stack jumps**: `LOAD_SOUND_DATA` and `PUT_STRING` read the bytes behind their `JSR` through the return address and return behind those bytes. Two such returns ran in the attract play (`880a` -> `6bf3` and `86f9` -> `7a25`, in `lr_split_transitions.csv`). Neither target lies 3 bytes behind a `JSR`, so `stack_jumps()` counts both, and `find_routines()` makes each a routine of its own: `routine_6bf3` is the `.end` `RTS` of `CHECK_FOR_GOLD_PICKED_UP_BY_PLAYER`, `routine_7a25` the tail of `PUT_STATUS`.
- **The reach of a branch**: whether a branch to a `JMP` was needed for reach can be computed from two addresses (see "A branch to a `JMP` where the branch alone would reach").
- **A tail call `papple2` gets right, and one it absorbs**: `GUARD_DROP_GOLD` ends in `JMP DRAW_SPRITE_AT_PIXEL_COORDS`, a subroutine many others call with `JSR`. So its target is an entry for `papple2`, and the `JMP` shows as a blue arrow (it did not run in the attract play). `TRY_GUARD_MOVE_DOWN` jumps into `TRY_GUARD_MOVE_UP`'s tail, which nobody calls with `JSR`, so `papple2` absorbs the tail into `routine_6f39`. The routine graph shows the result: `routine_6f39` is credited with the `JSR`s at `6f26` (60 to `routine_74f7`) and `6f2d` (76 to `routine_7574`), which lie in `TRY_GUARD_MOVE_UP`'s span. The `NUDGE_GUARD_TOWARDS_EXACT_*` tail calls into `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (blue arrows "JMP 6" and "JMP 2" into `routine_74f7`) are of the first kind.
- **Call or jump is a question per site, not per subroutine**: `DRAW_SPRITE_AT_PIXEL_COORDS` is entered by `JSR` from many sites and by `JMP` from `GUARD_DROP_GOLD`; `STORE_GUARD_DATA` only by `JMP` and dispatch; `GUARD_DO_NOTHING` only by branches. Seeing one `JSR` into a subroutine says nothing about its other ways in.
- **Coverage of the attract play**: static reading shows paths a run never took, e.g. a guard never moved up, never carried gold, never fell. A longer run covers more, because the attract play replays a recording (see appendix C), and the 4,000,000 instructions of the current run read the player's input only 79 times, covering 3 of the recording's pairs. About a quarter of those instructions went into delays and relocation, computed by hand from `lr_split_tiles.csv`: the inner delay loop of `SOUND_DELAY` (`86b7`, 2 instructions, 397,080 times: about 794,000), and the two relocation loops (`2821` and `5f4b`, 4 instructions each, 33,024 and 32,768 times: about 263,000). Skipping their recording saves report rows and instrumentation time, not emulation time; for relocation, the snapshot after relocation is already parked in `TODO.md`.
- **Xekri's labels in `papple2`'s views**: the routine graph and the reports show the dossier's labels, mostly `routine_xxxx`, so reading them next to Xekri's source means translating every address by hand, across several programs. Idea: a way to show Xekri's labels in the views (e.g. from `docs/listings/listing_clean.tsv`), with short forms where `edit()` needs them, without writing them into the dossier.
