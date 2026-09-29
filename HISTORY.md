# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

- The detailed entries up to 2026-09-26 are at the git tag `pre-redesign`: `git show pre-redesign:HISTORY.md`.

---

## 2026-09-29 (third session) -- Every test module in `pytest` style; the `CPU` half of the hooks

- `tests/test_memory.py` and `tests/test_assembler.py` converted from `unittest` to plain `pytest` functions; no test module uses `unittest` any more. In `test_assembler.py` the helpers became module functions, the star import became explicit imports, the unused `dump_chromatix01_state` went, and the printing helper `test_dump` became `dump_state`, so the runner no longer collects it as a test (the two commented-out `dump=` calls now name it).
- `CPU` counts instructions: `instruction_count`, zeroed like `cycles` in `__init__` and `reset()`, increased at the start of `do_next_step()`, so the first instruction is number 1. Named so it is not confused with `Emulator.instructions`, which every `run()` call resets. About 2-3% slower (medians 3.32 s without, 3.38 s and 3.43 s with, in one sitting; the times rose during the sitting, so the figure is rough). Accepted: every position in the design rests on this count.
- `CPU` has the hook list `after_instruction`, called at the end of `do_next_step()`, after the memory hooks of that instruction. A hook gets no arguments and reads `instruction_count`, `last_PC` and `last_opcode` from the `CPU`; an experiment keeps the `CPU` in `self.cpu`. `reset()` keeps the hooks. Chosen over `hook(cpu)` because it follows the design note, and a quick `timeit` (4,000,000 calls, one hook) found it slightly faster, not slower. Not measured on Lode Runner: the user decided that the cost of each small step tells us little; what counts is the total, and we pay it anyway.
- Tests: `tests/test_instruction_count.py` and `tests/test_cpu_hooks.py`, all green.
- Learned (process, the user's feedback at the end of the session): the steps were small, but the explanations were not. What got in the way: dense sentences and idioms, a git command (`git stash`) used without explaining it, instructions that assumed the wrong state of the repo, measurement plans without a clear question, several open threads at once, and no big picture that ties each step to something the user can see on screen and start thinking in. Suggesting a fresh conversation was not asked for and read as pressure. For next time: one thing per message, plain words, say what a step is for before how it is done, and head for something visible.

## 2026-09-29 (second session) -- Hook lists in `Memory`; a first look at the attract play

- `Memory` has one hook list per kind of access, named after its method with an `after_` prefix (`after_read_opcode` ... `after_write_stack`). A read hook gets `(address, value)`, a write hook `(address, value, old_value)`. The old value comes straight from the memory list, so taking it does not flip a soft switch at `$C0xx`. Each list is tested before its loop.
- Speed: headless Lode Runner, median of five runs in the same sitting, 3.19 s before and 3.29 s after, about 3%. Accepted as the price every run pays for the hooks.
- Tests: `tests/test_memory_hooks.py`, written out, one test per method: each read method reports address and value to its own list, each write method the old value too, and hooks run in list order. A first version built the names from strings (`getattr`, parametrize); PyCharm can't follow such names, so it was replaced.
- A windowed run can pause at an instruction count: `scripts/boot_lode_runner.py --instructions N` stops as if Ctrl-X had been pressed, and the next Ctrl-X continues. In `Emulator.run()`, a met `until` is dropped when a window is open; headless runs still end at it.
- First experiment, run by the user: 4,000,000 instructions (the headless timing run) reach deep into the attract play -- iris wipe, the level being built, player and enemies moving, the first dig. No RWTS reads in that stretch: the attract play's level comes from memory.
- `after_instructions` and `at_address` moved from `core/emulator.py` to `papple2/debug/stop_conditions.py`. The core keeps the type `Until`: the shape of a condition, not the conditions themselves.
- Learned (process): compare old and new in the same sitting; against the baseline from an earlier sitting the cost looked like 4%, in the same sitting it was 3%. Designing how experiments get their hooks (`attach()`) before any experiment exists went in circles; decide it with the first one. Short answers, one point at a time.

## 2026-09-29 -- The instrumentation design; `CPU` and `Memory` speak in kinds

- Design session: the braindump became decisions, in `docs/instrumentation-design.md`. Three kinds of instrumentation: breakpoints and traps at the `Emulator`'s boundary, before the instruction; hooks inside it, after an access or after the instruction. After-hooks only, one hook list per kind of access, return values ignored, position = run plus instruction count. Ring buffers and counters are building blocks outside `core`. `pysm` stays: the one place where run control happens; an event queue would be a wrapper of our own, later.
- Pickling removed: `pickle`/`unpickle` in five classes, and the broken `save_hires_bytes`/`load_hires_bytes`. Snapshots will be designed fresh when an experiment needs them.
- `Memory` has one method per kind of access (`read_opcode`, `read_operand`, `read_pointer`, `read_data`, `read_stack`, `read_vector`, `write_data`, `write_stack`), and three 16-bit reads built from them (`read_operand_word`, `read_pointer_word` with the page wrap, `read_vector_word`). The CPU calls them; `CPU.read_byte`, `read_word` and `write_byte` are gone. Immediate operands are still reported as data reads, on purpose.
- The disassembler reads the memory list directly, and no longer switches the soft switches off around its reads.
- Speed: headless Lode Runner, 4,000,000 instructions, median of five runs 3.19 s before and 3.16 s after, so no measurable cost. `scripts/boot_lode_runner.py` now prints two decimals.
- Tests: every kind of access reaches the same memory; word reads take the low byte first; the pointer read wraps within the page.
- Learned (process): the noise between runs alone spans about 6%, so compare medians of five runs. Checking for callers before a change (`grep`) found the disassembler reading through the CPU before it could become a problem. A pushed commit can still be reviewed in PyCharm's Log, and `git revert` is the safe way back.

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
