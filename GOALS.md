# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example (`DIRECTION.md`). Lode Runner now runs in the pygame window faster than on a real Apple II, after the window-polling fix. A key press in attract mode hangs in the game's RWTS, since `papple2` has no disk drive. The manual with-window checks are scripts (`make boot-*`); see `HISTORY.md`, 2026-09-23.

**What's next:**
- Type hints sweep, `TODO.md` section 1, one file per step. `make patch` makes the many-file steps cheap.
- Then: my research away from the keyboard, and `DIRECTION.md`. Candidates are in `TODO.md` section 2, among them Lode Runner real play via an RWTS hook and the level extraction for `a2-lode-runner`.
