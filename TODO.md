# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M2 -- The emulator boots on macOS (done on 2026-09-06)

- ~~Replace hardcoded Windows paths~~ -- introduced `papple2.toml` (local, gitignored; `papple2.example.toml` committed instead) holding `data_dir`/`trace_dir`, read once in `Robotron.__main__` and threaded explicitly through `start_emulator`, `Workbench.__init__`, and `save_results` -- no `os.chdir` needed anymore. Also swept up `args.savemem`'s `dat\test.dat` (now under `data_dir`) and the Graphviz `PATH` hack in `Tiles.py` (removed; `dot` now found via `brew install graphviz`).
- ~~Replace or remove `util.msgbox`~~ -- removed entirely; no callers existed anywhere in the codebase.
- ~~Status-bar font~~ -- no code change needed: `pygame.font.SysFont` already falls back silently when `"Source Code Pro"` isn't installed.
- ~~Two missing `papple2.`-prefix imports, found while testing the real boot~~ -- `Checkpoints.py`'s `from util import *` and `Robotron.py`'s `from RobotronXl import workbench, emulator` were leftovers from the M1 package migration; both fixed.
- ~~`Workbench.simulate_execution`'s `mm.post_op` bug (was in Scratchpad)~~ -- `mm` was never defined; replaced with the already-correct `self.map`.
- ~~pygame vs. Python 3.14~~ -- vanilla `pygame` 2.6.1 doesn't build/run correctly under Python 3.14 yet (open upstream issue); venv recreated under Python 3.12 instead, resolved. Documented in `README.md`.

**Done when:** ~~`python -m papple2.Robotron` opens the pygame window, runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution.~~ Confirmed -- the animated Robotron splash screen renders correctly on macOS.

## M2.5 -- Emulator refactoring (preparation for M3, planned 2026-09-11)

**Why:** `Emulator.event_loop` is two things in one method: the emulator (checkpoints, one instruction, `post_op`, state machine) and the window (pygame key polling, pygame clock, `pygame.display.flip`). Silent mode needs the first without the second. The state machine handlers also call `display.show_status` and read pygame modifier keys, which ties them to the window. This milestone separates the two; it does not change what the emulator does with the window open.

**Verified starting point (2026-09-11):** `Emulator(no_display=True)` raises `AttributeError: 'Display' object has no attribute 'screen'`. Cause: `Display.__init__` returns early in `no_display` mode before creating `self.screen`, but `Emulator.__init__` and `EmulatorStates.__init__` both do `self.screen = self.display.screen`. So `--nodisplay` has never worked through `Emulator`; the M1 tests bypass `Emulator` and build `Apple2` directly.

**Working rules for this milestone:** Discuss -> Approve -> Implement per slice. Drop-in replacements. `make test` green after every slice and `make run` still behaves as before after every slice (Ctrl-X stops/resumes, left/right rewind with the time machine on, `d` and `l` print, Print key exits). Read the `pysm` README's nested-state example before slice 4; do not rely on memory of how `pysm` nests states. Each finished slice gets a dated `HISTORY.md` entry.

**Before starting:** uncomment `src/papple2/Assembler.py` in `manifest.lst` (the M3 test uses it) and pin the installed `pysm` version in `requirements.txt` so the README being read matches the library being used.

- **Slice 1 -- `Emulator` constructs without a window.** Remove the two `self.screen = self.display.screen` lines (nothing reads `Emulator.screen` or `EmulatorStates.screen`; `Display` uses its own `self.screen`). Make `Display.show_status` and `Display.clear_status` return early when `no_display`, like `update`, `refresh_hires`, and `flash` already do. Replace `pygame.time.get_ticks()` in `Emulator.__init__` and `update_display` with `time.monotonic()` (seconds; adjust `elapsed_frame` accordingly; `last_ticks` is still pickled and `RobotronXl.load_state` sets it to 0, both fine). _Done when:_ a new test `tests/test_emulator_silent.py::test_constructs_without_window` builds `Emulator(no_display=True)` and loads `data/bin/ROBOTRON.BIN`; all green.
- **Slice 2 -- Window layer extracted.** New module `src/papple2/Window.py` with two classes sharing three methods: `poll() -> list` returns the pending events as `pysm` `Event` objects (the pygame class contains exactly the key-mapping code that is in `event_loop` today, including the Ctrl-X, arrow, `d`, `l`, Print, and plain-key cases, plus a marker for `pygame.QUIT`); `present()` contains the body of today's `update_display` (flash, flip, frame pacing); `status(text)` forwards to `Display.show_status`. `PygameWindow` implements them with pygame; `NoWindow` returns `[]` and does nothing. `determine_states_from_kmods` moves into `PygameWindow` and its result travels in the `left`/`right` event cargo, so the state handlers no longer touch pygame. `Emulator.__init__` picks the class from `no_display`. _Done when:_ `event_loop` and the state handlers contain no `pygame` reference; `make run` unchanged; all green.
- **Slice 3 -- Loop split into `run(until=None)` and `event_loop()`.** `run` is the core loop: checkpoints, `cpu.do_next_step()`, `post_op()`, then `for event in self.window.poll(): self.states.dispatch(event)`, then `self.window.present()`. `until` is a callable `(emulator) -> bool`; `run` wraps it as a checkpoint that ends the loop when it returns `True`. Two helpers in `Emulator.py`: `after_instructions(n)` and `at_address(address)`, each returning such a callable. `event_loop()` becomes `return self.run()` so `Robotron.py` and `RobotronXl.continue_robotron` keep working unchanged. Add `Emulator.press_key(ascii_code)` that does what `on_key` does today (`Ascii2Apple2Ascii`, write to `softswitches.kbd`, print); `on_key` calls it. _Done when:_ `test_run_stops_after_n_instructions` and `test_run_stops_at_address` pass silently; all green.
- **Slice 4 -- State machine with real child states.** `EmulatorStates` becomes a plain class that owns a `StateMachine` (resolves the existing TODO comment in `EmulatorStates.__init__`). Two parent states, each a `StateMachine` used as a state, with two `State` children each: `Executing` with children `Running` (default; runs until an external event) and `RunningUntil` (entered by `run(until=...)`, i.e. a stop condition is armed); `NotExecuting` with children `Stopped` (default on entry) and `Rewinding` (entered by the first `left`/`right` event; further arrow keys are handled here; `ctrlx` from either child resumes). `breakpoint` and `halt` transitions as today. Handlers change the emulator only (`executing` flag, time machine enable/disable restoring, rewind steps) and report through `self.emulator.window.status(text)`; no `Display` or pygame access inside `Emulator.py`'s state classes. `on_l`'s Robotron zero-page dump stays as is (M4). _Done when:_ `make run` unchanged; `test_ctrlx_toggles_state` builds a silent `Emulator`, dispatches `Event('ctrlx')` twice, and asserts the leaf state names `Running` -> `Stopped` -> `Running`; all green.
- **Cleanup, one line:** after slice 4 check whether `Emulator.executing` still has a reader anywhere (none found in `Emulator.py`, `Workbench.py`, `Robotron.py`, `RobotronXl.py` on 2026-09-11); if not, remove it in a separate approved step.

**Done when:** all four slices are in, `make run` behaves exactly as before with the window, `Emulator(no_display=True).run(until=after_instructions(1000))` returns without touching pygame, and the tests above are all green.

## M3 -- Silent mode

- **Scripted keys.** New checkpoint class `KeyScript` in `Checkpoints.py`: takes a list of `(instruction_count, ascii_code)` pairs and calls `emulator.press_key` when `emulator.instructions` reaches each count. `RecordedKeys` (cycle-based, Robotron-specific) stays untouched for M4.
- **First silent test, which is also the usage documentation.** `tests/test_emulator_silent.py::test_keypress_reaches_program`: assemble with `Assembler` a small program that loops reading `$C000` until the high bit is set, stores the byte at `$0300`, touches `$C010` to clear the strobe, then loops forever at a known address; load it, build `Emulator(no_display=True)`, add a `KeyScript` that presses `'A'` after a few hundred instructions, `run(until=at_address(<loop address>))`, and assert `mem[0x0300] == ord('A') | 0x80`. Write the test's docstring as a walkthrough: this is the first document that shows how to use `papple2` from code.
- **Optional second test:** boot `A2ROM.BIN` silently (reset vector at `$FFFC`), run for N instructions, press a key, assert that the ROM stored it in the input buffer at `$0200`. _Needs investigation_ once the first test is green: how many instructions the ROM needs before it polls the keyboard.
- **`--nodisplay` in `Robotron.py`:** now means "run silently; only a checkpoint can stop the loop" (no keyboard, so no Print key). Keep `--exit` as the way to skip the loop entirely.
- We don't have docs on how to use the emulator yet, so the silent tests should be seen not only as insurance against regression but as a documentation feature of `papple2`.
- _Already done, no new work needed:_ `pygame.init()` is already conditional on `no_display` (fixed during M1) -- `ACTION_PLAN.md`'s M3 item about this is stale.

**Done when:** the emulator can run to a breakpoint or for N instructions without opening a window, and a test can feed keypresses from code and check memory afterwards.

**Look at first:** the M2.5 section above, then `Emulator.run`, `Checkpoints.KeyScript`, `SoftSwitches.read_byte`.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Memory.write_byte2` looks like an older version of `write_byte`. Check whether anything calls it; remove in M4 if not.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
