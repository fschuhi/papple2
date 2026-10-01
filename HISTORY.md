# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

- The detailed entries up to 2026-09-26 are at the git tag `pre-redesign`: `git show pre-redesign:HISTORY.md`.

---

## 2026-10-01 -- `read_immediate`: immediate operands are a kind of their own

- `Memory` has a ninth kind of access, `read_immediate`, with its list `after_read_immediate`; `Emulator.attach()` knows the name. The CPU reports the `$42` in `LDA #$42` there instead of through `read_data`.
- How: a flag, not split operations. `immediate_mode()` sets `CPU.immediate`, `do_next_step()` resets it with `branched` and `operand_length`, and the 11 operations with immediate mode read their byte through `read_data_or_immediate()`. `TODO.md` had planned to split each operation into reading the byte and using it (`lda_value(...)`); that would have doubled the 11 operations for the same cost (one extra method call either way). The user found the flag more readable, and on reflection Claude agreed: it follows the flags `cpu.py` already resets per instruction, and none of the 11 operations reads its operand twice.
- `scripts/lr_count.py` attaches `after_read_immediate`; the last-opcode workaround and `IMMEDIATE_OPCODES` are gone. Run by the user: 2316 addresses fetched as opcode and 2083 as operand, the same as on 2026-09-29, and 347 read as immediate (the first recorded figure); 4.18 s for the run, not compared with earlier sittings.
- Tests: one per call site (13: the 11 opcodes, plus `ADC` and `SBC` in decimal mode), each must report to `after_read_immediate` and not to `after_read_data`; and `LDA #$42` followed by `LDA $0300` reports the second read as data, which shows the reset. `read_immediate` in the kind tests of `test_memory.py` and `test_memory_hooks.py`. All green.

---

## 2026-09-30 -- Hot-loop optimization and dynamic Basic Blocks (Stretches)

- Optimization of the `lr_tiles.py` hot path: I noticed a 4% performance hit just from packing data into `NamedTuples` on every instruction. You suggested keeping raw tuples in the hot loop and converting them on the cold path. You also bypassed method call overhead by inlining `observe_instruction` and `tile_at`, and replaced set lookups for opcodes with a precomputed 256-byte array (`OPCODE_KIND`). This brought the 4,000,000-instruction run down to 4.77 seconds.
- The conceptual pivot: We discarded the academic graph-theory heuristics (SCCs, loop candidates, interval overlaps) that you initially generated, as they didn't suit dynamic 6502 execution. My intuition was that a leap landing inside a glided execution path should simply break the tile into two pieces. We committed to my vocabulary for this domain: tiles, gliding, leaps, and stretches.
- The Transformer pass: Instead of risking the hot loop's speed by breaking tiles on the fly, you implemented a post-run `transform_to_stretches` function. It mathematically slices overlapping tiles into strictly disjoint basic blocks (stretches) using all known entry points, accurately reconstructing the historical execution traffic by cascading the counts down the split pieces.
- Validation and Output: The noisy graph reports (`lr_loop_candidates.csv`, `lr_stitch_candidates.csv`, `lr_overlap_groups.csv`) were deleted. In their place, `lr_split_tiles.csv` and `lr_split_transitions.csv` are now generated. You extracted the ledger math validation into a standalone `check_stretch_consistency` function to guarantee zero overlaps and perfectly conserved traversals. 
- The Revelation: Running the transformer on Lode Runner yielded the exact same number of stretches as raw tiles. This proved that during the 4M-cycle attract play, the game's execution paths merge in perfect alignment with zero mid-instruction overlaps.

## 2026-09-30 -- The experiments as a group; `instruction_count_reaches`

- `scripts/count_lode_runner.py` renamed to `scripts/lr_count.py`, so the Lode Runner experiments (`lr_count.py`, `lr_trace_pc.py`, `lr_tiles.py`) group as `lr_*`. Each has a `make` target: `lr-count`, `lr-trace-pc`, `lr-tiles`. The `boot_*` scripts keep their names.
- The stop condition `after_instructions(n)` renamed to `instruction_count_reaches(n)`: the old name read almost like the hook `after_instruction`, with a different meaning. The count is `Emulator.instructions`, which every `run()` resets, so `n` counts the instructions of this run.

## 2026-09-29/30 -- Breakpoints; a readable HTML map

- Milestone, run by the user: breakpoints, step 5 of the redesign. With them, the three kinds from the design note are all in place: breakpoints and traps at the `Emulator`'s boundary, hooks inside the instruction. `Emulator.add_breakpoint(breakpoint)` puts the object's `should_break(pc)` into `Emulator.breakpoints`, just as `attach()` puts hook methods into the hook lists; the method name is the interface (duck typing). Before each instruction, before the traps, `run()` asks every breakpoint, and stops the same way `until` does if any said `True`. So a breakpoint at a trap's address stops before the trap moves PC away. PC is passed because it is about to change ("pass only what is gone afterwards"). `break_at(address)` lives in `stop_conditions.py`, outside `core`. Not in the first iteration: a hit counter ("stop on the n-th visit"). `attach()` stays reserved for hooks.
- The HTML execution map: an info line above the map shows address and counts under the mouse, black cells included (the script works out the address from the cell's position, so the cells carry only their counts). The map scrolls in its own box, with sticky row and column labels, so the address grid stays in view. The colours stay as they are; the map does its job.

## 2026-09-29 -- The first execution map; `Emulator.attach()`

- Milestone, run by the user: the first real output of the new instrumentation. `scripts/count_lode_runner.py` boots Lode Runner headless, runs 4,000,000 instructions from the start (the attract play), counts per address how often it was fetched as an opcode and as an operand, and saves a 256 x 256 map as a PNG (one pixel per address, row = page) and as an HTML table with tooltips. Step 5 (breakpoints at the boundary) was not needed first: the hook lists are public, and `until` already stops the run.
- What the map shows: 2316 addresses ran as opcode, 2083 as operand, none as both. `$0800`-`$0802` is the `JMP $2800` the file starts with; `$2800`-`$2831` is the relocation routine, which lies in hi-res page 1 and is overwritten by graphics later, so the map records history, not what is in memory at the end. The game's code runs in `$5F32`-`$8B0B`; nothing in `$0000`-`$1FFF` apart from `$0800`, nothing above `$8B0B`, no ROM, no RWTS reads. The run is deterministic: a second run gave the same map.
- Speed: with the two counting hooks, 4.05 s for the run, against about 3.4 s without hooks in earlier sittings (rough). The script also prints the speed against a real Apple II from the cycle count (cycles / 1,023,000): 12,815,538 cycles, 12.53 s on a real Apple II, 3.09 times as fast.
- `Emulator.attach(experiment)` and `detach(experiment)`: each method named after a hook list (`after_read_opcode` ... `after_write_stack`, `after_instruction`) goes into that list in `Memory` or `CPU`, and comes out again on `detach()`. A method starting with `after_` that matches no list is refused before anything is attached. Both log one line at INFO through Python's `logging` (silent unless a script turns INFO on). Decided with the first experiment, as planned; matching by name is fine for setup code. Named hook types (`ReadHook` ...) were dropped: experiments are objects that expose several hooks, and the naming convention is the interface. Tests: `tests/test_attach.py`.
- Immediate operands (the `$0B` in `LDA #$0B`) are read with `read_data`, so they showed as black holes after their opcode (found by the user at `$8438`). `ExecutionCounts` works around it: it remembers the last opcode and counts a data read as immediate when that opcode has immediate mode and the read is the byte right after it. Shown in green; a byte of more than one kind in red.
- The browser's own tooltips are unreliable on 6-pixel cells (they need the mouse to stop). The combination of blue, orange and green doesn't work either. Both are in `TODO.md`.

## 2026-09-29 -- Every test module in `pytest` style; the `CPU` half of the hooks

- `tests/test_memory.py` and `tests/test_assembler.py` converted from `unittest` to plain `pytest` functions; no test module uses `unittest` any more. In `test_assembler.py` the helpers became module functions, the star import became explicit imports, the unused `dump_chromatix01_state` went, and the printing helper `test_dump` became `dump_state`, so the runner no longer collects it as a test (the two commented-out `dump=` calls now name it).
- `CPU` counts instructions: `instruction_count`, zeroed like `cycles` in `__init__` and `reset()`, increased at the start of `do_next_step()`, so the first instruction is number 1. Named so it is not confused with `Emulator.instructions`, which every `run()` call resets. About 2-3% slower (medians 3.32 s without, 3.38 s and 3.43 s with, in one sitting; the times rose during the sitting, so the figure is rough). Accepted: every position in the design rests on this count.
- `CPU` has the hook list `after_instruction`, called at the end of `do_next_step()`, after the memory hooks of that instruction. A hook gets no arguments and reads `instruction_count`, `last_PC` and `last_opcode` from the `CPU`; an experiment keeps the `CPU` in `self.cpu`. `reset()` keeps the hooks. Chosen over `hook(cpu)` because it follows the design note, and a quick `timeit` (4,000,000 calls, one hook) found it slightly faster, not slower. Not measured on Lode Runner: the user decided that the cost of each small step tells us little; what counts is the total, and we pay it anyway.
- Tests: `tests/test_instruction_count.py` and `tests/test_cpu_hooks.py`, all green.
- Learned (process, the user's feedback at the end of the session): the steps were small, but the explanations were not. What got in the way: dense sentences and idioms, a git command (`git stash`) used without explaining it, instructions that assumed the wrong state of the repo, measurement plans without a clear question, several open threads at once, and no big picture that ties each step to something the user can see on screen and start thinking in. Suggesting a fresh conversation was not asked for and read as pressure. For next time: one thing per message, plain words, say what a step is for before how it is done, and head for something visible.

## 2026-09-29 -- Hook lists in `Memory`; a first look at the attract play

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
