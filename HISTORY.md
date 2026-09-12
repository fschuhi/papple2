# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

---

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
