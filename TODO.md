# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## 1. Type hints sweep

- ~~1. `util.py` ... 8. `debug/` package, each file its own approved step, `make test` green after each.~~ -- Done 2026-09-24: every function signature in `src/papple2/` has type hints; `debug/` went annotations+labels, checkpoints, disassembler, memory_map, tiles, assembler. See `HISTORY.md` 2026-09-24. Still open below: the attribute follow-up, and the test files (optional).
- Annotate the attributes `mypy` can't figure out by itself, e.g. `self.ops_dispatch = [None] * 0x100` in `core/cpu.py` (it concludes the list only ever holds `None`); likewise `CPU.PC`, `CPU.branched`, `Memory.apple2`. PyCharm doesn't mind these, so this only matters if we ever adopt `mypy`.
- Test files: hints are optional there. Decide whether to add them; today they're mixed (some fixtures in `conftest.py` have hints, most local fixtures don't).

## 2. Direction follow-ups (from 2026-09-23)

See `DIRECTION.md` for the context of each item.

- _Needs investigation:_ stretches -- keep the concept, or replace it with what other disassemblers use (usually plain functions)? `tiles.py`'s docstring has the doubts.
- _Needs investigation:_ is there an Apple II tool that saves per-byte code/data marks to a file (like FCEUX's Code/Data Logger), or tracks data provenance? microM8's heat map comes close.
- Jupyter primer, for a conscious decision on the monitor: Joel Grus's talk "I Don't Like Notebooks" (JupyterCon 2018), marimo's "why marimo", then a small hands-on notebook with `papple2` booting Lode Runner.
- Lode Runner, real play: a key press in attract mode starts a real game, which hangs in the game's own copy of DOS 3.3's RWTS at `$B600`-`$BFFF` (PC `$B94F`) -- `papple2` has no disk drive. The game reads sectors only, through the standard IOB and DCT (`main.nw` chapter 10). Plan: a checkpoint at the RWTS entry reads the IOB (track, sector, buffer, command), copies that sector from a disk image into the buffer, reports success, and returns as RWTS would -- no drive emulation. Confirm first: where the RWTS entry and the IOB sit (`main.nw`), and the format of Xekri's disk files (https://github.com/XekriRedmane/lode_runner_reveng/tree/main/disk): nibbles or 256-byte sectors, physical or DOS logical sector order.
- Level extraction for `a2-lode-runner`, depends on real play above: let the game's own code load each level, then read the filled memory -- all levels into the `a2-lode-runner` documentation. Expect its HTML to grow; the table of 103 sprites is already large.
- Robotron out of `papple2` (`make run` is already `make boot-robotron`; the script stays): the labels in `Labels.add_standard_labels` (including `waitKbd` twice), the three unused classes in `checkpoints.py`, and with `RecordedKeys` also `Display.save_hires_bytes`/`load_hires_bytes` (broken, no other caller), the `$51b6` exemption and the stale `examples/Robotron/workbench.py` pointer in `tiles.py`, `README.md` (Vision, screenshots, "hardest test case"), and the three tests in `test_emulator_silent.py` that load `ROBOTRON.BIN`. Move what `probotron` needs, delete the rest.
- Research document with glossary (in progress, away from the keyboard): established reverse-engineering concepts, and what the tools for 6502 platforms (NES, C64, Apple II) offer to understand a game. Basis for renaming `papple2`'s concepts, or at least putting them into their proper context.

## 3. Parked decisions

- Hook order: a write hook that blocks a write (today only the test's `WriteProtectHook`) ends the chain, so `TimeMachine` and `MemAccessCollector` never see that write. Decide what should happen once a real write guard exists.
- ~~`Memory.write_byte` didn't redraw a write to `$5FFF`, the last byte of hi-res page 2.~~ -- Fixed 2026-09-24 (`< 0x6000`), test extended.
- `tiles.py` has four known slips, left alone until the stretches question (section 2) is decided: a tile without links isn't marked as tail, a tile linked on both sides is wrongly marked as tail, `link_next_type` vs `link_type` disagree, and `is_straight_jsr_tile` can crash when nothing jumps to the next tile.
- The window's hi-res colours ignore the NTSC neighbour rules (a pixel's colour depends on its neighbours), so they can look wrong. `a2-hires-lab` has worked out the rules; use them if accurate colour ever matters.
- ~~`core/cpu.py` had its own copy of `signed()`.~~ -- Fixed 2026-09-24: imported from `util`.
- ~~Text pages 1 and 2 shared their flashing state (`flash_chars`).~~ -- Fixed 2026-09-24: two separate lists.
- ~~`Apple2.__init__` took `frame_rate` and ignored it.~~ -- Fixed 2026-09-24: parameter removed; `Emulator` keeps and uses its own.
- Unfinished ideas in `core/emulator.py`, kept on purpose: `EmulatorRunningState.action()` (a state handler, never registered) and `Emulator.write_hook` with `write_hook_enabled` (a write hook, its install line commented out). Both are early sketches of acting alongside execution. Think them through with the monitor and the research: finish them, or replace them with something better.
- `core/emulator.py` imports `MemoryMap` from `debug`, but `README.md`'s diagram says `core` never imports from `debug`. Decide with the research: draw the exception into the diagram, or move the memory map into `core`.
- Give recorded data names instead of positions: `core/hooks.py` stores memory accesses as nested tuples, and `debug/disassembler.py` returns small dicts (`OperandInfo`). Turn both into `dataclass(slots=True)`s: as small as tuples and as fast to read, only slower to create, so time a `MemAccessCollector` run before and after. Make `mem_access_colors`' `kind` an `enum`. `probotron` reads these tables, so check it along.
- The `TimeMachine` (Stopped, then left arrow steps back) doesn't work in the window yet. Revisit with the monitor:
  - `boot_lode_runner.py` doesn't switch it on (`time_machine=True`), so it never records; `on_left` still prints "restore".
  - Holding the arrow key steps only once: nothing calls `pygame.key.set_repeat`.
  - The status line isn't refreshed after a restore, so it keeps showing the old PC.
  - Stepping back stops one write early, so the very first write can never be undone (`> 1` instead of `> 0` in `restore_prev_state`: deliberate, or an off-by-one?).
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
- ~~`Emulator.post_op()` called `post_op()` on `TimeMachine` and `MemAccessCollector` even while they were switched off (about 7% headless).~~ -- Fixed 2026-09-24: it checks their `hooked` flag.
- ~~`MemoryMap.post_op()` defined three helper functions inside itself, rebuilt on every instruction.~~ -- Fixed 2026-09-24: private methods (measured 1288 -> 836 ns per call).
- Speed limit: `papple2` runs as fast as Python allows, faster than a real Apple II. Lode Runner's attract mode is visibly too fast, and steering the player will be hard once real play works (see the real-play item in section 2). _Needs investigation:_ how emulators handle this; decide only once watches and hooks show what they cost.
