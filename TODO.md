# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## 1. Type hints follow-ups

- Annotate the attributes `mypy` can't figure out by itself, e.g. `self.ops_dispatch = [None] * 0x100` in `core/cpu.py` (it concludes the list only ever holds `None`); likewise `CPU.PC`, `CPU.branched`, `Memory.apple2`. PyCharm doesn't mind these, so this only matters if we ever adopt `mypy`.
- Test files: hints are optional there. Decide whether to add them; today they're mixed (some fixtures in `conftest.py` have hints, most local fixtures don't).

## 2. Direction follow-ups (from 2026-09-23)

See `DIRECTION.md` for the context of each item.

- ~~Lode Runner, real play: a key press in attract mode hung in the game's RWTS -- `papple2` has no disk drive.~~ -- Done 2026-09-26: `RwtsHook` in `scripts/boot_lode_runner.py`, a checkpoint at `DISABLE_INTS_CALL_RWTS` (`$B7B5`), serves the game's reads from the `.do` image via `papple2.core.disk_image`; level 1 played, level 2 loaded from disk. See `HISTORY.md` 2026-09-26.
- Level extraction for `a2-lode-runner`, now possible since real play works (2026-09-26): let the game's own code load each level, then read the filled memory -- all levels into the `a2-lode-runner` documentation. Expect its HTML to grow; the table of 103 sprites is already large.
- _Needs investigation:_ stretches -- keep the concept, or replace it with what other disassemblers use (usually plain functions)? `tiles.py`'s docstring has the doubts.
- _Needs investigation:_ is there an Apple II tool that saves per-byte code/data marks to a file (like FCEUX's Code/Data Logger), or tracks data provenance? microM8's heat map comes close.
- Jupyter primer, for a conscious decision on the monitor: Joel Grus's talk "I Don't Like Notebooks" (JupyterCon 2018), marimo's "why marimo", then a small hands-on notebook with `papple2` booting Lode Runner.
- Robotron out of `papple2` (`make run` is already `make boot-robotron`; the script stays): the labels in `Labels.add_standard_labels` (including `waitKbd` twice), the three unused classes in `checkpoints.py`, and with `RecordedKeys` also `Display.save_hires_bytes`/`load_hires_bytes` (broken, no other caller), the `$51b6` exemption and the stale `examples/Robotron/workbench.py` pointer in `tiles.py`, `README.md` (Vision, screenshots, "hardest test case"), and the three tests in `test_emulator_silent.py` that load `ROBOTRON.BIN`. Move what `probotron` needs, delete the rest.
- Research document with glossary (in progress, away from the keyboard): established reverse-engineering concepts, and what the tools for 6502 platforms (NES, C64, Apple II) offer to understand a game. Basis for renaming `papple2`'s concepts, or at least putting them into their proper context.

## 3. Parked decisions

- Hook order: a write hook that blocks a write (today only the test's `WriteProtectHook`) ends the chain, so `TimeMachine` and `MemAccessCollector` never see that write. Decide what should happen once a real write guard exists.
- `tiles.py` has four known slips, left alone until the stretches question (section 2) is decided: a tile without links isn't marked as tail, a tile linked on both sides is wrongly marked as tail, `link_next_type` vs `link_type` disagree, and `is_straight_jsr_tile` can crash when nothing jumps to the next tile.
- The window's hi-res colours ignore the NTSC neighbour rules (a pixel's colour depends on its neighbours), so they can look wrong. `a2-hires-lab` has worked out the rules; use them if accurate colour ever matters.
- Unfinished ideas in `core/emulator.py`, kept on purpose: `EmulatorRunningState.action()` (a state handler, never registered) and `Emulator.write_hook` with `write_hook_enabled` (a write hook, its install line commented out). Both are early sketches of acting alongside execution. Think them through with the monitor and the research: finish them, or replace them with something better.
- `core/emulator.py` imports `MemoryMap` from `debug`, but `README.md`'s diagram says `core` never imports from `debug`. Decide with the research: draw the exception into the diagram, or move the memory map into `core`.
- Give recorded data names instead of positions: `core/hooks.py` stores memory accesses as nested tuples, and `debug/disassembler.py` returns small dicts (`OperandInfo`). Turn both into `dataclass(slots=True)`s: as small as tuples and as fast to read, only slower to create, so time a `MemAccessCollector` run before and after. Make `mem_access_colors`' `kind` an `enum`. `probotron` reads these tables, so check it along.
- ~~The `TimeMachine` doesn't work in the window yet (never switched on by `boot_lode_runner.py`, no key repeat, stale status line, the first write can't be undone).~~ -- Superseded 2026-09-26: the time machine goes, see section 7.
- `debug/assembler.py` calls `sys.exit(1)` on an error in the source it assembles. Fine for scripts and tests (`pytest` fails just that test), but it would end an interactive session (monitor, notebook) on a typo. Decide with the monitor: keep it, or raise an `AssemblerError` (stops just as fast, but can be caught -- and swallowed).
- Check whether our leap recording handles two patterns where `JSR` and `RTS` don't pair up: tail calls (a `JMP` at the end of a routine instead of `JSR` + `RTS`, so the jumped-to routine's `RTS` returns straight to the original caller), and the RTS trick (push an address minus 1 onto the stack by hand, then `RTS` to jump there, e.g. for jump tables). Watch `has_matched_JSR` and how an `RTS` is matched to its `JSR`.
- The memory map crashes on a `JMP` to its own address (`JMP *`, a "wait forever" loop): `MemoryMap._link_with_prev` asserts that an instruction never follows itself. The assertion is deliberate ("we do not allow jumps to self"), but real programs use `JMP *`. Found 2026-09-24.

## 4. Environment / packaging housekeeping

- Bring in automated `black` formatting, as in some of my other projects. Decide how it runs: a `make` target, PyCharm on save, or a pre-commit hook. A hook reformats on `git commit` and then stops the commit, so you have to `git add` and commit again; that's the "why do I have to commit twice" effect from other projects. Explain whichever choice plainly. Then reformat the whole codebase in one separate commit, so later diffs show only real changes, and list that commit in `.git-blame-ignore-revs`, so `git blame` looks past it.
- Python 3.14: `pygame-ce` 2.5.8 works there (imports with `mixer` and `font` on 3.14.5, checked 2026-09-24). Remaining: run `make test` under 3.14, then update the Python-version notes in `README.md` and the `Makefile`.
- Pin `pysm`'s version in `requirements.txt` (nothing is pinned today; `pip show pysm` shows the installed one). `pysm` first, because the emulator's state machine rests on it; decide whether to pin the others too.

## 5. Optional coverage

- Finish the `unittest` -> `pytest` conversion: `tests/test_memory.py` and `tests/test_assembler.py` still use `unittest` (`test_memory.py` already has two `pytest` functions next to its old class). In `test_assembler.py`, rename `test_dump`: it's a printing helper, but its `test_` name makes the runner run it as a test.

## 6. Performance (parked, 2026-09-23)

Measured with `cProfile` on the headless Lode Runner run, see `HISTORY.md` 2026-09-23. Headless already runs at about twice real Apple II speed, so none of these is needed today.

- `is_executing()` runs three times per instruction and asks the `pysm` state machine each time (about 8% headless). The flag already exists: `executing` is set in both states' `on_enter`/`on_exit`, and agrees with the state after every transition (checked 2026-09-24), except right after construction: `pysm` only fires the initial state's `on_enter` with `initialize(fire_events_on_init=True)`, which `papple2` doesn't pass. If ever: pass it (check that Running's `on_enter` is safe that early, e.g. without a window yet), `return self.executing`, and add a test that the flag agrees with the state.
- Speed limit: `papple2` runs as fast as Python allows, faster than a real Apple II. Lode Runner's attract mode is visibly too fast, and since real play works (2026-09-26), steering the player is very hard: level 1 was just barely playable. _Needs investigation:_ how emulators handle this; decide only once watches and hooks show what they cost.

## 7. Hook architecture review (next session, decided 2026-09-26)

The hook mechanisms grew one need at a time; review them as a whole before more hooks are added. Order: functionality and tests first (`RwtsHook` has the first; Bandits brings the second case), then refactoring.

- Start with Bandits as the second real case. AppleWin shows disk access when a new level starts; whether that goes through DOS's RWTS or a loader of its own is unknown, and there's no answer key. So first a watch in the style of step 3a (`HISTORY.md` 2026-09-26): find the entry, stop, read the request. Then `make boot-bandits` with `scripts/boot_bandits.py`. What `RwtsHook` and a Bandits hook share goes into `core`; what differs stays per game.
- `RwtsHook` (`scripts/boot_lode_runner.py`) is the worked example: a checkpoint that changes `PC`, `SP`, carry and memory from outside the instruction stream and returns `(True, True)`, and keeps a log of what it did.
- Today there are four mechanisms, each registered differently: checkpoints (a list, `add_checkpoint()`), `post_op` observers (hard-coded in `Emulator.post_op()`, which knows `TimeMachine` and `MemAccessCollector` by name), `read_hook`/`write_hook` (one slot each, chained by hand through `CPUHook`), and `op_hook` (one slot). No written protocol for how they interact.
- `post_op`: make it a hook point others register with, instead of a list of named calls.
- `read_hook` can only watch a read, never answer it.
- The checkpoint contract (return values, "a checkpoint may move `PC`, the loop continues from there", `execute=False` is a breakpoint) belongs next to the `Checkpoint` alias in `core/emulator.py`.
- `jsr_stack`: rethink what control-flow bookkeeping records, aiming at what a tool like Ghidra would want, including rebuilding the stack contents for any point in the execution history (also direct writes to `$0100`-`$01FF`). Hooks like `RwtsHook` move `SP` without an instruction (its fake `RTS` leaves the caller's `JSR` on `jsr_stack`); such events must be recordable. Look at what `MemoryMap` and `jsr_stack` made of the three served reads first.
- Remove `cpu.op_hook`: nothing uses it, neither `papple2` (tests included) nor `probotron` (checked 2026-09-26). It doesn't fit the loop either: skipping an instruction would make `Emulator.post_op()` record the previous one a second time, since `cpu.last_PC` isn't updated.
- Remove the time machine (decided 2026-09-26): `TimeMachine` in `core/hooks.py`, `Emulator`'s `time_machine` parameter and its `post_op` call, the left-arrow restore in the window, `tests/test_time_machine.py`, and the rewinding in `README.md`'s Vision. Check `probotron` along.
