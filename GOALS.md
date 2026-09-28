# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example (`DIRECTION.md`). The old instrumentation is gone (`HISTORY.md` 2026-09-27/28): `papple2` is an emulator again, with four boots (`make boot-basic`, `boot-robotron`, `boot-lode-runner`, `boot-bandits`), the two disk stand-ins as address traps, and Apple II speed on request (`make boot-lode-runner-throttled`). The redesign of the instrumentation starts from `docs/instrumentation-ideas.md` (the braindump) and `docs/instrumentation-map.md` (the "before" picture, pinned to the tag `pre-redesign`).

**What's next:**
- Open the design phase with an in-depth discussion: `pysm`, yes or no (`TODO.md`).
- Turn the braindump into a design document, structure first, experiments afterwards: the machine seam, one record per instruction or one event per access, roles, the lifecycle of a step.
- Alongside, the small code steps in `TODO.md`: the assembler bug, uppercase defaults in `util.py`, the stale comments in the stand-ins, `graphviz` in `requirements.txt`.
- Discuss and expand `docs/reveng-catalogue.md`. Add AFK research on Ghidra and SourceGen. 
