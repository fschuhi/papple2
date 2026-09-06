# papple2 -- History

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

- The resolved-work record: what was built and when (note date, or have the points in roughly reverse-chronological order).
- This is the trophy case -- kept in the repo, **out of the per-session filesdump** (so it no longer rides along every session).
- For *forward* work see `TODO.md`; for direction see `GOALS.md`; for the architecture as it stands see `README.md`.
- See "Workflow for the Whole Session (CRITICAL)" in `LLM_INSTRUCTIONS.md` for the interplay between `TODO.md` and this file. 

---

## 2026-09-06 -- Imports untangled

- Untangled the circular import between `Emulator`, `Hooks`, `Checkpoints`.
- Replaced `from X import *` with explicit imports.

## 2026-09-06 -- M2

- Replaced hardcoded Windows paths with `papple2.toml` (local, gitignored; `papple2.example.toml` committed instead), no `os.chdir` needed anymore. Also swept up `args.savemem`'s `dat\test.dat` (now under `data_dir`) and the Graphviz `PATH` hack in `Tiles.py` (removed; `dot` now found via `brew install graphviz`).
- Removed `util.msgbox`; would need Tkinter; no callers existed anywhere in the codebase.
- Vanilla `pygame` 2.6.1 doesn't build/run correctly under Python 3.14 yet (open upstream issue); venv recreated under Python 3.12 instead, resolved. Documented in `README.md`.
- `make run` opens the pygame window, runs the Robotron binary from `data/bin/`, and Ctrl-X stops and resumes execution. The animated Robotron splash screen renders correctly on macOS.

## 2026-09-05 -- M1

- `src/papple2` is a real, installable package (`pyproject.toml`, editable install wired into the `Makefile`).
- Prefixed all internal imports with `papple2` (mechanical prefix only); star-imports (`import *`) kept as-is on purpose. Converting to explicit names is M4 work, not this.
- Split `tests.py` into per-class files under `tests/`, all green.
- `TestWaves.test_input_wave` marked `@unittest.skip`; left as-is, including the `sys.exit(0)` and the dead code after it. Revisit later, not now.

## 2026-09-03 -- Inaugural papple2 session

Revival of the emulator after the Robotron 2084 project went dormant. Full read-through of the code base with Claude (Fable 5.1). Result: `ACTION_PLAN.md` with milestones M1 (tests green on macOS) to M8 (documentation), ordered by cheapest visible value. The target-state list moved from `GOALS.md` to `ACTION_PLAN.md`; `GOALS.md` now holds only the vision and the session pointer; `TODO.md` holds the M1 tasks. Main findings: Windows-only paths, `pytest` missing from requirements, two identical `tests.py`, `from X import *` throughout, Robotron-specific behaviour inside `Memory.write_byte`. No code changed.
