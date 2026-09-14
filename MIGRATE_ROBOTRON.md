# Migrating Robotron + Excel out of `papple2`

(Note: "I" in the following paragraphs refers to the project owner, "you" to
you as the AI model picking this up in a fresh session.)

**Why this file exists:** this was worked out in a `papple2` session that
was mid-way through the `unittest` -> `pytest` conversion (Theme 1) and
didn't want to context-switch into a full repo split there. Everything
below is the plan as discussed -- not yet implemented. Read this file, plus
the current `papple2.toml`/`README.md`/`GOALS.md`/`TODO.md`/`manifest.lst`
for whatever's changed since, then work through it with the same
Discuss -> Approve -> Implement workflow as any other session
(`CRITICAL_RULES.md`).

## The decision

Split what's currently mixed into `papple2` into two things:

1. **`papple2` itself** -- the emulator core, the debugging tools
   (`papple2.core`, `papple2.debug`), and a small in-repo manual pygame
   smoke test (`tests/test_robotron.py`, done already -- see below). Stays
   a macOS-focused, installable Python package. No Excel, no `pyxll`.
2. **A new, separate repo** -- the Robotron 2084 disassembly workbench
   (`examples/Robotron/`: `workbench.py`, `RobotronXl.py`, `excel.py`,
   `mem_log_dlg.py`, and a trimmed `Robotron.py` that no longer needs to
   double as the pygame smoke test), the PyXLL/Excel bridge, and the
   Robotron-specific data/docs. Depends on `papple2` as an installed
   package. Windows-focused (PyXLL requires it).

**Motivation, in the project owner's words:** the Excel bridge (M7) was
blocking forward progress, but the real near-term interest is the Lode
Runner disassembly (`load-runner`/`main.nw`), not finishing Robotron's
Excel tooling. Splitting the repos removes that blocker from `papple2`'s
critical path entirely -- Excel/Robotron work continues on its own
timeline, in its own repo, whenever there's appetite for it again.

## Why this is a move, not a refactor

Checked during the discussion, worth re-verifying if time has passed:

- `papple2` is already a real installable package (`src/papple2/`,
  `pyproject.toml`, `pip install -e .` via `make setup`), split into
  `papple2.core`/`papple2.debug` (M4, done). No further internal
  restructuring needed on that front.
- The old Robotron-specific logic that used to live *inside* the core
  (protected memory ranges in `Memory.write_byte`, Robotron addresses in
  `Emulator.on_l`, a Robotron-only assumption in `handle_rts`) was already
  extracted before this session -- confirmed by `tests/test_emulator_debug_keys.py`
  (the veto-hook pattern that replaced `on_l`) and the `handle_rts`
  regression test in `tests/test_emulator_silent.py`.
- `examples/Robotron/*.py` already import `papple2` as a clean package
  (`from papple2.core.apple import Apple2`, etc.), not via relative-path
  hacks. The only internal-import cleanup needed is that they currently
  import *each other* as `examples.Robotron.X` (`Robotron.py` imports
  `from examples.Robotron.workbench import Workbench`, etc.) -- that
  changes once they're not nested under `papple2` anymore. Decide the new
  repo's internal package shape (flat scripts vs. its own `src/robotron/`
  layout mirroring `papple2`'s -- the latter is arguably the more
  instructive answer to "how do I use `papple2` from another project",
  since `load-runner` will face the same question later) before touching
  the imports.
- **Important finding:** `examples/Robotron/Robotron.py` (what `make run`
  used to invoke) is *not* currently decoupled from the Excel bridge at
  import time -- it imports `RobotronXl.py`, which does
  `from pyxll import xl_func` unconditionally at module level. So today,
  even just booting the pygame window already requires `pyxll` installed.
  This is exactly why `tests/test_robotron.py` (see below) was written as
  new, minimal code rather than extracted from `Robotron.py`.

## What moves to the new repo

- `examples/Robotron/` (all five files, with `Robotron.py` reworked: drop
  whatever role it played as the pygame entry point, since
  `papple2/tests/test_robotron.py` now covers that inside `papple2`
  itself; keep whatever workbench/Excel-launching responsibilities remain)
- `tests/test_robotronxl.py`
- `data/bin/ROBOTRON.BIN`, `data/do/Robotron 2084 (1983)(Atari).do`,
  `data/img/Robotron_*.jpg`
- `docs/Robotron/*`
- `Robotron.xlsb`, `test.xlsm` (assumed to be Robotron workbook artifacts
  from name/location -- confirm before moving)
- `pyxll/` entirely (`pyxll.cfg`, `pyxll.example.cfg`, `logs/`)

`tests/test_robotron_waves.py` does **not** move -- it was already deleted
outright in this session (dead WIP, a `sys.exit(0)` mid-test, no working
assertions; see `HISTORY.md`/session transcript if the reasoning is
needed again). The wave-select patch idea it contained stays out of both
repos per the project owner's call.

## What stays in `papple2`, and shrinks

- `src/papple2/` (unchanged), the non-Robotron tests, `docs/6502`,
  `docs/Apple`, `data/bin/A2ROM.BIN` (the generic Apple II ROM).
- `requirements.txt`/`pyproject.toml`: drop `pyxll`. Keep `graphviz` --
  it's imported by `papple2.debug.tiles` itself (confirmed by grep), not
  Robotron code, so it's a genuine `papple2` dependency.
- **`Makefile`: once the move is actually done**, the whole
  `ifeq ($(OS),Windows_NT)` branch, `.venv-win`, and the `excel` target
  can be deleted -- PyXLL was the only reason `papple2`'s own `Makefile`
  needed to know about Windows at all. `papple2` becomes macOS-only.
  (Not done yet -- doing it before the actual file move would break
  `make excel` while Robotron/PyXLL code is still sitting in this repo.)
- `manifest.lst`: drop every line under "Robotron example" and the
  Robotron-related data/docs/pyxll lines.

## Already done in this session (don't redo)

- `tests/test_robotron.py` -- a minimal `@pytest.mark.manual` test that
  boots `Emulator(no_display=False)` with the real `ROBOTRON.BIN` and
  calls `emulator.run()` with no `until`, same as the old `make run` did,
  but with zero `workbench`/`tiles`/`pyxll` involvement. Registered via
  `pyproject.toml`'s `[tool.pytest.ini_options]` (`markers`, `addopts = "-m
  'not manual'"`), so `make test` skips it automatically and
  `pytest tests/test_robotron.py -m manual -s -v` runs it deliberately.
  `Makefile`'s `run` target now calls exactly that. This is what makes the
  carve-out safe in the first place: `papple2` keeps a real (if manual)
  check on the with-window code path without needing the Robotron
  workbench, tiles, or Excel bridge back.
- `ROBOTRON.BIN` distribution: not solved by moving code, solved by
  config. `papple2.toml`'s `data_dir` (already a settled, gitignored,
  per-machine setting) can point at the new repo's `data/bin/` on a given
  machine -- no duplication, and it sidesteps redistributing a
  still-copyrighted binary via GitHub. `README.md` should get a short note
  along these lines: contact the project owner directly for a copy of
  `ROBOTRON.BIN`, then point `data_dir` at it.
- A fallback idea, **not built, not needed for the above**: boot
  `A2ROM.BIN` alone (no game image) into AppleSoft/Integer BASIC instead
  of Robotron, as a licensing-safer manual smoke test. Mechanically
  plausible -- `Apple2.__init__` already loads `A2ROM.BIN` at `$D000`
  unconditionally, and `CPU.reset()` exists to follow the standard `$FFFC`
  reset vector into it -- but nothing in `papple2` currently calls
  `cpu.reset()` (`Emulator.load_image` only sets `PC` to the *loaded
  image's* start address), so this is untested, not just unused. Worth
  trying eventually since `A2ROM.BIN` carries a lower (not zero) licensing
  risk than a specific arcade port, but it wasn't needed once the
  `data_dir` approach was on the table, and it doesn't test the same thing
  `test_robotron.py` does (Robotron-specific memory layout and behavior).

## Open, not decided

- New repo's internal package shape for the former `examples/Robotron/*`
  files (see above).
- Whether the new repo also needs to run the workbench/pygame path without
  Excel on macOS, or is genuinely Windows-only end to end.
- Confirm `Robotron.xlsb`/`test.xlsm` are what they're assumed to be
  before moving them.
- The M7 `ExcelContext`/`raise_error` decision and verifying the remaining
  Excel functions from a live workbook -- both still open from before this
  discussion, now scoped to the new repo instead of `papple2`.
- `README.md`'s "Package split" diagram and "Testing strategy" section
  both currently describe the Robotron showcase as living inside this
  repo -- both need rewording once it's an external consumer instead
  (though the "Testing strategy" manual-check gap is already closed by
  `test_robotron.py`).
- `GOALS.md`/`ACTION_PLAN.md`: item 2 and item 4 of "Where it is going",
  and the M7 milestone description, all currently assume Robotron stays
  in-repo "as a showcase" -- reword once the split is real.
