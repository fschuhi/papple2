
# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M2.5 -- Emulator refactoring (preparation for M3, done 2026-09-11)

~~Split `Emulator.event_loop` (checkpoints, `cpu.do_next_step`, state machine) from the pygame window layer, across four slices: (1) `Emulator` constructs and runs headless; (2) `src/papple2/Window.py` (`PygameWindow`/`NoWindow`) extracted, key polling returns `pysm` `Event`s instead of the state handlers touching pygame directly; (3) loop split into `run(until=None)`/`event_loop()` with `after_instructions`/`at_address` checkpoint helpers and `Emulator.press_key`; (4) `EmulatorStates` composes a `StateMachine` instead of subclassing one, states renamed `Running`/`Stopped`, checkpoints dispatch a `breakpoint` event instead of hard-returning.~~ **Done when:** ~~all four slices in, `make run` unchanged, `make test` green (68 tests).~~ See `HISTORY.md` for the full account.

## M3 -- Silent mode

- **Scripted keys.** New checkpoint class `KeyScript` in `Checkpoints.py`: takes a list of `(instruction_count, ascii_code)` pairs and calls `emulator.press_key` when `emulator.instructions` reaches each count. `RecordedKeys` (cycle-based, Robotron-specific) stays untouched for M4.
- **First silent test, which is also the usage documentation.** `tests/test_emulator_silent.py::test_keypress_reaches_program`: assemble with `Assembler` a small program that loops reading `$C000` until the high bit is set, stores the byte at `$0300`, touches `$C010` to clear the strobe, then loops forever at a known address; load it, build `Emulator(no_display=True)`, add a `KeyScript` that presses `'A'` after a few hundred instructions, `run(until=at_address(<loop address>))`, and assert `mem[0x0300] == ord('A') | 0x80`. Write the test's docstring as a walkthrough: this is the first document that shows how to use `papple2` from code. _Needs investigation, carried over from M2.5's "before starting" (never actioned):_ this test uses `Assembler`, which is currently commented out in `manifest.lst`; uncomment it there, and pin the installed `pysm` version in `requirements.txt` so the README being read matches the library being used.
- **Optional second test:** boot `A2ROM.BIN` silently (reset vector at `$FFFC`), run for N instructions, press a key, assert that the ROM stored it in the input buffer at `$0200`. _Needs investigation_ once the first test is green: how many instructions the ROM needs before it polls the keyboard.
- **`--nodisplay` in `Robotron.py`:** now means "run silently; only a checkpoint can stop the loop" (no keyboard, so no Print key). Keep `--exit` as the way to skip the loop entirely.
- We don't have docs on how to use the emulator yet, so the silent tests should be seen not only as insurance against regression but as a documentation feature of `papple2`.
- _Already done, no new work needed:_ `pygame.init()` is already conditional on `no_display` (fixed during M1) -- `ACTION_PLAN.md`'s M3 item about this is stale.

**Done when:** the emulator can run to a breakpoint or for N instructions without opening a window, and a test can feed keypresses from code and check memory afterwards.

**Look at first:** `HISTORY.md`'s M2.5 entry, then `Emulator.run`, `Checkpoints.KeyScript`, `SoftSwitches.read_byte`.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Memory.write_byte2` looks like an older version of `write_byte`. Check whether anything calls it; remove in M4 if not.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
