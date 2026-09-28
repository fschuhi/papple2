# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

- The detailed entries up to 2026-09-26 are at the git tag `pre-redesign`: `git show pre-redesign:HISTORY.md`.

---

## 2026-09-27/28 -- The clean-slate redesign begins: the old instrumentation pruned

- Decision: the instrumentation (hooks, checkpoints, `MemoryMap`/`OpInfo`, tiles, stretches, annotations) is not improved but designed anew. The machine stays: CPU, memory, soft switches, display, keyboard. The last state before the redesign is the tag `pre-redesign` (commit `0797250`); a separate private project keeps a working copy of it, so nothing that was built is lost.
- Removed in six steps, each with an inventory first and `make test` green after it: `annotations.py`; `tiles.py` with stretches and Graphviz call trees; `MemoryMap`, `OpInfo`, the leaps and `jsr_stack` (after this, `core` imports nothing from `debug`); `hooks.py` with `CPUHook` and `MemAccessCollector`, and the CPU's hook calls including `hook=False` and the `immediate` flag; the Robotron leftovers in `checkpoints.py`, `labels.py` and `emulator.py`; the checkpoint list with `KeyScript` and the headless `watch` statistics.
- What took their place: the two disk stand-ins are address traps (`Emulator.add_trap()`; a handler returns whether it served its address, and an unserved trap stops the run via `breakpoint`). The disassembler is static, with an optional `is_code(address)` instead of `MemoryMap`. `executing` mirrors the state machine again: only Running's entry and exit actions set it, and `initialize(fire_events_on_init=True)` runs the entry action at construction, as Harel's statecharts demand.
- Speed: without `MemoryMap`'s work on every instruction, the emulator runs at about 3.5 times a real Apple II (measured, M4); without the hook checks, about 9% faster again. Windowed runs can now be throttled to Apple II speed (`speed`, 1.0 = about 1.023 MHz, checked against AppleWin); `make boot-lode-runner-throttled` next to the unthrottled `make boot-lode-runner`; `frame_rate` 40 by default for a smooth display.
- Milestone: Bandits runs past its first load of code over code, which `MemoryMap` used to refuse, into the game itself -- right up to Game Over.
- New documents: `docs/instrumentation-ideas.md`, a braindump of the design ideas (the user's, Claude's, and two other models'); `docs/instrumentation-map.md` with diagrams of the old instrumentation and `docs/diagrams/inner-loop.html`, which traces seven instructions through the inner loop.
- Tests: 142 before, 140 after (tile, collector and write-protect tests gone; throttle, trap, `is_code` and `executing` tests new).
- Learned (process): a change list before every patch, naming each deletion and marking anything beyond what was agreed; `&&` between dependent shell commands; when a patch reaches the end of a file, the real file as its base, not the copy from the dump.

## Before the redesign: the road so far

- 2026-09-26 -- Lode Runner plays a real game from its disk image: a stand-in for the game's RWTS at `$B7B5` serves sector reads from `DiskImage`. Bandits runs from Total Replay's ProDOS files, through a stand-in for the MLI at `$BF00`. `op_hook` and the time machine removed.
- 2026-09-24 -- Every function signature in `src/papple2/` has type hints.
- 2026-09-23 -- The new direction: `papple2` as a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example and XekriRedmane's `main.nw` as the answer key. `make patch`. Lode Runner boots after two CPU fixes (stack wrap in `pull_word()`, decimal mode). The window is polled every 1000 loop passes instead of on every instruction. Manual checks became scripts.
- 2026-09-15 -- `README.md` rewritten for GitHub; the D/L hotkey and text/hi-res mixed-mode bugs fixed.
- 2026-09-14 -- All tests on pytest, with shared fixtures. Robotron and its Excel bridge moved into a separate private project.
- 2026-09-12/13 -- The first fully code-only run (an assembled program, a scripted key, no window, no Robotron). Robotron specifics out of the core. Tests for soft switches and the hi-res pages.
- 2026-09-11 -- Emulator core and pygame window separated: `papple2` runs headless.
- 2026-09-06 -- `papple2.toml` instead of hardcoded Windows paths; circular imports untangled, star imports replaced.
- 2026-09-03/05 -- Revived after six years at rest (it began in 2019, building on ApplePy); an installable package.
