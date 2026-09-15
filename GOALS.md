# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` or `CHANGELOG.md`(on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** M8 (documentation) is done. `README.md` was rewritten for the public, post-carve-out state of the project -- reworded architecture diagrams, three new ones (extension points, the `CPUHook` chain, tiles/stretches/call trees), three screenshots, a "Data files" section, a Contents TOC -- and absorbed `GOALS.md`'s old "Strategic vision" (now removed from this file, see `HISTORY.md`). `ACTION_PLAN.md`, fully executed across M1 through M8, has been deleted from the repo (a copy kept in `tmp/` locally).

**What's next:** the type hints sweep (`TODO.md` section 1). Production code in `src/papple2/` only, test files/fixtures out of scope for now. Core before debug, one file per approved step: `util.py`, then `core/apple.py`/`cpu.py`/`memory.py`/`window.py`/`emulator.py`/`hooks.py`, then the `debug/` package.
