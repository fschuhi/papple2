# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** direction-finding. `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example: Xekri's `main.nw` gives both the runnable binary and an answer key to grade every tool against. The session's collected thinking -- landscape, glossary, vision, critique, open questions -- is in `DIRECTION_DRAFT.md`, a working draft. Lode Runner boots in `papple2` (headless, demo mode) after two CPU fixes, stack wrap and decimal mode; see `HISTORY.md`. `make patch` is in place.

**What's next:**
- Review location and running of `boot_lode_runner.py`. For `Makefile`, should we run it from a test, like `test_robotron.py`?
- I'm reconsidering the direction and doing research away from the keyboard; we start from `DIRECTION_DRAFT.md` and my findings. Candidates are in `TODO.md` section 2, plus the type hints sweep (section 1), which gained weight now that `make patch` makes many-file changes cheap.
