# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

---

- **2026-10-13:** The cross reference at the prompt: `read_xrefs()` reads `lr_xrefs.csv` back into the same shape the run counted, the `Session` keeps it, and `show_xrefs("tbl_hx_byte")` shows who reads the table, its rows merged where their addresses follow each other.
- **2026-10-13:** The cross reference: every byte the code reads or writes, counted by the instruction that touched it, with the target as it ran, so code that writes code shows itself. `memory_tour` tells it as Part 3 of the walkthrough, rendered by `make walkthrough-md`; 720 tests green. First light on Lode Runner: 216,787 rows in 5.4 seconds, and `tbl_hx_byte` read exactly the 404 times the first case study predicted.
- **2026-10-12:** The routine graph wears the dossier's colors. A routine that lies wholly in one color range gets a thick border in its shade: `draw_at_hx` and `erase_at_hx` in blue, `y_to_ptrs` in cyan, the routines of the first case study found at a glance in the picture of the whole run. From idea to green in one evening, every new name checked before the first line of code.
- **2026-10-12:** The first case study: drawing and erasing a sprite in Lode Runner, read with the tools from `draw_player` down through `draw_at_hx` to the div 7 and mod 7 tables, colored in the editor, the hexdump and the map. Names first: cell, y, hx, byte, shift, one word for one thing, and the riddle of the "half-screen column" solved: it is the pixel column halved, every second column, so a sprite never changes its colors as it walks. A walk at the prompt in `docs/lr_case_studies.md`, ready to present.
- **2026-10-12:** In the editor, `q` leaves and keeps the lines on the screen, to read next to a hexdump or a map; the height given stays for every routine.
- **2026-10-12:** The README describes what is there now: the history out, the developer sections in `docs/architecture.md` and `docs/data-files.md`, the workbench a section of its own with four screenshots. `docs/decisions.md` is gone: the project keeps no decision records.
- **2026-10-12:** The walkthrough becomes a book of chapters that are tests, every row explained: `nested_loops` through the whole pipeline, and `rts_dispatch`, where an `RTS` jumps and the shadow stack sees through it, its targets becoming routines in one before-and-after. `make walkthrough-md` renders the chapters as a document: a tutorial that cannot go out of date.
- **2026-10-12:** A program's `boot()` now gives a ready emulator, and `run()` only runs it.
- **2026-10-11:** The memory map: `memory_map()` shows the dossier's color ranges across all 64 KB at once, with a legend, and zooms down to single bytes. Where two colors meet, the cell turns light yellow. The first picture of what I know about Lode Runner's memory as a place, not a list.
- **2026-10-11:** Syntax coloring in the editor: mnemonics in the colors of the 6502 reference, operands in the color of the table they read, and the same colors in the hexdump. Structure I had never seen so fast jumps out at once.
- **2026-10-11:** De-spaghettification: `listing.py` and the `Session` take over from `shell.py`, which is a third shorter, and two more diagrams show how both views get one list of rows and how the emulator stops.
- **2026-10-11:** `papple2`'s structure at a glance: architecture diagrams made from the code, rendered by `make presentation`, with a script for every slide. A game changer, and something to present.
- **2026-10-10:** The `Session`: a dozen module variables and their `global`s gathered into one object, while the commands stay as they were.
- **2026-10-09:** Colors for orientation, saved in the dossier's `colors.json`. Related routines keep their colors throughout the editor's breadcrumbs, backward and forward, with bold marking the current routine. Long listings color code by location while comments and arrows stay white; the result is readable and the separation looks right. Clipboard text stays plain. The editor's instruction lines deliberately remain uncolored.
- **2026-10-09:** Persistent hiding: `hide()` and `unhide()` keep named ranges in the dossier's `hidden.json`. In `listing()` and `edit()`, each hidden span becomes one grey row, without decoding its bytes or removing its labels and comments. `routine_0800` is easier to read now that the overwritten relocation loop can be set aside.
- **2026-10-09:** `routine_0800` can be read: a listing shows only the code that ran, and every gap that never ran is one grey line. On the way I found that Lode Runner's start-up code was overwritten after it ran, and traced the jumps from `0800` through the relocation to `game_start` at `6056`.
- **2026-10-09:** Up the call tree in the editor: `u` lists the callers of the routine shown, with how often each call was made, and Enter lands on the `JSR`. From `r_11x2_2` it is two steps up to the main loop, and `routine_64bd` turns out to be the hub of nearly everything drawn.
- **2026-10-09:** Offset labels: `STA .selfmod1+2` instead of `STA $845c` with a comment. The self-modifying chain in `routine_8438` now reads as code: `.selfmod1` writes into the operand of `.selfmod3`.
- **2026-10-08:** Go To and forward in the editor. `g` lists every routine of the run, Enter takes me there; Backspace comes back, and `f` goes forward again, the way ahead in grey in the breadcrumbs, like in a browser. Built while comparing `r_11x2_1` and `r_11x2_2`, and used for it at once. The old editor is retired; the new one is simply `listing_editor` now.
- **2026-10-08:** The new listing editor, built on prompt_toolkit. Lode Runner's code opens right under the IPython prompt and vanishes when I leave. Enter on a `JSR` takes me into the routine it calls, Backspace brings me back, the breadcrumbs in the top rule say where I am, and every routine opens as I last left it. Labels with Tab, in place, comments with `e`. Was fuer ein geiler Editor!
- **2026-10-07:** `hexdump()`: Lode Runner's row tables at a glance, `hgr_rows_lo` ending exactly where `hgr_rows_hi` begins. Whatever a command shows goes to the clipboard with `clip()`.
- **2026-10-07:** Labels where the code uses them: in `edit()`, I name what an operand points at, zero page included. Two terminals work on one dossier side by side.
- **2026-10-07:** Structure discovery: a routine now ends where another begins, and every way into a routine is an arrow of its own kind: `JSR`, `JMP`, branch, glide, and the `RTS` of a stack jump, found by the shadow stack. Every piece of code that ran now belongs to a routine; no orphans left.
- **2026-10-06:** The routine graph: every routine of the attract play in one picture, with the `JSR`s between them and my labels on the boxes. Level loading on the left, the game loop on the right. Clearer than my dot from the Robotron project: the point where `papple2` leaves the old workbench behind for good.
- **2026-10-06:** The inner-loop page for the new design: the same seven instructions, every byte with the hook list that hears it. The immediate operand was the eye-opener: the addressing mode reads nothing, the operation reads it as an immediate.
- **2026-10-06:** The Book. I know now where all of this is headed: a series about Apple II games, how they work under the hood, and how to find that out. Remember, appreciate, tinker, create.
- **2026-10-05:** The listing editor. I label and comment Lode Runner's code in the terminal as fast as I read it, and every change is saved at once. It began as my own half-hour prototype.
- **2026-10-04:** `lookup_hgr`, the first routine of Lode Runner I found, read and named without help. Then its four callers, and my first tail call.
- **2026-10-03:** The dossier. What I learn stays: labels and comments survive every run, under git. All 68 routines of the attract play at the prompt.
- **2026-10-02:** The first look at real code with the new tools: `LOAD_LEVEL` in IPython, its four loops drawn as nested arrows. All four match the oracle.
- **2026-10-02:** The walkthrough: twenty bytes through the whole pipeline, every row predicted by hand first.
- **2026-09-29:** The first execution map: one picture of everything Lode Runner's attract play runs.
- **2026-09-27 to 2026-10-01:** The instrumentation rebuilt from scratch, from the tag `pre-redesign` to `core-complete`. The emulator runs at 3.5 times a real Apple II.
- **2026-09-27:** The inner-loop diagram: seven instructions traced through the old emulator, call by call, on a page I can click through. Two hours back and forth between the diagram and the code, one of the best sessions of the project.
- **2026-09-27:** Bandits runs into the game, right up to Game Over.
- **2026-09-26:** Lode Runner plays a real game from the original disk image.
- **2026-09-23:** The new direction: understanding Apple II games by running them. Lode Runner boots.
- **2026-09-11:** `papple2` runs without a window.
- **2026-09-03:** Revived after six years at rest.

(The detailed entries up to 2026-09-26 are at the git tag `pre-redesign`: `git show pre-redesign:HISTORY.md`.)
