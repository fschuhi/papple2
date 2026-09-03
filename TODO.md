# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## Session housekeeping (this session)

- Draft an addition to `LLM_INSTRUCTIONS.md` or `CRITICAL_RULES.md` (TBD which): explanations in plain language, no jargon, no invented terminology or idioms; short sentences over clever ones.
- Add `ACTION_PLAN.md` to `manifest.lst` under "Context & Meta".
- Create `HISTORY.md` entry for the inaugural session: action plan written, target state moved, `GOALS.md` and `TODO.md` rewritten.

## M1 -- Tests run and are green on macOS

- _Needs investigation_: decide the package layout before touching any file. Options: (a) keep `src/papple2/` and make it a real package with `from papple2.Memory import Memory` everywhere; (b) keep the flat top-level imports and add `src/papple2` to the path in the `Makefile`. Option (a) is what `load-runner` needs later; option (b) is the smaller change. Decide, then record the decision in `README.md`.
- Add `pytest` to `requirements.txt`.
- Update the `Makefile` test targets so `pytest` finds both the tests and the package, according to the layout decision.
- Convert `tests.py` into pytest files in `tests/`, one file per topic, named `test_<topic>.py` (for example `test_memory.py`, `test_cpu_load_store.py`, `test_cpu_branches.py`, `test_assembler.py`). Keep the test bodies as they are; only the framework changes.
- Remove `src/papple2/tests.py` once the conversion is done (it is an identical copy of `tests/tests.py`).
- Fix file paths used by the tests: `bin\ROBOTRON.BIN` -> `data/bin/ROBOTRON.BIN`; `tmp\ROBOTRON#062DFD.BIN` -> `tmp/...`. Make paths relative to the repo root.
- Tests that construct `Apple2(no_display=False)` open a pygame window. Change to `no_display=True` where the test does not need the screen, or mark the test so it can be skipped in a headless run.
- Run `make test`; everything green closes M1.

## Scratchpad

- `util.py` has a Windows-only `msgbox` (uses `ctypes.windll`). Remove or replace in M2.
- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- `Memory.write_byte2` looks like an older version of `write_byte`. Check whether anything calls it; remove in M4 if not.
