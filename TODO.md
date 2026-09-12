# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M4 -- Split into core, debugging tools, and Robotron showcase (done 2026-09-12)

~~Robotron-specific code (`on_l`, `Memory.write_byte`'s guard ranges, `handle_rts`'s crash-on-empty-stack assertion) removed from the core; `write_byte2` and a dead `CPU.write_byte` trap removed; modules renamed to lower case and split into `papple2.core`/`papple2.debug`; showcase moved to `examples/Robotron/`; `Statemachines_example.py` removed.~~ **Done when:** ~~three clearly named parts exist, the core has no Robotron-specific lines, and `pysm` is only used in the debugging or showcase part.~~ See `HISTORY.md` for the full account. **Not done:** `Robotron.py` itself is still in `src/papple2/`, not yet moved to `examples/Robotron/`.

## M5 -- pytest coverage

- **First, before anything else:** move `Robotron.py` from `src/papple2/` to `examples/Robotron/`, alongside the rest of the showcase; fix up its imports (PyCharm's move/rename refactor).
- Add tests for the four areas from `GOALS.md`: (1) 6502 instructions and known bugs, (2) Apple II specifics (soft switches, display memory), (3) running a binary or disk image with and without the window, (4) breakpoints, time machine, memory access log.

**Done when:** tests exist for all four areas.

**Work items:** decided per area when we get there; each area is its own approved step.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
- A write-protect hook (`WriteProtectHook` in `tests/test_emulator_debug_keys.py`) vetoes a write before `TimeMachine`/`MemAccessCollector` ever see it -- fine while nothing happens on a vetoed write, but worth a real decision once a write guard and one of those two are ever active at the same time.
