# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## 1. Test infrastructure

- ~~Convert the remaining 11 `test_cpu_*.py` files from `unittest` to `pytest`.~~ **2026-09-14:** done, across four batches -- see `HISTORY.md`. `test_cpu_status_flags.py`, `test_cpu_branch.py`, `test_cpu_register_transfer.py`, `test_cpu_inc_dec.py`, and `test_cpu_arithmetic.py`'s `CMP`/`CPX`/`CPY`/`ADC`/`SBC` are now parametrized; `test_cpu_logical.py` and `test_cpu_shift.py` stay as plain functions since their ops don't share a uniform table. One bug found and fixed along the way: an `SBC` case that silently inherited `carry_flag` from the previous case broke when pulled out as an independent parametrized row.
- ~~Remaining: add an `Emulator`/`Assembler` fixture to `conftest.py`, needed before `test_emulator_silent.py`, `test_time_machine.py`, `test_mem_access_collector.py`, `test_emulator_debug_keys.py`, and `test_tiles.py` can convert. `test_softswitches.py` and `test_display_memory.py` need their own smaller local fixtures (`Display`/`Speaker`/`SoftSwitches`, and `Apple2` respectively). `test_robotron_waves.py` stays separate -- it loads the real `ROBOTRON.BIN`.~~ **2026-09-14:** done -- see `HISTORY.md`. `test_robotron_waves.py` was deleted outright rather than converted (dead WIP: its one test was already `@unittest.skip`'d and contained an unconditional `sys.exit(0)` mid-test). Still open: the per-address parametrize candidate in `test_softswitches.py`.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.

## 2. Finishing M7 (Excel bridge via PyXLL)

_Stays here for now, will be migrated to the Robotron project once that repo exists -- see `MIGRATE_ROBOTRON.md`._

- Try every function from Excel directly, not just via `make run`/pytest -- so far only `start_emulator` is confirmed working from Excel itself.
- Decide whether `ExcelContext`/`raise_error` is still worth keeping now that everything's converted, given PyXLL's own built-in exception-to-Excel-error handling.
- `RobotronXl.validate_memlog_dialog()`'s auto-create-if-missing fallback is commented out (`#if workbench.memlog_dialog is None: #    create_memlog_dialog(15)`). As it stands, calling any of `send_memlog_dialog_event`/`get_memlog_lines`/`get_memlog_cursor_pos`/`find_pc_forward`/`find_pc_backward` before `create_memlog_dialog` has ever run crashes with a raw `AttributeError` instead of the clean `"#..."` Excel error the other guards produce. Not fixed -- unclear why the fallback was disabled in the first place, so restoring it blind risks undoing a deliberate decision.
- Graphviz (the actual `dot` binary, not just the `graphviz` pip package) isn't installed on the Windows VM -- blocks `save_results` under `make run` specifically (calling individual Excel functions isn't affected). Either install Graphviz for Windows properly (e.g. `winget install Graphviz.Graphviz`) or keep using `--noresults` to skip it for now.

**Look at first:** `tests/test_robotronxl.py`, both as the reference for what's already been verified and as the pattern for the Excel round-trip check still to come.

**Decision already made (`GOALS.md`):** the bridge moves from `xlwings` to PyXll; not something to re-open here.

**Done when:** the functions in `RobotronXl.py` are callable from Excel through PyXll on the Windows VM.

## 3. Parked decisions

- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one below. Revisit if it ever matters in practice.
- `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- `TileFactory.update_heads_and_tails` (`tiles.py`) only ever sets `is_tail = True` for a tile that already has a `link_prev` -- a fully standalone tile (no links at all) comes out `is_head=True`, `is_tail=False`. Found and documented, not fixed (M6's `ACTION_PLAN.md` decision excludes redesigning tiles/stretches) -- see `tests/test_tiles.py::test_tiles_are_unlinked_given_the_non_adjacent_layout`.
- `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.

## 4. Environment / packaging housekeeping

- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- Public-repo prep, parked until Theme 1 is done: remove the contents from `data/bin` and `data/do`, use checked-in `.gitkeep` instead, files remain in the folders locally. Needs an explanatory section in `README.md` with the locations where to download the files. Review necessity of `ROBOTRON#062dfd.bin` and `ROBOTRON.BIN`.

## 5. Optional coverage

- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.

## 6. Type hints sweep

`LLM_INSTRUCTIONS.md` requires type hints on every function signature. First surfaced when `tests/test_robotronxl.py` (added in the M7 session) turned out to be written without them; today's Theme 1 conversion work made the gap bigger and, worse, inconsistent with itself. Needs a dedicated session, not a quick pass -- the scope question below has to be settled first, since it changes how big the actual work is.

- _Needs investigation:_ does the type-hints mandate apply to test files/fixtures at all, or was it written with `src/papple2/` production code in mind? Nothing in `LLM_INSTRUCTIONS.md` currently scopes it either way. This decides everything below -- if tests are in scope, the list is long; if not, it shrinks to `conftest.py` and production code only.
- Concrete inventory of what's inconsistent as of today, so the dedicated session doesn't have to re-derive it:
  - `conftest.py`: the three new factory fixtures (`assemble`, `make_emulator`, `run_steps`) have type hints; the original `memory`/`cpu` fixtures, pre-dating today, don't.
  - Today's own new local fixtures are inconsistent with each other: `test_time_machine.py`'s `emulator_with_three_writes` has a return type hint, but `test_tiles.py`'s `tile_factory`, `test_mem_access_collector.py`'s `make_mem_access_emulator`, `test_softswitches.py`'s `display`/`speaker`/`switches`, and `test_display_memory.py`'s `apple2` don't.
  - No `test_*` function anywhere -- old (`test_cpu_*.py`) or new -- has type-hinted fixture parameters (e.g. `def test_no_recording_before_hook_enabled(make_emulator, run_steps):`). This is either evidence the mandate was never meant to reach test functions, or a project-wide gap; see the scope question above.
  - `tests/test_robotronxl.py`: the original trigger for this item, still untouched.
