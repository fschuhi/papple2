# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). **Milestones 2026-10-02:** the workbench's first pipeline (`Tiling` records what ran, the basic blocks analysis finds blocks, dominators and loops; on `LOAD_LEVEL` exactly the oracle's four loops), and then the first look at the code itself. A tiny program, two nested loops and one `JSR`, went through the whole pipeline and is now a story in tests (`tests/test_walkthrough.py`). In IPython, `dis()` shows a range from memory after the run, with names given by hand and the jumps the run took as arrows; `scripts/lr_basic_blocks_analysis.py` brings `LOAD_LEVEL` there, where the listing already shows a first hypothesis: two 4-bit values per byte, unpacked at `627e`-`6292`.

**What's next:**
- The IPython slice's second half (`docs/workbench-ideas.md`, section 13): `name()` and `comment()`, saved in a session file under git and always in sync with the session. Names follow the oracle protocol: hypothesis first, then the name, then the oracle. `LOAD_LEVEL` is the first routine to name.
- A whole-run view at the prompt: every basic block with its runs, the pieces in no routine marked (`TODO.md`).
- Sharpen "routine = `JSR` target" for `PHA-PHA-RTS` and tail jumps (a shadow stack, `TODO.md`): the tools a spike into Bandits needs.
- Prune the `instrumentation-*.md` documents: the inventory was done on 2026-10-02, the decisions are open.
- Alongside: the small code steps and the parked work in `TODO.md`.

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Worth settling before the IPython slice fixes its data model.
