# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

- The detailed entries up to 2026-09-26 are at the git tag `pre-redesign`: `git show pre-redesign:HISTORY.md`.

---

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
