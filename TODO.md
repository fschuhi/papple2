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

- Start with Bandits as the second real case, timeboxed. Goal of the first part: Bandits' title screen in `papple2`, booted from its disk image. If booting turns into a boot-loader rabbit hole, stop there and do the review with `RwtsHook` alone; Bandits comes back later. Bring the `.do` to the session, so the boot sector and the DOS tracks can be checked directly. What we know (2026-09-26, from CiderPress screenshots; the boot details are general Apple II knowledge, to be confirmed):
  - Disk image: `Bandits (1982)(Sirius Software)[cr Nameless Cracker - Pirate Treck - Krakowicz][t +1].do`, a crack. It is byte-identical to `Bandits (1982)(Sirius)[cr Krakowicz][Button Shield].dsk`, so that `.dsk` is in DOS order too (CiderPress guessed "pdos/blk", wrongly) and `DiskImage` reads either. The `[o]` version has 143363 bytes (an overdump), which `DiskImage` refuses. The WOZ from the wozaday collection is the copy-protected original at flux level (Applesauce): using it would mean emulating the Disk II controller down to the nibbles -- set aside.
  - CiderPress sees a DOS 3.x volume 254 with an empty catalog ("0 files, 0 sectors free"): the game is probably loaded by track and sector, not by file name.
  - Track 0 sector 0 looks like the standard DOS 3.3 boot sector: it starts with `01` (load one sector), and `09 C0 85 3F A9 5C 85 3E` at `$0D` builds `$Cs5C` in `$3E`/`$3F` (`$C65C` for slot 6), the Disk II controller ROM's "read a sector" routine, which the boot sector calls to load more. Track 1 sector 6 holds DOS 3.3 itself: its error messages, the boot file name `HELLO`, `APPLESOFT`.
  - AppleWin shows disk access when a new level starts, so the game reads the disk during play too.
- Bandits, plan: boot through two hook points of the same shape as `RwtsHook`.
  1. Fake what the controller ROM does at boot: put track 0 sector 0 at `$0800` and start at `$0801`. Find out what the ROM leaves behind for the boot sector (at least the slot number times 16 in `$2B`). `papple2` has no Disk II ROM at `$C600`, which doesn't matter as long as a checkpoint catches `PC` there before anything executes.
  2. A hook at `$C65C` serves the boot sector's sector reads from the disk image. Find out its parameters (track, sector, buffer, in zero page).
  3. Once DOS is in memory: a watch in the style of step 3a (`HISTORY.md` 2026-09-26) finds how the game calls RWTS -- through DOS's standard entry, or some other way. Then serve those reads like `RwtsHook`.
  4. If the crack reads the disk outside DOS (its own sector-read code), that's a third hook point; the watch shows it.
  5. Then `make boot-bandits` with `scripts/boot_bandits.py`. What the hooks share goes into `core`; what differs stays per game.
- `RwtsHook` (`scripts/boot_lode_runner.py`) is the worked example: a checkpoint that changes `PC`, `SP`, carry and memory from outside the instruction stream and returns `(True, True)`, and keeps a log of what it did.
- Today there are four mechanisms, each registered differently: checkpoints (a list, `add_checkpoint()`), `post_op` observers (hard-coded in `Emulator.post_op()`, which knows `TimeMachine` and `MemAccessCollector` by name), `read_hook`/`write_hook` (one slot each, chained by hand through `CPUHook`), and `op_hook` (one slot). No written protocol for how they interact.
- `post_op`: make it a hook point others register with, instead of a list of named calls.
- `read_hook` can only watch a read, never answer it.
- The checkpoint contract (return values, "a checkpoint may move `PC`, the loop continues from there", `execute=False` is a breakpoint) belongs next to the `Checkpoint` alias in `core/emulator.py`.
- `jsr_stack`: rethink what control-flow bookkeeping records, aiming at what a tool like Ghidra would want, including rebuilding the stack contents for any point in the execution history (also direct writes to `$0100`-`$01FF`). Hooks like `RwtsHook` move `SP` without an instruction (its fake `RTS` leaves the caller's `JSR` on `jsr_stack`); such events must be recordable. Look at what `MemoryMap` and `jsr_stack` made of the three served reads first.
- Remove `cpu.op_hook`: nothing uses it, neither `papple2` (tests included) nor `probotron` (checked 2026-09-26). It doesn't fit the loop either: skipping an instruction would make `Emulator.post_op()` record the previous one a second time, since `cpu.last_PC` isn't updated.
- Remove the time machine (decided 2026-09-26): `TimeMachine` in `core/hooks.py`, `Emulator`'s `time_machine` parameter and its `post_op` call, the left-arrow restore in the window, `tests/test_time_machine.py`, and the rewinding in `README.md`'s Vision. Check `probotron` along.
