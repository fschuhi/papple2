# The structures of Lode Runner, read from Xekri's source

Started 2026-10-15, base commit `dc2d967`. Read from Xekri's literate source (`main.nw`) and its listing (`docs/listings/listing_clean.tsv`), with the counts from the attract play's split reports (`docs/reports/lr_basic_blocks_analysis/lr_split_tiles.csv` and `lr_split_transitions.csv`). Why this document exists and what it is for: `docs/structures_handover.md`.

---

## Status (2026-10-15, evening)

- **Part 1**, the table of Xekri's subroutines: 15 rows done, the guard's "legs" (everything that carries out a move). 7 rows to do, the helpers of the guard AI: `SHOULD_GUARD_MOVE_LEFT`, `SHOULD_GUARD_MOVE_RIGHT`, `SHOULD_GUARD_MOVE_UP_OR_DOWN`, `PSEUDO_DISTANCE`, `GUARD_FIND_CANDIDATE_ROW_ABOVE`, `GUARD_FIND_CANDIDATE_ROW_BELOW`, `DETERMINE_GUARD_LEFT_RIGHT_LIMITS`. Their rows need only how they are entered and left, not how the AI decides.
- **Part 2**, the catalogue of structures: entry 1 (tail call) written, its explain-back answered, its parts 6 and 7 open. The handover lists six structures: tail call; jump into the middle of another subroutine; dispatch by `RTS`; one subroutine with two doors; fall-through into the next subroutine; code that runs once and is overwritten. The first three all appear in Part 1. Each entry has the same eight parts (see the handover).
- **Part 3**, a rule for routines: empty. It needs Parts 1 and 2.
- **Part 4**, open questions: three.
- **Done**, as the handover defines it: Part 1 covers the pilot, Part 2 holds the six structures with all eight parts each, Part 3 has a rule graded on the pilot.

---

## Terms

- **Xekri's subroutine**: a unit of Xekri's source, from his `SUBROUTINE` mark to its last instruction. Static: it holds its code whether that code ran or not.
- **routine**: `papple2`'s word. The blocks that ran, found from one run. A routine is a hypothesis: another run can show blocks this run never reached.
- **part of a routine**: a block that ran and that the rule for routines assigns to it. Code that never ran is part of no routine.
- **span**: from the first address up to the end. For a Xekri subroutine: from its start to the first address behind its last instruction. For a routine: from its lowest block to the end of its highest block, gaps included.
- **lies within**: position only. Data, payload or code that lies within a span is not claimed as belonging to it. Whether it belongs is a question for stretches (`GOALS.md`, "Routines as stretches").
- **label**: what an address is called. This document uses Xekri's labels; the dossier's labels are not touched by it.
- **stack jump**: an `RTS` to an address that is not right behind a `JSR`, i.e. not an ordinary return. The mechanism, whatever it is used for (`papple2`'s `stack_jumps()`).
- **dispatch by `RTS`**: one use of a stack jump: pushing an address taken from a table and doing `RTS` to choose among several subroutines (`MOVE_GUARD`, `6e96`). The returns behind a payload are stack jumps too, but no dispatch.
- **Addresses**: a pair like `6f26-6f39` includes the first address and excludes the second.

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

## Part 1: the subroutines of guard movement, as Xekri has them

The answer key: any rule for routines that `papple2` uses later is graded against this table.

**Scope (first round)**: `MOVE_GUARD`, `GUARD_DO_NOTHING`, the four `TRY_GUARD_MOVE_*`, the six small helpers from `GET_GUARD_SPRITE_AND_COORDS` (`74df`) to `NUDGE_GUARD_TOWARDS_EXACT_ROW` (`7595`), `STORE_GUARD_DATA` and `LOAD_GUARD_DATA`. `DETERMINE_GUARD_MOVE` is one row; its seven helpers are the rows still to do (see Status). Together they are the guard AI, which decides where a guard goes. Everything else in the scope carries that decision out. The sprite routines `ERASE_SPRITE_AT_PIXEL_COORDS` (`8336`) and `DRAW_SPRITE_AT_PIXEL_COORDS` (`83a7`) appear only as callees.

**Columns**:

| Column | Meaning |
|---|---|
| name | Xekri's label at the start |
| start | the first address of Xekri's subroutine (see the notes for subroutines whose start is not their entry) |
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
- `DETERMINE_GUARD_MOVE` is the guard AI, here as a closed box. It answers in one of three ways, each with an `RTS` of its own: "in a hole: up" (the order that `GUARD_DO_NOTHING` deals with when the way up is blocked); "on the player's row with nothing in between: straight at him", right or left; otherwise the answer of its helpers (rows still to do). All its `RTS`s return to `MOVE_GUARD`, right before the dispatch.
- `LOAD_GUARD_DATA` is the mirror of `STORE_GUARD_DATA`: tables to working copy. It starts right behind `STORE_GUARD_DATA`'s `RTS`, without a gap.
- `GUARD_DROP_GOLD`: a guard carrying gold has a negative `GUARD_GOLD_TIMER`, counted up by one each time he enters a new cell. When it reaches 0, he drops the gold if the cell is empty; the drawing is a tail call, `JMP DRAW_SPRITE_AT_PIXEL_COORDS` (`756e`), whose `RTS` returns to `GUARD_DROP_GOLD`'s caller. If the cell is not empty, the timer goes back to -1 and he tries again at the next cell. In the attract play no guard carried gold, so only the first test and the `RTS` ran.
- `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW`: two levels of tail call. `TRY_GUARD_MOVE_DOWN` calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` by `JSR` (`6f69`). If the guard is already on his column, `NUDGE` returns with its own `RTS` (70x). If not, it moves him one step toward the column and jumps to `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (6x), whose `RTS` returns to `TRY_GUARD_MOVE_DOWN` (`6f6c`), not to `NUDGE`. The same pattern as `MOVE_GUARD` and `STORE_GUARD_DATA`, one level down. The gold check follows each nudge because the step may leave the guard exactly on a cell with gold.
- `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`: on pickup, `GUARD_GOLD_TIMER` is set to `$FF - $53` (`751b-7520`). `$53` is `GUARD_RESURRECT_COL`, a counter that `HANDLE_TIMERS` steps through 0 to 27 once per round of the game loop. So the timer starts between -1 and -28, and `GUARD_DROP_GOLD` counts it up once per cell: how far a guard carries gold depends on when he picked it up. A cycling counter used as a cheap random number. Read from the code; the pickup never ran in the attract play.
- A long global label with another subroutine's label as its prefix (`TRY_GUARD_MOVE_UP_check_for_gold`) marks a door from outside: dasm makes a local label (`.check_for_gold`) visible only within its own `SUBROUTINE`, so a label reached from another subroutine has to be global.
- Start and entry: in six places, Xekri's subroutine begins with a local label in front of its entry, used by the "give up early" tests at the top: `67d8`, `689e`, `71a1`, `720b`, `72fd`, `739a` (found by reading, not by a tool). The four in the pilot (`71a1`, `720b`, `72fd`, `739a`) lie in the guard AI's helpers, the rows still to do; the decision how the "start" column treats them comes with those rows.

---

## Part 2: the catalogue of structures

### Entry 1: tail call

Status: explain-back answered (2026-10-15). Parts 6 and 7 are open.

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

**5. What `papple2` does with it today**: if the target of the `JMP` is also called by `JSR` somewhere, it is an entry, and the `JMP` shows as a blue arrow between two routines: `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW` into `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` ("JMP 6" and "JMP 2" into `routine_74f7`). If it never is, the target is no entry and is absorbed into every routine that jumps there: `STORE_GUARD_DATA` is part of `routine_6f39`, `routine_6fbc` and `routine_7047` at once (`docs/structures_handover.md`, "E"). The docs call every blue `JMP` arrow a tail call, which claims more than the code checks.

**6. What I want to see**: to be decided, after discussing the alternatives. Candidates:

- **A. In the routine graph**: the target as a routine of its own (`STORE_GUARD_DATA`), with the tail calls as arrows into it. Needs a rule that makes it an entry (part 7).
- **B. In the listing**: at each tail call, a note saying where its `RTS` will return, e.g. "returns to the caller of `MOVE_GUARD`".
- **C. In a report**: a table of tail calls: site, target, how often, and where the target's `RTS` returned.
- **D. Nothing of its own**: tail calls only matter as far as they make the routines right.

**7. A rule in words**: a first idea, not graded. A `JMP` is a tail call if the `RTS` that ends the code at its target returns to the caller of the subroutine the `JMP` lies in. The run can check this: the stack tracking knows which `JSR` an `RTS` returns for. Known problem: a `JMP` back to the start of its own loop (`SHOULD_GUARD_MOVE_LEFT`, `7208`) also ends in an `RTS` that returns to its caller, and must not count. See Part 4, "A jump upward past the subroutine's own entry".

**8. Explain-back**: `TRY_GUARD_MOVE_DOWN` calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` with `JSR`; `NUDGE` jumps to `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`. Whose `RTS` brings control back to `TRY_GUARD_MOVE_DOWN`, and why not `NUDGE`'s? Answer (2026-10-15): `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD`'s, because `NUDGE` jumped there instead of calling it; and on the pickup path `ERASE_SPRITE_AT_PIXEL_COORDS`'s, because `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` ends in a tail call of its own there.

---

## Part 3: a rule for routines, graded on the pilot

(to come)

---

## Part 4: open questions

- **A jump upward past the subroutine's own entry** is a signal that the code leaves into someone else's, but not proof. `TRY_GUARD_MOVE_DOWN` jumps up into `TRY_GUARD_MOVE_UP`'s tail (`6fb6`, `6fb9`); `SHOULD_GUARD_MOVE_LEFT` branches up to its own exit (`71a6` -> `71a1`). A rule in Part 3 has to tell the two apart.
- **`GUARD_DO_NOTHING`'s timer fix-up**: does the reading in the notes of Part 1 match what is seen in play?
- **Not yet understood: the adjustments and the nudging.** How `GUARD_X_ADJ` and `GUARD_Y_ADJ` (0 to 4, 2 = exactly on the cell) place a guard between cells, and why moving in one direction nudges him toward the middle of the other. Booked as "too difficult, yet"; a picture of one cell with its five positions would be the place to start.

---

## Traces of how the code was written

Findings that may say something about how Doug wrote the code, not about what it does. Candidates for Xekri's documentation (`a2-lode-runner`). None of them is a message from Doug to the reader: they may be left over from his development process.

- **The exit at the door**: in six places, the target of a subroutine's "give up early" tests sits right in front of its entry (`67d8`, `689e`, `71a1`, `720b`, `72fd`, `739a`), and in one more it is a subroutine of its own (`GUARD_DO_NOTHING`, `6ea1`). The byte before the entry is the closest spot to those tests. Branches reach at most 128 bytes back and 127 forward, so placing the exit there from the start keeps it in reach however long the subroutine grows. In the two digging cases it was needed: `.stop_digging` (`6892`) is 165 bytes from the `BCS` at `67eb`.
- **A branch to a `JMP` where the branch alone would reach**: in `TRY_GUARD_MOVE_DOWN`, `BCC .check_for_gold` (`6f85`) leads to `JMP TRY_GUARD_MOVE_UP_check_for_gold` (`6fb9`), but the `BCC` ends at `6f87`, only 97 bytes behind `6f26`. In `TRY_MOVING_DOWN`, `BCC .check_for_gold_` (`67ac`) leads to `JMP TRY_MOVING_UP_check_for_gold` (`67d5`), but the `BCC` ends at `67ae`, only 87 bytes behind `6757` (both computed by hand). So these are no stretchy branches as far as reach goes. Perhaps they were, in an earlier version of the code.
- **Player code and guard code with the same shape**: `TRY_MOVING_DOWN` and `TRY_GUARD_MOVE_DOWN`, compared side by side by reading: the same steps in the same order, and both borrow the tail of their `UP` by the same two doors. The guard version adds a test for a guard below, `GUARD_DROP_GOLD` and the test whether the player is killed; it leaves by `JMP STORE_GUARD_DATA` instead of `SEC` / `RTS`; and it calls `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` before setting the row pointers, where the player version calls it after. More guard twins of player subroutines, with the guard's zero-page bytes in place of the player's: `GET_GUARD_SPRITE_AND_COORDS` (`74df`) and `GET_SPRITE_AND_SCREEN_COORD_AT_PLAYER` (`6b85`); `INC_GUARD_ANIM_STATE` (`7574`) and `INC_ANIM_STATE` (`6bf4`); `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` and `_ROW` (`7582`, `7595`) and `NUDGE_PLAYER_TOWARDS_EXACT_COLUMN` and `_ROW` (`6c13`, `6c26`), down to the tail call into the gold check.
- **Sharing where the whole ending is the same**: `TRY_GUARD_MOVE_DOWN` borrows `TRY_GUARD_MOVE_UP`'s whole tail, animation included, since both climb (states 14-15). `TRY_GUARD_MOVE_LEFT` and `TRY_GUARD_MOVE_RIGHT` share nothing, although their last 12 bytes are identical (`703b-7047` and `70cc-70d8`: `JSR INC_GUARD_ANIM_STATE`, `JSR GET_GUARD_SPRITE_AND_COORDS`, `JSR DRAW_SPRITE_AT_PIXEL_COORDS`, `JMP STORE_GUARD_DATA`); only the animation groups loaded just before them differ. The player code does the same (`TRY_MOVING_LEFT`, `TRY_MOVING_RIGHT`). A guess: Doug shared an ending only where it was the same as a whole, not where only its last bytes were.
- **The double indirection in `COMPUTE_SHIFTED_SPRITE`**: the shifted sprite bytes are found through `PIXEL_SHIFT_PAGES` and `PIXEL_SHIFT_TABLE` into `PIXEL_PATTERN_TABLE`, where less would seem to do. Noted in earlier work on the sprite routines, outside this document's pilot; not checked again here.
- **Labels that say more or other than the code**: `.ladder` (`6e85`) means "not falling, not in a hole: choose a move"; `GUARD_DO_NOTHING` is not the dispatch's "do nothing"; `GUARD_GOLD_TIMER` holds two meanings, positive and negative.

---

## Ideas for `papple2`

Ideas that came up while reading, for the session that goes back to `papple2`. Not decisions.

- **Similarity between subroutines**: the player code and the guard code have the same shape (see "Traces of how the code was written"), found by eye. A cheap first measure: compare two subroutines' sequences of mnemonics, e.g. with Python's `difflib`. Tools that do this properly, named from memory and not checked: Ghidra's BSim and Version Tracking, radare2's `radiff2`, BinDiff, Diaphora.
- **Returns behind a payload are counted as stack jumps**: `LOAD_SOUND_DATA` and `PUT_STRING` read the bytes behind their `JSR` through the return address and return behind those bytes. Two such returns ran in the attract play (`880a` -> `6bf3` and `86f9` -> `7a25`, in `lr_split_transitions.csv`). Neither target lies 3 bytes behind a `JSR`, so `stack_jumps()` counts both, and `find_routines()` makes each a routine of its own: `routine_6bf3` is the `.end` `RTS` of `CHECK_FOR_GOLD_PICKED_UP_BY_PLAYER`, `routine_7a25` the tail of `PUT_STATUS`.
- **The reach of a branch**: whether a branch to a `JMP` was needed for reach can be computed from two addresses (see "A branch to a `JMP` where the branch alone would reach").
- **A tail call `papple2` gets right, and one it absorbs**: `GUARD_DROP_GOLD` ends in `JMP DRAW_SPRITE_AT_PIXEL_COORDS`, a subroutine many others call with `JSR`. So its target is an entry for `papple2`, and the `JMP` shows as a blue arrow (it did not run in the attract play). `TRY_GUARD_MOVE_DOWN` jumps into `TRY_GUARD_MOVE_UP`'s tail, which nobody calls with `JSR`, so `papple2` absorbs the tail into `routine_6f39`. The routine graph shows the result: `routine_6f39` is credited with the `JSR`s at `6f26` (60 to `routine_74f7`) and `6f2d` (76 to `routine_7574`), which lie in `TRY_GUARD_MOVE_UP`'s span. The `NUDGE_GUARD_TOWARDS_EXACT_*` tail calls into `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` (blue arrows "JMP 6" and "JMP 2" into `routine_74f7`) are of the first kind.
- **Call or jump is a question per site, not per subroutine**: `DRAW_SPRITE_AT_PIXEL_COORDS` is entered by `JSR` from many sites and by `JMP` from `GUARD_DROP_GOLD`; `STORE_GUARD_DATA` only by `JMP` and dispatch; `GUARD_DO_NOTHING` only by branches. Seeing one `JSR` into a subroutine says nothing about its other ways in.
- **Coverage of the attract play**: static reading shows paths a run never took, e.g. a guard never moved up, never carried gold, never fell. A longer run covers more, because the attract play replays a recording (see "Corrections and additions to Xekri's documentation"), and the 4,000,000 instructions of the current run read the player's input only 79 times, covering 3 of the recording's pairs. About a quarter of those instructions went into delays and relocation, computed by hand from `lr_split_tiles.csv`: the inner delay loop of `SOUND_DELAY` (`86b7`, 2 instructions, 397,080 times: about 794,000), and the two relocation loops (`2821` and `5f4b`, 4 instructions each, 33,024 and 32,768 times: about 263,000). Skipping their recording saves report rows and instrumentation time, not emulation time; for relocation, the snapshot after relocation is already parked in `docs/structures_handover.md`.
- **Xekri's labels in `papple2`'s views**: the routine graph and the reports show the dossier's labels, mostly `routine_xxxx`, so reading them next to Xekri's source means translating every address by hand, across several programs. Idea: a way to show Xekri's labels in the views (e.g. from `docs/listings/listing_clean.tsv`), with short forms where `edit()` needs them, without writing them into the dossier.

---

## Corrections and additions to Xekri's documentation

- **`9B00` is not unused**: `main.nw` ("Extra data") says that `9000-9EFF` appears to be unused. But `INIT_GAME_DATA` sets the pointer `$A8`/`$A9` to `$9B00` (`6068`: `$A8` = 0, `606c`: `$A9` = `$9B`), and `CHECK_FOR_MODE_1_INPUT` reads its key commands from there in the attract play (`69dc`, `69e1`), two bytes at a time: a command byte (low nibble: `KEY_COMMAND`, high nibble: `KEY_COMMAND_LR`, both as indexes into `VALID_KEY_COMMANDS`) and how many moves it lasts. So `9B00` holds the attract play's recorded input. In the current run, `69da-69f2` loaded 3 pairs (`16 4C`, `66 02`, `55 01`). Where the recording ends is not checked yet.
- **`$53` in `CHECK_FOR_GOLD_PICKED_UP_BY_GUARD` is `GUARD_RESURRECT_COL`**: `main.nw` writes `GUARD_GOLD_TIMER = 0xFF - $53` with the address raw. `$53` is the counter that `HANDLE_TIMERS` steps through 0 to 27 once per round of the game loop, so how far a guard carries gold depends on when he picked it up (see the notes of Part 1).
