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

**Decided (2026-09-15):** production code first -- `src/papple2/` -- not test files/fixtures for now; test-file typing stays optional, revisit later if the core/debug gap being closed doesn't already take care of the itch. Sequenced core before debug, since `debug` already imports from `core` and should get real types to point at rather than untyped guesses:

1. `util.py`
2. `core/apple.py`
3. `core/cpu.py`
4. `core/memory.py`
5. `core/window.py`
6. `core/emulator.py`
7. `core/hooks.py`
8. `debug/` package (file order to be decided when we get there)

Each file its own approved step, `make test` green after each -- same rhythm as the pytest conversion work.

`LLM_INSTRUCTIONS.md` requires type hints on every function signature. First surfaced when `tests/test_robotronxl.py` (added in the M7 session) turned out to be written without them; the Theme-1 conversion work made the gap bigger and, worse, inconsistent with itself.

- Concrete inventory of what's inconsistent as of today, so this doesn't have to be re-derived:
  - `conftest.py`: the three new factory fixtures (`assemble`, `make_emulator`, `run_steps`) have type hints; the original `memory`/`cpu` fixtures, pre-dating today, don't.
  - Today's own new local fixtures are inconsistent with each other: `test_time_machine.py`'s `emulator_with_three_writes` has a return type hint, but `test_tiles.py`'s `tile_factory`, `test_mem_access_collector.py`'s `make_mem_access_emulator`, `test_softswitches.py`'s `display`/`speaker`/`switches`, and `test_display_memory.py`'s `apple2` don't.
  - No `test_*` function anywhere -- old (`test_cpu_*.py`) or new -- has type-hinted fixture parameters. Consistent with today's decision to leave test files out of scope for now, not a gap that needs re-deciding.
  - `tests/test_robotronxl.py`: the original trigger for this item, moved to `probotron` along with the rest of the Excel bridge -- no longer this repo's concern.

## 2. Direction follow-ups (from 2026-09-23)

See `DIRECTION.md` for the context of each item.

- _Needs investigation:_ stretches -- should the concept survive? What do other tools use as a container for basic blocks (traces, superblocks, IDA's function chunks, QEMU's translation block chaining, plain functions)?
- _Needs investigation:_ is there an Apple II tool that saves per-byte code/data marks to a file (like FCEUX's Code/Data Logger), or tracks data provenance? microM8's heat map comes close.
- Jupyter primer, for a conscious decision on the monitor: Joel Grus's talk "I Don't Like Notebooks" (JupyterCon 2018), marimo's "why marimo", then a small hands-on notebook with `papple2` booting Lode Runner.
- ~~`boot_lode_runner.py`: decide where it lives in the repo, if at all. Its windowed mode is untried.~~ -- Stays in `scripts/`; windowed mode works (`make boot-lode-runner`). All manual with-window checks are scripts now, see `HISTORY.md` 2026-09-23.
- Lode Runner, real play: a key press in attract mode starts a real game, which hangs in the game's own copy of DOS 3.3's RWTS at `$B600`-`$BFFF` (PC `$B94F`) -- `papple2` has no disk drive. The game reads sectors only, through the standard IOB and DCT (`main.nw` chapter 10). Plan: a checkpoint at the RWTS entry reads the IOB (track, sector, buffer, command), copies that sector from a disk image into the buffer, reports success, and returns as RWTS would -- no drive emulation. Confirm first: where the RWTS entry and the IOB sit (`main.nw`), and the format of Xekri's disk files (https://github.com/XekriRedmane/lode_runner_reveng/tree/main/disk): nibbles or 256-byte sectors, physical or DOS logical sector order.
- Level extraction for `a2-lode-runner`, depends on real play above: let the game's own code load each level, then read the filled memory -- all levels into the `a2-lode-runner` documentation. Expect its HTML to grow; the table of 103 sprites is already large.
- Robotron de-emphasis, partly done: `make run` is now `make boot-robotron`, and the script stays. Open: `README.md` (Vision, screenshots, "hardest test case") and the three tests in `tests/test_emulator_silent.py` that load `data/bin/ROBOTRON.BIN` by hard-coded path -- replace with Lode Runner, skip when missing, or keep?
- ~~Move the tests in `tests/test_cpu.py` into the existing `test_cpu_stack.py` (stack wrap) and `test_cpu_arithmetic.py` (decimal mode, replacing its BCD TODO), then delete `test_cpu.py`. Prepared as `2026-09-23-cpu-tests-into-existing-files.patch`, not yet applied.~~ -- Done between sessions.
- Glossary into the documentation; then compare each tool with its closest established counterpart and borrow what has proven itself.

## 3. Parked decisions

- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one below. Revisit if it ever matters in practice.
- `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- `TileFactory.update_heads_and_tails` (`tiles.py`) only ever sets `is_tail = True` for a tile that already has a `link_prev` -- a fully standalone tile (no links at all) comes out `is_head=True`, `is_tail=False`. Found and documented, not fixed (M6's `ACTION_PLAN.md` decision excludes redesigning tiles/stretches) -- see `tests/test_tiles.py::test_tiles_are_unlinked_given_the_non_adjacent_layout`.
- `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Display.save_hires_bytes`/`load_hires_bytes` (`core/apple.py`) call `self.pickle.dump(...)`/`self.pickle.load(...)`, but `self.pickle` is the class's own `pickle(pickler)` method, so both would crash with `AttributeError`. Not dead code: `KeyScript` in `debug/checkpoints.py` calls `save_hires_bytes`, in a branch the tests never reach. Decide: fix (use the `pickle` module), or remove both together with the `KeyScript` call. Found during the type hints sweep, 2026-09-24.
- `Display.__init__` sets `self.flash_chars = [[0] * 0x400] * 2`, which is one list referenced twice, not two lists: text pages 1 and 2 share their flash state. Fix: `[[0] * 0x400 for _ in range(2)]`. Found during the type hints sweep, 2026-09-24.
- `Apple2.__init__` accepts `frame_rate` and never uses it; `Emulator` passes it through. Remove, or give it a job? Found during the type hints sweep, 2026-09-24.

## 4. Environment / packaging housekeeping

- _Needs investigation_: Python 3.14. `README.md` says pygame 2.6.1 fails under 3.14 (`mixer`, `font` missing), but that was the original `pygame`; `requirements.txt` now installs `pygame-ce`, the workaround. Does `pygame-ce` run on 3.14? If so, revisit the Python-version notes in `README.md`/`Makefile`.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- Public-repo prep, parked until Theme 1 is done: remove the contents from `data/bin` and `data/do`, use checked-in `.gitkeep` instead, files remain in the folders locally. Needs an explanatory section in `README.md` with the locations where to download the files.

## 5. Optional coverage

- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.

## 6. Performance (parked, 2026-09-23)

Measured with `cProfile` on the headless Lode Runner run, see `HISTORY.md` 2026-09-23. Headless already runs at about twice real Apple II speed, so none of these is needed today.

- `is_executing()` is called three times per instruction and walks the `pysm` state machine each time (about 8% headless). If ever: a plain flag set in the Running state's entry and exit handlers, not a local copy in `Emulator.run()`.
- `Emulator.post_op()` calls `post_op()` of `TimeMachine`/`MemAccessCollector` even while they are disabled (about 7% headless): check their enabled flag instead of whether the object exists.
- `MemoryMap.post_op()` defines three inner functions on every call.
- No speed limit in `papple2`: the game slows itself down on repeated left-arrow presses, and future hooks will cost speed anyway.
