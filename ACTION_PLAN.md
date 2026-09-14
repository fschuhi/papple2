# papple2 -- Action Plan

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file is the route from where `papple2` stands today to the target state described in `GOALS.md`. It lists milestones in the order we work on them. Each milestone says what "done" means and what to look at first. Details that only matter once we reach a milestone are left open on purpose and are filled in when we get there. Concrete, startable tasks for the current milestone live in `TODO.md`; finished work is recorded in `HISTORY.md`.

**Working rule for this plan:** Each milestone must leave the project in a runnable state with the tests green. We do not start a milestone while the previous one is unfinished, unless we decide so explicitly.

---

## 1. Where the project stands (September 2026)

- The code was written on Windows. File paths use backslashes and point to `bin\...` while the files live in `data/bin/`. `util.msgbox` uses a Windows-only call. Logging writes to `trace\...`. The emulator cannot start on macOS as it is.
- `make test` fails because `pytest` is missing from `requirements.txt`. The test files use `unittest`, not `pytest`.
- `src/papple2/tests.py` and `tests/tests.py` are identical copies.
- ~~All modules import each other as top-level modules (`from Memory import *`), not as members of the `papple2` package. `Emulator`, `Hooks`, and `Checkpoints` import each other in a circle.~~ **2026-09-06** fixed in focused session after completing M2
- Robotron-specific code sits inside the core emulator: protected memory ranges in `Memory.write_byte`, Robotron addresses in `Emulator.on_l`, an assertion in `Emulator.handle_rts` that only holds for Robotron.
- `pygame.init()` runs unconditionally in `Apple2.__init__`. A `no_display` flag exists and is passed down to `Display`, but the window-less mode is untested and incomplete.
- `pysm` state machines are used in three places: the run/stop state of the emulator, the scrolling memory-log dialog for Excel, and a learning example file.
- The Excel bridge (`RobotronXl.py`, `Excel.py`) uses `xlwings`, which I no longer use.
- Tiles and stretches (`Tiles.py`) are the building blocks for the Graphviz call trees. A tile is a run of instructions that always execute in sequence (a "basic block"); a stretch is a chain of tiles that always continue into each other. They depend only on `MemoryMap` and `util`.

## 2. Target state

This list moved here from `GOALS.md`. It is preliminary; more constraints will be added while we work through the code.

- The code base is reviewed and refactored, broadly according to common practice for naming and organizing Python code in a project like `papple2`.
- Non-standard debugging concepts (tiles, stretches, time machine, memory access log) are understood, documented, and tested -- or removed when unnecessary or easier to accomplish differently.
- Functionality is split sensibly between core emulator and additional debugging tools.
- `papple2` can be used as a library in other Python projects such as `load-runner`.
- `papple2` has good pytest coverage, including (1) 6502 specifics, (2) Apple II specifics, (3) running disk images with and without the pygame window, (4) breakpoints and other debugging tools.
- The Robotron 2084 disassembly is the showcase for how to use the emulator. It does not have to be part of the project, but it can be, as an example.
- The emulator runs both with the pygame window and keyboard input, and completely silently with keypresses sent from code.
- The Excel bridge uses PyXll instead of xlwings.
- `README.md`, `GOALS.md`, `TODO.md`, and `ACTION_PLAN.md` are complete and current.

**2026-09-14 note:** the Robotron showcase and Excel bridge no longer stay *in* the project (see M7.5) -- "it can be, as an example" above is superseded by the decision to carve both out into their own repo, which `papple2` depends on being usable *from*, same as `load-runner` would.

## 3. Milestones

### M1 -- Tests run and are green on macOS

**Done when:** `make test` runs `pytest` from the repo root and every test passes on the MacBook.

**Work items:**

- Add `pytest` to `requirements.txt`.
- Make the modules importable as a package (`from papple2.Memory import Memory`), or put `src` on the path in the `Makefile`. Decide which before touching files; the package form is what `load-runner` will need later.
- Convert `tests.py` into pytest files in `tests/`, named `test_<topic>.py` (for example `test_cpu_load_store.py`, `test_assembler.py`). Remove `src/papple2/tests.py`.
- Fix the file paths the tests use (`bin\ROBOTRON.BIN` -> `data/bin/ROBOTRON.BIN`, `tmp\...`).
- Tests that open a pygame window today (`Apple2(no_display=False)`) are changed to `no_display=True` or marked as needing the display.

**Look at first:** the two `setUp` patterns in `tests.py`; the `Makefile` test target.

**Suitable for a less powerful model:** yes, this is mostly mechanical work with clear pass/fail.

### M2 -- The emulator boots on macOS

**Done when:** `python -m papple2.Robotron` (or the equivalent command we settle on) opens the pygame window and runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution.

**Work items:**

- Replace all hard-coded Windows paths with paths relative to a single data directory.
- Replace or remove `util.msgbox`.
- Fix `logging.basicConfig` target path.
- Check that `pygame` and the "Source Code Pro" status font work on macOS; fall back to a default font if not.

**Look at first:** `Apple2.__init__`, `Workbench.__init__`, `Robotron.__main__`, `RobotronXl.start_emulator`.

### M3 -- Silent mode

**NOTE:** It's possible that, instead of this milestone, we might be able to do a small refactoring project first.

_In any case, this is a good moment to analyze control flow and display it as charts, to help me understand what I did years ago, at a point where I had just started to learn Python._

**Done when:** the emulator can run to a breakpoint or for N instructions without opening a window, and a test can feed keypresses from code and check memory afterwards.

**Work items:**

- Make `pygame.init()` conditional on `no_display` (or replace `pygame.time` use in the event loop with `time`).
- Give `Emulator.event_loop` a way to run without polling pygame events: a step count, a stop address, or a callback.
- Add a programmatic keypress path (write to `softswitches.kbd` the way `on_key` does).
- One pytest that boots silently, runs the Apple II ROM or a small assembled program, presses a key, and asserts on memory.

**Look at first:** `Emulator.event_loop`, `EmulatorExecutingState.on_key`, `SoftSwitches.read_byte`.

### M4 -- Split into core, debugging tools, and Robotron showcase

**Done when:** three clearly named parts exist (for example sub-packages `papple2.core`, `papple2.debug`, and an `examples/robotron/` directory), the core has no Robotron-specific lines, and `pysm` is only used in the debugging or showcase part.

**Work items:**

- Move Robotron-specific behaviour out of `Memory.write_byte`, `Emulator.on_l`, `Emulator.handle_rts` into hooks or into the Robotron code.
- ~~Untangle the circular import between `Emulator`, `Hooks`, `Checkpoints`. Replace `from X import *` with explicit imports.~~ **2026-09-06** fixed in focused session after completing M2
- Decide module names (lower case per PEP 8) and rename in one approved step.
- `Statemachines_example.py` and `Papple2.py`: move to `examples/` or remove.

**Decision already made:** `pysm` stays in the project. Open is only where the run/stop state machine lives (core or debug).

**Look at first:** the import graph (documented in the first session), `Emulator.__init__`.

### M5 -- pytest coverage

**Done when:** tests exist for the four areas from `GOALS.md`: (1) 6502 instructions and known bugs, (2) Apple II specifics (soft switches, display memory), (3) running a binary or disk image with and without the window, (4) breakpoints, time machine, memory access log.

**Work items:** decided per area when we get there; each area is its own approved step.

### M6 -- Tiles and stretches

**Done when:** `Tiles.py` lives in the debugging part, has a short docstring explaining tile, stretch, and call tree in plain words, and has at least one test that builds tiles from a small assembled program.

**Decision already made:** no redesign. Lower priority because tiles support disassembly work, not emulation.

### M7 -- Excel bridge via PyXll

~~**Done when:** the functions in `RobotronXl.py` are callable from Excel through PyXll on the Windows VM.~~

**2026-09-14 superseded:** the Excel bridge is leaving `papple2` entirely, along with the rest of the Robotron showcase, into its own repo (M7.5). Finishing it is that repo's concern from here on, not `papple2`'s.

**Note:** lowest priority, but not no priority. ~~The Excel bridge is part of the Robotron showcase for `papple2`.~~

### M7.5 -- Migrate Robotron + Excel bridge to their own repo

**Done when:** `examples/Robotron/`, the PyXLL/Excel bridge, and Robotron-specific data/docs live in a separate repo that depends on `papple2` as an installed package; `papple2` itself is back to macOS-only (no `pyxll`, no Windows branch in the `Makefile`); `tests/test_robotron.py` remains as `papple2`'s own manual smoke test of the with-window path.

**Work items:** see `MIGRATE_ROBOTRON.md` for the full plan -- what moves, what stays, what's already done, and what's still open.

**Look at first:** `MIGRATE_ROBOTRON.md`.

**Decision already made:** the near-term interest is the Lode Runner disassembly, not finishing the Excel bridge -- this milestone exists to remove that from `papple2`'s critical path, not to finish it in place.

### M8 -- Documentation

Runs alongside all milestones, not after them: `README.md` is rewritten once M4 has settled the structure; `GOALS.md` and `TODO.md` are kept current every session.

**Depends on M7.5:** the parts of `README.md` describing the Robotron showcase and the package split can't be finalized until the carve-out has actually happened -- documenting the current, mixed surface would just need redoing. Postponed until M7.5 is done.

## 4. Open questions

- Package layout for M1/M4: keep `src/papple2/` or flatten? Decide at the start of M1 with the `load-runner` use in mind.
- Which pygame calls does the event loop need when there is no window? Answer during M3.
- Do we want `Robotron.py` to stay a command-line tool, or become a documented example only? Decide during M4.
