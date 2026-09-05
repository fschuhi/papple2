# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M1 -- Tests run and are green on macOS

- ~~Decide package layout~~ -- chose Approach A: `src/papple2` is a real, installable package (`pyproject.toml`, editable install wired into the `Makefile`). Decision recorded in `README.md`.
- ~~Prefix all internal imports with `papple2.`~~ -- mechanical prefix only; star-imports (`import *`) kept as-is on purpose. Converting to explicit names is M4 work, not this.
- ~~Convert `tests.py` into topic-based `pytest` files~~ -- split into per-class files under `tests/`; old `src/papple2/tests.py` and `tests/tests.py` removed.
- ~~Fix hardcoded test paths and `no_display` flags~~ -- along the way, found and fixed two blocking bugs in `Apple2.__init__` itself (`pygame.init()` ran unconditionally; the Apple II ROM loaded via a Windows-only path). Both are core-module fixes, not just test fixes.
- ~~`TestWaves.test_input_wave`~~ -- marked `@unittest.skip`; left as-is, including the `sys.exit(0)` and the dead code after it. Revisit later, not now.
- ~~`make test`~~ -- all green.

## M2 -- The emulator boots on macOS

- Replace the remaining hardcoded Windows paths (the Apple II ROM path in `Apple2.__init__` is already fixed, from M1):
  - `Robotron.py`: `load_state(r'trace\Robotron.dat')`, `save_state(r'trace\Robotron.dat')`
  - `RobotronXl.py`: `logging.basicConfig(filename='trace\\Robotron.log', ...)`; `workbench.save_map(r'trace\map.txt')`, `save_asm(r'trace\asm.txt')`, `save_dot(r'trace\call_tree.dot', ...)`
  - `Workbench.py`: `self.emulator.load_image(0x2dfd, r'bin\ROBOTRON.BIN')`
  - _Needs investigation_: does `trace/` need to exist before these run, the same question we had for `tmp/` during M1?
- Replace or remove `util.msgbox` (uses `ctypes.windll.user32.MessageBoxW`, Windows-only). Check first whether anything still calls it.
- Check whether `pygame.font.SysFont("Source Code Pro", 12)` in `Apple.py` resolves on macOS; add a fallback font if not.

**Done when:** `python -m papple2.Robotron` opens the pygame window, runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution.

**Look at first:** `Apple2.__init__` (already partly touched in M1), `Workbench.__init__`, `Robotron.__main__`, `RobotronXl.start_emulator`.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Memory.write_byte2` looks like an older version of `write_byte`. Check whether anything calls it; remove in M4 if not.
- `Workbench.simulate_execution` calls `mm.post_op(...)`, but `mm` is never defined anywhere in that scope -- PyCharm caught this once the imports resolved. Looks like a genuine bug in the call-tree/simulate code, not exercised by any current test. Fix when we're in that file for M6, or sooner if it turns out to block something.
