# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file.

---

## 2026-09-15 -- make run-text verified; D/L hotkey and text/hires mix-mode bugs fixed

- Out-of-band session, working from `filesdump.txt` alone (no memory of any other papple2 session), triggered by `make run-text` (`tests/test_text.py`) showing a screen full of inverse `@` after `Display.update_text()` and `init_chars()` were re-enabled (they'd been commented out with "ACHTUNG: momentan text komplett ausgeschaltet" -- turning them back on was done just before this session, not during it). Confirmed the inverse-`@` wall itself is expected Apple II behavior, not a bug: the ROM's own cold-start self-test leaves `$00` across memory, and only BASIC's `HOME` clears it to spaces -- the Monitor never does. Also confirmed `Ctrl-B`, not a bare `B`, is this ROM set's shortcut from the Monitor into Integer BASIC.
- Found and fixed a real bug in `PygameWindow.poll()`: `D` and `L` were unconditionally reserved for debug hotkeys (`EmulatorStoppedState.on_d`, and the externally-attached `'l'` hook -- see `tests/test_emulator_debug_keys.py`), even while Running, silently swallowing those letters instead of passing them to `press_key()` -- meaning `LIST`, `LOAD`, `DEL`, or any variable name containing `D`/`L` could never be typed into the Monitor or BASIC. Fixed by gating the reservation to the `Stopped` state only, via a new `PygameWindow.debug_hotkey_event()` static method, deliberately pygame-window-free so the gating itself is covered by a real automated test (`test_debug_hotkey_event_only_fires_while_stopped`) rather than only the manual `make run-text`/`make run` checks. `README.md`'s "Settled decisions" updated with the scope of this reservation.
- Found and fixed a second, more serious bug that re-enabling `update_text()` surfaced: its mode check (`self.text or not self.mix or not row < 20`) rendered every text-page write as a glyph whenever `mix` was *off* -- backwards from real Apple II behavior, where a text-page write should only be visible in full `text` mode or the bottom four rows of `mix` mode, and otherwise not visible at all. Invisible for as long as `update_text()` was commented out; surfaced the moment it was turned back on, corrupting `make run`'s Robotron splash screen with hires and text interleaved across the full screen height -- confirmed impossible on real hardware. Fixed: `self.text or (self.mix and row >= 20)`. `make run` verified clean afterward.
- Not fixed, flagged for a future session: `determine_states_from_kmods()` exists identically in both `apple.py` and `window.py` -- almost certainly a leftover duplicate from before `window.py` was split out (M2.5), not something either bug fix above touched.

## 2026-09-14 -- probotron carve-out completed

- Deleted the migrated files from `papple2`: `examples/Robotron/` (all five files), `tests/test_robotronxl.py`, the Robotron-specific `data/bin`/`data/do`/`data/img` files, `docs/Robotron/*`, `pyxll/` entirely -- all now live in `probotron`, pushed to GitHub. Took about two minutes; `MIGRATE_ROBOTRON.md`'s inventory of what moves made it a checklist rather than a decision.
- `make test`, `make run`, and `make filesdump` all verified green afterward. `make excel` removed from the `Makefile` by hand -- PyXLL was the only reason it existed here, and PyXLL support now lives in `probotron`.
- `ACTION_PLAN.md`, `GOALS.md`, and `TODO.md` updated to reflect M7.5 done and M8 (documentation) unblocked; `MIGRATE_ROBOTRON.md` deleted now that its plan is carried out -- see the two entries below for what it described and decided.

## 2026-09-14 -- Robotron + Excel carve-out decided

- Decided to carve Robotron and the Excel/PyXLL bridge out of `papple2` into their own repo, rather than finishing M7 (the Excel bridge) in place. Motivation: the near-term interest is the Lode Runner disassembly, and Excel/Robotron work was blocking that, not enabling it. Full plan (what moves, what stays, what's already done, open questions) written to `MIGRATE_ROBOTRON.md` for a dedicated future session. `ACTION_PLAN.md` gained M7.5 for the migration; M7 marked superseded rather than deleted (it was real, scoped work, just work that's leaving); M8 (Documentation) noted as depending on M7.5 being done first, since it needs to describe the post-carve-out surface.
- Added `tests/test_robotron.py`: a minimal `@pytest.mark.manual` test that boots `Emulator(no_display=False)` with the real `ROBOTRON.BIN` and calls `emulator.run()` with no `until` -- same as the old `make run` did, but with zero `workbench`/`tiles`/`pyxll` involvement. This is what makes the carve-out safe: `papple2` keeps a real (if manual) check on the with-window code path without the Robotron workbench or Excel bridge. Registered via `pyproject.toml`'s new `[tool.pytest.ini_options]` (`markers`, `addopts = "-m 'not manual'"`), so `make test` skips it automatically and `make run` (repointed) runs it deliberately. Found along the way: `examples/Robotron/Robotron.py` -- what `make run` used to invoke -- already required `pyxll` installed just to *boot the window*, since it imports `RobotronXl.py`, which imports `pyxll` unconditionally at module level. Confirmed a fresh, minimal test was the right call rather than extracting the existing entry point.
- `ROBOTRON.BIN` distribution resolved without a code change: `papple2.toml`'s `data_dir` (already gitignored, per-machine) can point at wherever the file actually lives once it's in the new repo -- no need to redistribute a still-copyrighted binary via GitHub.

## 2026-09-14 -- Theme 1 finished

- Added `assemble`/`make_emulator`/`run_steps` factory fixtures to `conftest.py`, then converted `test_time_machine.py`, `test_mem_access_collector.py` (its own `make_mem_access_emulator` wrapper fixture on top, for the `mem_access.enable_hooks()` every test there needs), `test_emulator_debug_keys.py` (no fixture needed -- never touches `Assembler`), and `test_tiles.py` on top of them. `test_emulator_silent.py` converted too, split between bare `Emulator(no_display=True)` calls and the shared `make_emulator` fixture, depending on which of its nine tests actually assembled a program. `test_softswitches.py` and `test_display_memory.py` got their own smaller local fixtures (`display`/`speaker`/`switches`, and `apple2`) instead of the shared ones. `make test` green throughout, in small batches.
- Deleted `tests/test_robotron_waves.py` outright rather than converting it: its one test was already `@unittest.skip`'d, contained an unconditional `sys.exit(0)` mid-test (would have killed the whole `pytest` process if ever unskipped), and everything after that `sys.exit(0)` -- including the file's only assertion -- was genuinely unreachable. Confirmed with the project owner: the wave-select patch idea it was experimenting with had already been abandoned because of memory-layout interference with other Robotron functionality; the code stays out of both `papple2` and the future Robotron repo.
- Type-hints gap (open since the M7 session) turned out wider than expected, and inconsistent with itself: today's own new fixtures don't all have type hints (`test_time_machine.py`'s does, `test_tiles.py`'s doesn't, for example), on top of the pre-existing gap in `conftest.py`'s original `memory`/`cpu` fixtures. Elevated from a single `TODO.md` bullet to its own section with a concrete inventory and an explicit scope question (does the mandate reach test fixtures at all?), earmarked for its own dedicated session rather than a quick pass.

## 2026-09-14 -- pytest carryover (Theme 1, partial)

- Converted the remaining 11 `test_cpu_*.py` files (`test_cpu_jump_call.py`, `test_cpu_system.py`, `test_cpu_status_flags.py`, `test_cpu_bugs.py`, `test_cpu_branch.py`, `test_cpu_register_transfer.py`, `test_cpu_logical.py`, `test_cpu_load_store.py`, `test_cpu_inc_dec.py`, `test_cpu_shift.py`, `test_cpu_arithmetic.py`) from `unittest.TestCase` to native `pytest`, using the `memory`/`cpu` fixtures from `conftest.py` (the M5 template). Done across four batches, each followed by a green `make test` run.
- Parametrized wherever a clean shared table existed across the ops in a file: `test_cpu_status_flags.py` (`CLC`/`CLD`/`CLI`/`CLV`/`SEC`/`SED`/`SEI`), `test_cpu_branch.py` (all 8 branch ops), `test_cpu_register_transfer.py` (`TAX`/`TAY`/`TXA`/`TYA`), `test_cpu_inc_dec.py` (`INC`/`DEC` share one table, `INX`/`INY`/`DEX`/`DEY` another), and in `test_cpu_arithmetic.py`, `CMP`/`CPX`/`CPY` (one shared table) plus `ADC`/`SBC` (each parametrized on its own, since their cases don't reduce to one table). `test_cpu_logical.py` and `test_cpu_shift.py` left as plain functions -- their ops don't share a uniform table.
- Added a file-local `loaded_memory` fixture in `test_cpu_load_store.py` for the pre-loaded 5-byte test block, rather than adding it to the shared `conftest.py`.
- Found and fixed a real bug while parametrizing `test_SBC_without_BCD`: the original test's second case never set `carry_flag` explicitly, silently relying on the value left over from the first case -- broke when pulled out as an independent row; fixed by making the inherited `carry_flag = 1` explicit in that row.

## 2026-09-13 -- M7 (continued)

- Converted the remaining `@xw.func` functions in `RobotronXl.py` to PyXLL's `@xl_func`, in four batches, each followed by a green `make test` run: the plain read/query functions (`get_disassembly`, `get_memory_map`, `get_annotations`, `max_cycles`, `count_mem_accesses`); the functions taking cycle/byte-range arguments (`get_mem_access_log`, `get_mem_access_counts`, `get_screen_read_counts`, `get_screen_write_counts`, `get_access_colors`, `get_bytes`); the memlog-dialog functions (`create_memlog_dialog`, `send_memlog_dialog_event`, `get_memlog_lines`, `get_memlog_cursor_pos`, `find_pc_forward`, `find_pc_backward`); and the three `ndim=2`/transpose functions (`get_touch_count`, `get_first_cycles`, `get_last_cycles`), which PyXLL expresses as `var[][]`/`var[]` array types plus the `@xl_func` decorator's own `transpose=True` option, instead of xlwings' separate `@xw.arg`/`@xw.ret` decorators. `RobotronXl.py` no longer has a single `@xw.func` left. The now-dead `import xlwings as xw` was removed from both `RobotronXl.py` and `excel.py` (the latter's import was already unused before today); `xlwings` was already absent from `requirements.txt`.
- Added `tests/test_robotronxl.py`, the first test coverage this bridge layer has ever had: parametrized guard-path and smoke tests for every converted function, built on a module-scoped `running_workbench` fixture (and a `memlog_dialog_ready` fixture on top of it for the dialog-dependent functions).
- The new tests found three real, pre-existing bugs, all fixed: `MemAccessCollector.max_cycles()` crashed (`IndexError`) with no recorded memory accesses, now returns `0` like its sibling `count_mem_accesses()` always did; `RobotronXl.get_memlog_lines()` crashed the same way when the memlog dialog's `total_lines` is `0`, now returns `[]`; `RobotronXl.get_attribute_from_info()` (and the unused, dead `safe_get_info()`) called `emulator.memory_map`, an attribute that doesn't exist on `Emulator` (the real one is `.map`) -- meaning `get_touch_count`/`get_first_cycles`/`get_last_cycles` likely never worked, in the xlwings version either. Also fixed in passing: a missing closing parenthesis in `create_memlog_dialog`'s "reused" status string, and `validate_workbench()` added to the three array functions, which were missing it while every other converted function already had it.
- Parked in `TODO.md`, not fixed: `RobotronXl.validate_memlog_dialog()`'s auto-create-if-missing fallback is commented out, so calling most of the memlog functions before `create_memlog_dialog` has run crashes with a raw `AttributeError` instead of a clean Excel error.
- Not yet done: confirming any of this from a real Excel workbook (only `start_emulator` has been so far), and deciding whether `ExcelContext`/`raise_error` is still worth keeping now that everything's converted.

## 2026-09-12 -- M6

- Added a plain-language docstring to `tiles.py` (tile/stretch/call tree), plus `tests/test_tiles.py` building tiles from a small assembled program with a branch.
- Two findings surfaced along the way, deliberately not fixed (M6 excludes redesigning tiles/stretches): "stretch" as a concept is doubtful outside the compact JSR/RTS case; `update_heads_and_tails` only marks a tile `is_tail` if it already has a `link_prev`, so a fully standalone tile is head-only.
- One real slip mid-session: removed `TYPE_BRANCH_OVER_RTS`/`TYPE_BRANCH_OVER_JMP`/`TYPE_SHOWTEXT` as apparently unused, which broke `make run` -- they're tags `workbench.py` needs for manual tile-bridging. Restored.
- `make test` green (102 tests), `make run` verified.

## 2026-09-12 -- M5

- `Robotron.py` moved to `examples/Robotron/`; `make run`/PyCharm's run config repointed to `-m examples.Robotron.Robotron` (running it from `src/papple2` only ever worked because `-m` happened to put the repo root on `sys.path`).
- Added tests for the four areas from `GOALS.md`: soft switches and hi-res memory (`test_softswitches.py`, `test_display_memory.py` -- the hires pages are a scriptable buffer under `no_display=True`, independent of pygame rendering); `TimeMachine`/`MemAccessCollector` (`test_time_machine.py`, `test_mem_access_collector.py`, deliberately skipping the Excel/Graphviz-feeding views); confirmed the existing `test_cpu_*.py` suite already had full per-opcode coverage and closed the one gap found (`test_TSX`'s missing N/Z check).
- Decided the with-window half stays manual, via `make run` + Robotron; documented in `README.md`'s new "Testing strategy" section.
- Started converting the suite from `unittest` to native `pytest` (`conftest.py`, `test_cpu_stack.py` as the template); rest tracked in `TODO.md`.
- Two findings parked in `TODO.md`, not fixed: an off-by-one in `Memory.write_byte`'s hi-res range check, and a boundary quirk in `TimeMachine.restore_prev_state`.
- `make test` all green (100 tests).

## 2026-09-12 -- M4

- Removed Robotron-specific code from the core (`on_l`, two `Memory.write_byte` guard ranges, `handle_rts`'s crash-on-empty-stack assertion -- the last one was a real bug, not just a Robotron assumption). Also removed dead code found along the way: `write_byte2`, a `sys.exit(0)` trap in `CPU.write_byte`.
- New extension points replace what was removed: `EmulatorStates.stopped_state`/`running_state` let external code attach debug-key handlers (`pysm`'s own `handlers` dict) and write guards (a `CPUHook` subclass) without touching the core. Demonstrated in `tests/test_emulator_debug_keys.py`.
- Modules renamed to lower case and split into `papple2.core`/`papple2.debug` (PyCharm refactor); showcase moved to `examples/Robotron/`; `Statemachines_example.py` and the dead `Papple2.py` stub removed. `Robotron.py` itself still needs moving -- next session's first task.
- `make test` green, `make run` verified.

## 2026-09-12 -- M3

- Added `KeyScript` to `Checkpoints.py`: a checkpoint driven by `emulator.instructions` rather than `cpu.cycles`, so any assembled program can have keys scripted onto it, not just Robotron.
- Added `tests/test_emulator_silent.py::test_keypress_reaches_program`, the first fully code-only run of `papple2` -- assembled with `Assembler`, no pygame, no ROBOTRON.BIN. Its docstring is written as a walkthrough, doubling as the first usage documentation for driving the emulator from code.
- Found and fixed a real hang: in headless mode, a checkpoint requesting a stop (`execute=False`) without an `until` in play would flip the state machine to `Stopped` but then spin forever, since `NoWindow` never produces a `ctrlx` or `halt` event to resume or end it. `Emulator.run` now treats that case as a real halt when there's no window to recover from. Covered directly by `tests/test_emulator_silent.py::test_checkpoint_stop_halts_headless_run`, which registers a plain "stop after N instructions" checkpoint with no `until` at all.
- `--nodisplay`'s help text in `Robotron.py` now states what it actually implies: no keyboard, no pause/resume, a registered checkpoint is the only way execution stops.
- `make run` unaffected for the windowed path; `make test` all green.

## 2026-09-11 -- M2.5

- Split `Emulator.event_loop` into the emulator core and the window/pygame layer, across four slices: headless construction (`self.screen` removed, `Display.show_status`/`clear_status` guarded, `time.monotonic()` replaces `pygame.time.get_ticks()`); `src/papple2/Window.py` extracted (`PygameWindow`/`NoWindow`, sharing `poll()`/`present()`/`status()`); the loop split into `run(until=None)`/`event_loop()` with `after_instructions`/`at_address` checkpoint helpers and `Emulator.press_key`; `EmulatorStates` now composing a `StateMachine` instead of subclassing one, with states renamed `Running`/`Stopped` and checkpoints dispatching a `breakpoint` event instead of hard-returning from `run`.
- `make run` behaves exactly as before with the window open; `make test` green (68 tests, four new in `tests/test_emulator_silent.py`).

## 2026-09-06 -- Imports untangled

- Untangled the circular import between `Emulator`, `Hooks`, `Checkpoints`.
- Replaced `from X import *` with explicit imports.

## 2026-09-06 -- M2

- Replaced hardcoded Windows paths with `papple2.toml` (local, gitignored; `papple2.example.toml` committed instead), no `os.chdir` needed anymore. Also swept up `args.savemem`'s `dat\test.dat` (now under `data_dir`) and the Graphviz `PATH` hack in `Tiles.py` (removed; `dot` now found via `brew install graphviz`).
- Removed `util.msgbox`; would need Tkinter; no callers existed anywhere in the codebase.
- Vanilla `pygame` 2.6.1 doesn't build/run correctly under Python 3.14 yet (open upstream issue); venv recreated under Python 3.12 instead, resolved. Documented in `README.md`.
- `make run` opens the pygame window, runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution. The animated Robotron splash screen renders correctly on macOS.

## 2026-09-05 -- M1

- `src/papple2` is a real, installable package (`pyproject.toml`, editable install wired into the `Makefile`).
- Prefixed all internal imports with `papple2` (mechanical prefix only); star-imports (`import *`) kept as-is on purpose. Converting to explicit names is M4 work, not this.
- Split `tests.py` into per-class files under `tests/`, all green.
- `TestWaves.test_input_wave` marked `@unittest.skip`; left as-is, including the `sys.exit(0)` and the dead code after it. Revisit later, not now.

## 2026-09-03 -- Inaugural papple2 session

Revival of the emulator after the Robotron 2084 project went dormant. Full read-through of the code base with Claude (Fable 5.1). Result: `ACTION_PLAN.md` with milestones M1 (tests green on macOS) to M8 (documentation), ordered by cheapest visible value. The target-state list moved from `GOALS.md` to `ACTION_PLAN.md`; `GOALS.md` now holds only the vision and the session pointer; `TODO.md` holds the M1 tasks. Main findings: Windows-only paths, `pytest` missing from requirements, two identical `tests.py`, `from X import *` throughout, Robotron-specific behaviour inside `Memory.write_byte`. No code changed.
