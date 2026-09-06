
# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M2 -- The emulator boots on macOS (done on 2026-09-06)

- ~~Replace hardcoded Windows paths~~ -- introduced `papple2.toml` (local, gitignored; `papple2.example.toml` committed instead) holding `data_dir`/`trace_dir`, read once in `Robotron.__main__` and threaded explicitly through `start_emulator`, `Workbench.__init__`, and `save_results` -- no `os.chdir` needed anymore. Also swept up `args.savemem`'s `dat\test.dat` (now under `data_dir`) and the Graphviz `PATH` hack in `Tiles.py` (removed; `dot` now found via `brew install graphviz`).
- ~~Replace or remove `util.msgbox`~~ -- removed entirely; no callers existed anywhere in the codebase.
- ~~Status-bar font~~ -- no code change needed: `pygame.font.SysFont` already falls back silently when `"Source Code Pro"` isn't installed.
- ~~Two missing `papple2.`-prefix imports, found while testing the real boot~~ -- `Checkpoints.py`'s `from util import *` and `Robotron.py`'s `from RobotronXl import workbench, emulator` were leftovers from the M1 package migration; both fixed.
- ~~`Workbench.simulate_execution`'s `mm.post_op` bug (was in Scratchpad)~~ -- `mm` was never defined; replaced with the already-correct `self.map`.
- ~~pygame vs. Python 3.14~~ -- vanilla `pygame` 2.6.1 doesn't build/run correctly under Python 3.14 yet (open upstream issue); venv recreated under Python 3.12 instead, resolved. Documented in `README.md`.

**Done when:** ~~`python -m papple2.Robotron` opens the pygame window, runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution.~~ Confirmed -- the animated Robotron splash screen renders correctly on macOS.

## M3 -- Silent mode

- Give `Emulator.event_loop` a way to run without polling pygame events: a step count, a stop address, or a callback.
- Add a programmatic keypress path (write to `softswitches.kbd` the way `on_key` does).
- One pytest that boots silently, runs the Apple II ROM or a small assembled program, presses a key, and asserts on memory.
- _Already done, no new work needed:_ `pygame.init()` is already conditional on `no_display` (fixed during M1) -- `ACTION_PLAN.md`'s M3 item about this is stale.

**Done when:** the emulator can run to a breakpoint or for N instructions without opening a window, and a test can feed keypresses from code and check memory afterwards.

**Look at first:** `Emulator.event_loop`, `EmulatorExecutingState.on_key`, `SoftSwitches.read_byte`.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Memory.write_byte2` looks like an older version of `write_byte`. Check whether anything calls it; remove in M4 if not.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- `ACTION_PLAN.md`'s M7 section still says the Excel bridge only runs on the Windows VM and is lowest priority -- needs rewording, since it's part of the Robotron showcase now: lower priority, not zero.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
