# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). **Milestone 2026-10-01: the core is complete.** The instrumentation, rebuilt from scratch after the pruning of 2026-09-28, follows `docs/instrumentation-design.md`: nine kinds of memory access with hook lists, `after_instruction`, `attach()` by method name. Two experiments run on it: `lr_count.py` (the execution map) and `lr_tiles.py` (tiles split into disjoint basic blocks after the run, with their transitions). Four boots run (`boot-basic`, `boot-robotron`, `boot-lode-runner`, `boot-bandits`), and the two disk stand-ins act as traps.

**What's next:**
- The workbench's first slice (`docs/workbench-ideas.md`, section 13), with `LOAD_LEVEL` as the first target, thinking in chunks from the start.
- Structure detection as one workbench command, graded against the oracle on `LOAD_LEVEL` (`docs/workbench-ideas.md`, sections 6 and 7).
- Refactor the `instrumentation-*.md` files.
- Discuss and expand `docs/reveng-catalogue.md`.
- Alongside: the small code steps in `TODO.md`.
