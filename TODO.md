# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M7 -- Excel bridge via PyXll (in progress)

**Where this stands:** Every function in `RobotronXl.py` now uses PyXLL's `@xl_func` instead of xlwings' `@xw.func` -- the plain read/query functions, the ones taking cycle/byte-range arguments, the memlog-dialog functions, and the three `ndim=2`/transpose functions (PyXLL's `var[][]`/`var[]` array types plus the decorator's own `transpose=True` option, in place of xlwings' separate `@xw.arg`/`@xw.ret` decorators). `xlwings` is no longer imported anywhere in `RobotronXl.py` or `excel.py`, and was already absent from `requirements.txt`. New tests in `tests/test_robotronxl.py` cover every converted function and found three real, pre-existing bugs, all fixed -- see `HISTORY.md`.

Not yet done: only `start_emulator` has been confirmed working from a real Excel workbook; everything else has only been exercised via `make run` or the new pytest tests.

**Remaining work:**

- ~~Run `make test` -- not yet re-run since the `data_dir` threading change.~~ **2026-09-13:** confirmed green at the start of the session; every batch below kept it green throughout.
- Try every function from Excel directly, not just via `make run`/pytest -- so far only `start_emulator` is confirmed working from Excel itself.
- ~~Convert the ~15 remaining read/query functions to `@xl_func`.~~ **2026-09-13:** done, across three batches (the plain functions, the argument-taking functions, the memlog-dialog functions) -- see `HISTORY.md` for what each batch covered and the bugs it surfaced.
- ~~Convert `get_touch_count`, `get_first_cycles`, `get_last_cycles`.~~ **2026-09-13:** done. Also surfaced a real pre-existing bug -- `get_attribute_from_info` referenced `emulator.memory_map`, which doesn't exist (the real attribute is `.map`) -- fixed; see `HISTORY.md`.
- Decide whether `ExcelContext`/`raise_error` is still worth keeping now that everything's converted, given PyXLL's own built-in exception-to-Excel-error handling.
- ~~Remove `xlwings` from `requirements.txt` once nothing in `RobotronXl.py`/`excel.py` still imports it.~~ **2026-09-13:** `requirements.txt` was already clean; the two dead `import xlwings as xw` lines in the code itself are gone now too.
- Graphviz (the actual `dot` binary, not just the `graphviz` pip package) isn't installed on the Windows VM -- blocks `save_results` under `make run` specifically (calling individual Excel functions isn't affected). Either install Graphviz for Windows properly (e.g. `winget install Graphviz.Graphviz`) or keep using `--noresults` to skip it for now.

**Look at first:** `tests/test_robotronxl.py`, both as the reference for what's already been verified and as the pattern for the Excel round-trip check still to come.

**Decision already made (`GOALS.md`):** the bridge moves from `xlwings` to PyXll; not something to re-open here.

**Done when (`ACTION_PLAN.md`):** the functions in `RobotronXl.py` are callable from Excel through PyXll on the Windows VM.

## Scratchpad

- For the GitHub repo to turn to public, we need to remove the contents from `data/bin` and `data/do`, use checked in `.gitkeep` instead, files remain in the folders locally. Needs an explanatory section in `README.md` with the locations where to download the files. Review necessity of `ROBOTRON#062dfd.bin` and `ROBOTRON.BIN`.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- _Needs investigation, low priority:_ `RobotronXl.validate_memlog_dialog()`'s auto-create-if-missing fallback is commented out (`#if workbench.memlog_dialog is None: #    create_memlog_dialog(15)`). As it stands, calling any of `send_memlog_dialog_event`/`get_memlog_lines`/`get_memlog_cursor_pos`/`find_pc_forward`/`find_pc_backward` before `create_memlog_dialog` has ever run crashes with a raw `AttributeError` (`'NoneType' object has no attribute ...`) instead of the clean `"#..."` Excel error the other guards produce. Not fixed now -- unclear why the fallback was disabled in the first place, so restoring it blind risks undoing a deliberate decision. Found while converting `RobotronXl.py` to PyXLL (M7); the new tests in `test_robotronxl.py` work around it by always calling `create_memlog_dialog` first.
- _Needs investigation, low priority:_ `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.
- _Needs investigation, very low priority:_ `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way, see `test_display_memory.py`), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- _Needs investigation, low priority:_ `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one above. Revisit if it ever matters in practice.
- _Needs investigation, low priority:_ `TileFactory.update_heads_and_tails` (`tiles.py`) only ever sets `is_tail = True` for a tile that already has a `link_prev` -- a fully standalone tile (no links at all) comes out `is_head=True`, `is_tail=False`. Found and documented, not fixed (M6's `ACTION_PLAN.md` decision excludes redesigning tiles/stretches) -- see `tests/test_tiles.py::test_tiles_are_unlinked_given_the_non_adjacent_layout`.
- **pytest-native conversion (started in the M5 session, carried over):** `conftest.py` (shared `memory`/`cpu` fixtures) and `test_cpu_stack.py` are done as the template. Remaining: convert the other 11 `test_cpu_*.py` files, `test_softswitches.py`, `test_display_memory.py`, `test_time_machine.py`, `test_mem_access_collector.py`, `test_emulator_silent.py`, `test_emulator_debug_keys.py`, `test_tiles.py`, and `test_robotron_waves.py` (needs `@pytest.mark.skip` for its one skipped test) in batches, running `make test` green after each batch. Add an `Emulator`/`Assembler` fixture to `conftest.py` when the emulator/hooks files get their turn. Parametrize opportunistically along the way -- good candidates: the softswitches per-address checks, and `TAX`/`TAY`/`TXA`/`TYA`'s repeated 0x00/0x01/0xFF checks.
- Type hints sweep: `LLM_INSTRUCTIONS.md` requires type hints on every function signature; `tests/test_robotronxl.py` (added this session) was written without them, and it's worth checking the rest of the codebase for the same gap rather than assuming it's isolated to that one file.
