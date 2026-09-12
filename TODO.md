
# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M6 -- Tiles and stretches (done 2026-09-12)

~~Docstring added to `tiles.py` explaining tile/stretch/call tree in plain words; confirmed the module already lives in `papple2.debug`; added `tests/test_tiles.py`, building tiles from a small assembled program with a branch.~~ **Done when:** ~~`Tiles.py` lives in `papple2.debug`, has the docstring, and has at least one test building tiles from an assembled program.~~ See `HISTORY.md` for the full account.

## M7 -- Excel bridge via PyXll

- Replace `xlwings` with PyXll in `examples/Robotron/excel.py` and `examples/Robotron/RobotronXl.py`: swap `import xlwings as xw` / the `@xw.func` decorator for PyXll's own import and `@xl_func` decorator (PyXll wants explicit arg/return type strings, unlike xlwings).
- Update the Excel-side calls to match the M2 signature change: `start_emulator` and `save_results` now take `data_dir` + `trace_dir`, not the old single `path`. As of M2 these fail with a clear `TypeError`, not silently -- carried forward from a scratchpad note made at the time.
- Verify the functions in `RobotronXl.py` are callable from Excel through PyXll, on the Windows VM -- this milestone can't be verified from macOS; PyXll needs an actual Excel install.

**Look at first:** `examples/Robotron/excel.py` (small `ExcelContext`/`ExcelException` wrapper, its only xlwings touchpoint is the import), `examples/Robotron/RobotronXl.py` (`start_emulator`, `continue_robotron`, `save_results`, `save_state`, `load_state` -- all currently `@xw.func`).

**Decision already made (`GOALS.md`):** the bridge moves from `xlwings` to PyXll; not something to re-open here.

**Done when (`ACTION_PLAN.md`):** the functions in `RobotronXl.py` are callable from Excel through PyXll on the Windows VM.

## Scratchpad

- For the GitHub repo to turn to public, we need to remove the contents from `data/bin` and `data/do`, use checked in `.gitkeep` instead, files remain in the folders locally. Needs an explanatory section in `README.md` with the locations where to download the files. Review necessity of `ROBOTRON#062dfd.bin` and `ROBOTRON.BIN`.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- _Needs investigation, low priority:_ `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.
- _Needs investigation, very low priority:_ `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way, see `test_display_memory.py`), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- _Needs investigation, low priority:_ `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one above. Revisit if it ever matters in practice.
- _Needs investigation, low priority:_ `TileFactory.update_heads_and_tails` (`tiles.py`) only ever sets `is_tail = True` for a tile that already has a `link_prev` -- a fully standalone tile (no links at all) comes out `is_head=True`, `is_tail=False`. Found and documented, not fixed (M6's `ACTION_PLAN.md` decision excludes redesigning tiles/stretches) -- see `tests/test_tiles.py::test_tiles_are_unlinked_given_the_non_adjacent_layout`.
- **pytest-native conversion (started in the M5 session, carried over):** `conftest.py` (shared `memory`/`cpu` fixtures) and `test_cpu_stack.py` are done as the template. Remaining: convert the other 11 `test_cpu_*.py` files, `test_softswitches.py`, `test_display_memory.py`, `test_time_machine.py`, `test_mem_access_collector.py`, `test_emulator_silent.py`, `test_emulator_debug_keys.py`, `test_tiles.py`, and `test_robotron_waves.py` (needs `@pytest.mark.skip` for its one skipped test) in batches, running `make test` green after each batch. Add an `Emulator`/`Assembler` fixture to `conftest.py` when the emulator/hooks files get their turn. Parametrize opportunistically along the way -- good candidates: the softswitches per-address checks, and `TAX`/`TAY`/`TXA`/`TYA`'s repeated 0x00/0x01/0xFF checks.
