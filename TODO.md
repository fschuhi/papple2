# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M5 -- pytest coverage (done 2026-09-12)

~~`Robotron.py` moved to `examples/Robotron/`; soft-switch and hi-res-memory-buffer tests added (`test_softswitches.py`, `test_display_memory.py`); `TimeMachine`/`MemAccessCollector` covered (`test_time_machine.py`, `test_mem_access_collector.py`), deliberately skipping the Excel/Graphviz-feeding derived views; confirmed full per-opcode coverage in the existing `test_cpu_*.py` suite and closed the one gap found (`test_TSX` now checks N/Z flags); area 3's window half settled as manual verification via the Robotron showcase, documented in `README.md` instead of automated.~~ **Done when:** ~~tests exist for all four areas from `GOALS.md`.~~ See `HISTORY.md` for the full account.

## M6 -- Tiles and stretches

- **First:** re-read `Tiles.py` fresh and write the short docstring explaining tile / stretch / call tree in plain words -- the `ACTION_PLAN.md` Done-when for this milestone. Do this before touching any code; writing the docstring is likely to surface questions about what to keep.
- Confirm `Tiles.py` already lives in `papple2.debug` after the M4 split; move it if it hasn't been relocated yet.
- Add at least one test that builds tiles from a small assembled program -- a handful of instructions with a branch or two should be enough to produce more than one tile/stretch to assert on. Same style as this session's `THREE_WRITES_PROGRAM`-type helpers.

**Decision already made (`ACTION_PLAN.md`):** no redesign of the tile/stretch mechanism itself. Lower priority than the other milestones -- tiles support disassembly work, not emulation.

**Done when:** `Tiles.py` lives in `papple2.debug`, has the docstring, and has at least one test building tiles from an assembled program.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- _Needs investigation, low priority:_ `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.
- _Needs investigation, very low priority:_ `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way, see `test_display_memory.py`), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- _Needs investigation, low priority:_ `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one above. Revisit if it ever matters in practice.
- **pytest-native conversion (started this session, carried over from M5):** `conftest.py` (shared `memory`/`cpu` fixtures) and `test_cpu_stack.py` are done as the template. Remaining: convert the other 11 `test_cpu_*.py` files, `test_softswitches.py`, `test_display_memory.py`, `test_time_machine.py`, `test_mem_access_collector.py`, `test_emulator_silent.py`, `test_emulator_debug_keys.py`, and `test_robotron_waves.py` (needs `@pytest.mark.skip` for its one skipped test) in batches, running `make test` green after each batch. Add an `Emulator`/`Assembler` fixture to `conftest.py` when the emulator/hooks files get their turn. Parametrize opportunistically along the way -- good candidates: the softswitches per-address checks, and `TAX`/`TAY`/`TXA`/`TYA`'s repeated 0x00/0x01/0xFF checks.
