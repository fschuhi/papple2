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

## 2. M8 -- Documentation cleanup

~~`README.md`'s "Package split" diagram and "Testing strategy" section, plus `GOALS.md`'s strategic vision items 2 and 4, all still described the Robotron showcase as living inside this repo.~~ **2026-09-15:** done, and expanded well beyond the reword -- see `HISTORY.md`.

## 3. Parked decisions

- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
- `TimeMachine.restore_prev_state`'s loop guard is `while self.state_index > 1`, not `> 0` -- once rewound down to `state_index == 1`, the very first recorded write can never be undone through this method (see `test_time_machine.py`, `test_restore_prev_state_stops_at_the_earliest_undoable_write`, which documents this as current behavior, not a fix). Might be intentional (always keep one anchor state), might be an off-by-one like the one below. Revisit if it ever matters in practice.
- `Memory.write_byte`'s hi-res render-trigger range check is `0x2000 <= address < 0x5FFF`, so a write to `0x5FFF` itself -- the last byte of real hi-res page 2 -- never calls `display.update`. Harmless for headless scriptable-buffer use (the byte still lands in `_mem` either way), but it's a pre-existing off-by-one in the render-trigger range. Fix if/when it ever matters for actual rendering.
- `TileFactory.update_heads_and_tails` (`tiles.py`) only ever sets `is_tail = True` for a tile that already has a `link_prev` -- a fully standalone tile (no links at all) comes out `is_head=True`, `is_tail=False`. Found and documented, not fixed (M6's `ACTION_PLAN.md` decision excludes redesigning tiles/stretches) -- see `tests/test_tiles.py::test_tiles_are_unlinked_given_the_non_adjacent_layout`.
- `a2-hires-lab`'s VBA work on NTSC hi-res color rules surfaced that `Display.update_hires`'s pixel-by-pixel color logic (no neighbor rules) isn't NTSC-accurate. Not a `papple2` blocker today -- headless write/read access to the hires pages bypasses rendering entirely (see `test_display_memory.py`). Revisit if/when NTSC-accurate hi-res color becomes a real requirement; `a2-hires-lab`'s findings would inform the fix.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.

## 4. Environment / packaging housekeeping

- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- Public-repo prep, parked until Theme 1 is done: remove the contents from `data/bin` and `data/do`, use checked-in `.gitkeep` instead, files remain in the folders locally. Needs an explanatory section in `README.md` with the locations where to download the files.

## 5. Optional coverage

- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
