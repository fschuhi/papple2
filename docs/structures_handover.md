# Handover: the structures of Lode Runner, read from Xekri's source

(Note: "I" in the following paragraphs refers to the user, "you" to you as the AI model.)

Written at the end of the session of 2026-10-15, base commit `b3dce2b`. For the next session, which works from Xekri's source, statically, and writes no `papple2` code.

---

## Why this session exists

For four weeks, `papple2` has been built to find Lode Runner's structure by running the game: basic blocks, routines, loops, callers, stack jumps, cross references. On 2026-10-15, reading its output closely showed that its routines do not match the structure of the code as Xekri's source shows it. The tools grew faster than my understanding of what they produce, and each new output made things less clear, not more.

So we stop building and first write down what structure we want to see. Xekri's source is the best map of Lode Runner we have: his `SUBROUTINE` marks show where the author's routines begin and end, and his names say what they do. The next session reads it and writes the document described below. Only after that do algorithms come back, measured against that document.

## What works today, in short

- **The emulator** boots Lode Runner from the original disk image and runs the attract play.
- **Basic blocks** (`Tiling`, the split tiles) are sound: every piece of code that ran, cut at every entry and every leap, without overlaps.
- **Stack jumps** are found: `routine_6cdb` chooses the guard's move by pushing an address and doing an `RTS`, and the run finds all three targets (`6f39` 76 times, `6fbc` 26 times, `7047` 10 times). That is real structure, found dynamically, and it matches Xekri.
- **The dossier** keeps labels, comments, hidden ranges and color ranges.
- **`make lr-current`** opens IPython with the run and all committed reports loaded; `edit()` and `show_xrefs()` work there together. It writes `docs/reports/lr_current/lr_overview.txt`, `lr_routines.csv` and `lr_listing.tsv`, with labels.

## What does not work: the worked example

`papple2`'s rule for a routine: it starts at an **entry** (the run's start, a `JSR` target, or a stack jump target) and holds every block reachable from there along branches and `JMP`s, without following `JSR`s. It is named `routine_` plus its entry.

Xekri's `TRY_GUARD_MOVE_DOWN` (`6f39`) has no `RTS` of its own. It ends in one of three `JMP`s (from `docs/listings/6f39-TRY_GUARD_MOVE_DOWN.lst`):

```
6f60  JMP STORE_GUARD_DATA                      ; to 75a8
6fb6  JMP TRY_GUARD_MOVE_UP_inc_anim_state      ; to 6f29, 16 times
6fb9  JMP TRY_GUARD_MOVE_UP_check_for_gold      ; to 6f26, 60 times
```

`6f26`-`6f39` is the end of another subroutine, `TRY_GUARD_MOVE_UP`, whose entry never ran in the attract play. It ends with `6f36 JMP $75a8`. `STORE_GUARD_DATA` (`75a8`-`75ce`) ends in the `RTS` that returns behind the `JSR 6cdb` at `6c9b`. Nobody calls `6f26`, `6f29` or `75a8` with `JSR`, so for `papple2` they are not entries, and they are absorbed into the routines that jump there:

```
 6f26   6f39            6fbc         7047         70d8 ......... 75a8   75ce
 |--A--||------B-------||-----C-----||-----D-----| other        |--E--|
 UP's    MOVE_DOWN       MOVE_LEFT    MOVE_RIGHT   routines      STORE_GUARD_DATA
 tail

 routine_6f39 = A + B + E      (B jumps to A, A jumps to E)
 routine_6fbc =         C + E  (C jumps to E)
 routine_7047 =             D + E

 "span" of routine_6f39 = 6f26 up to 75ce: everything from A to E,
 including C, D and the other routines, which it does not own
```

What follows from this:

1. **Tail calls by `JMP` are not detected.** The blue `JMP` arrows in the routine graph only mark a `JMP` into code that is already an entry because someone else `JSR`s there. A `JMP` into code nobody calls is followed as if it were inside the routine. The docs call the blue arrows tail calls, which claims more than the code does.
2. **Routines overlap.** `STORE_GUARD_DATA` belongs to three routines. In a noweb view of the code, overlapping routines make no sense.
3. **A listing shows a span, not a routine.** `listing()`, `edit()` and `lr_listing.tsv` show everything from a routine's lowest block to its highest, so other routines appear inside it. In `lr_listing.tsv`, the column `routine` means "listed under", not "belongs to". That column is wrong as named.
4. **`edit()` on such a routine is unusable.** The arrows span thousands of bytes, the gutter grows too wide, and without a scrollbar there is no sense of where in the routine one is.

## The job for the next session

Read Xekri's source and write `docs/lr_structures.md`. No `papple2` code. Tools only to check a claim before it is made (Rule 8 of `CRITICAL_RULES.md`), and each tool use announced.

**Inputs to attach:**

- Xekri's source: the literate source `main.nw`, or the full listing that `make dasm-listing` writes in `a2-lode-runner`. The two sections in `docs/listings/` are not enough.
- this document
- `dossiers/lode_runner/annotations.json`, for the labels given so far
- `docs/reports/lr_basic_blocks_analysis/lr_split_tiles.csv` and `lr_split_transitions.csv`, for what ran and how often

**Start with a pilot, not the whole game:** the guard movement. That is `routine_6cdb` and what it dispatches to, from `TRY_GUARD_MOVE_UP` to `STORE_GUARD_DATA` (`6f26`-`75ce`), plus the helpers they call (`GET_GUARD_SPRITE_AND_COORDS` at `74df`, `NUDGE_GUARD_TOWARDS_EXACT_COLUMN` at `7582`, `GUARD_DROP_GOLD` at `753e`, the sprite drawing at `8336` and `83a7`). It holds most of the structures below in a small space. Extend to other chapters only after the pilot is done.

## The deliverable: `docs/lr_structures.md`

### Part 1: the routines as Xekri has them (the pilot)

One row per Xekri `SUBROUTINE` in the pilot area:

| Column | Meaning |
|---|---|
| name | Xekri's name |
| start | its first address |
| end | the first address behind it (exclusive) |
| entered by | `JSR` from where, `JMP` from where, `RTS` dispatch from where, falls in from where |
| leaves by | `RTS`, `JMP` to which routine, falls into which routine |
| ran | whether it ran in the attract play, from `lr_split_tiles.csv`; partly, if only some of its blocks ran |

This table is the answer key: any rule for routines that `papple2` uses later is graded against it.

### Part 2: the catalogue of structures

One entry per structure. Each entry has the same parts:

1. **Name**: one name, used everywhere afterwards.
2. **What it is**, in plain words, two or three sentences.
3. **Xekri's example**: the lines of code, quoted with addresses and Xekri's names.
4. **How it shows in a run**: the rows of `lr_split_transitions.csv` that carry it, with their counts.
5. **What `papple2` does with it today**, in one or two sentences.
6. **What I want to see**: in a listing, in the routine graph, in a file.
7. **A rule in words** that would find it from a run. No code.
8. **Explain-back check**: a question about the example that I answer in my own words before the entry counts as done.

The structures met so far, each with its example:

1. **Tail call by `JMP`**: `TRY_GUARD_MOVE_DOWN` ends in `JMP STORE_GUARD_DATA`.
2. **Jump into the middle of another routine**: `TRY_GUARD_MOVE_DOWN` into `TRY_GUARD_MOVE_UP` at `6f26` and `6f29`.
3. **Dispatch by `RTS`**: `routine_6cdb` choosing among the three guard moves.
4. **One routine with two doors**: `DRAW_SPRITE_PAGE1` (`82aa`) ends in a `BNE` to `DRAW_SPRITE` (`82b4`); `DRAW_SPRITE_PAGE2` (`82b0`) runs straight into it. Xekri makes all three separate subroutines.
5. **Fall-through into the next routine**: Xekri's "Fallthrough to RESET_GAME" at `6008`.
6. **Code that runs once and is overwritten**: the relocation (`2800`-`2832`, `5f32`-`6056`).

Candidates to check while reading. Each is either confirmed in Xekri's source with an example, or dropped:

- **Self-modifying code**: `shift_sprite` writes its own operands (`shift_sprite.selfmod1` to `.selfmod8`).
- **Jump through a pointer**: `JMP ($xxxx)`, if Lode Runner has any.
- **Tables split into low and high bytes**: `CURR_LEVEL_ROW_SPRITES_PTR_OFFSETS` and `_PAGES` at `1c05` and `1c15`, used in `LOAD_LEVEL`.
- **Two copies of the same data on two pages**: `PTR1` and `PTR2` in `LOAD_LEVEL`, one per sprite table.
- **Packed data**: two level values per byte in `LOAD_LEVEL`, low nibble then high nibble.
- **A branch that always jumps**: `628a BPL` after `AND #$0f`, used as a short `JMP`.
- **Delay loops**: `86b5`-`86bd`, 397,080 passes in the attract play.
- **Data inside code**: bytes between routines that are read, never run.

### Part 3: a rule for routines, graded on the pilot

A rule in words that turns the run's blocks into routines. It must meet two tests:

- **Partition**: every block belongs to exactly one routine. (Check first in Part 1 whether Xekri's subroutines meet that themselves; the two doors and the fall-through are the cases to look at.)
- **Agreement**: on the pilot, how many of Xekri's subroutines the rule gets right, and for each one it gets wrong, why.

The idea from 2026-10-15 to start from: code reached by `JMP` from more than one routine, or reached by `JMP` and never by falling through, starts a routine of its own. Grade it on paper against Part 1 before anyone writes code for it.

### Part 4: open questions

Whatever the reading raises that the document cannot settle.

## How to work in that session

- **Worked example first.** No claim without the lines of code it rests on, with Xekri's names first and the address second. Never an address alone.
- **One structure at a time.** An entry is done when I have answered its explain-back check.
- **I lead the reading.** You check, point out, and write down what we agreed. You do not summarize ahead of me.
- **Done** when Part 1 covers the pilot, Part 2 holds the six structures above with all eight parts each, and Part 3 has a rule graded on the pilot. That is enough to come back to `papple2` with a target.

## Parked for when `papple2` resumes

- `lr_listing.tsv`: the column `routine` means "listed under". Replace it by a whole-run listing with a column `routines` (who owns the instruction), or by listings of a routine's own blocks only.
- `edit()`: the gutter grows too wide on long routines; no indication of where in the routine the bar is (no scrollbar).
- The docs (`README.md`, `docs/workbench.md`) call the blue `JMP` arrows tail calls, and still mention `scripts/lr_overview.py` and `make lr-overview`, which are gone.
- The snapshot after relocation, at the `JMP` at `5fa3` to `619b`, which drops about 131,000 of the rows of `lr_xrefs.csv`, and lets the run end at the same instruction as today.
- The xrefs digest (`lr_xrefs_digest.csv`), with routine names: designed against the routines of Part 3, not today's.
