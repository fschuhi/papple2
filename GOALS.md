# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). **Milestone 2026-10-02: the workbench's first pipeline.** `Tiling` records what ran and writes its reports into a folder; the basic blocks analysis reads them and finds basic blocks, dominators and natural loops. Its first run on `LOAD_LEVEL` found the oracle's four loops, exactly. `lr_overview.py` shows the whole attract play -- 68 routines, 42 loops -- with first hypotheses: the main loop, the relocation, twin routines, a probable jump table.

**What's next:**
- A walkthrough of how the reports come about: a tiny 6502 program (about ten instructions, one loop, one `JSR`) through `Tiling` and the basic blocks analysis, predicting each report's rows before looking. At that size, following the thread of execution by hand is still possible, so it shows what the tools do mechanically at 10,000 transitions.
- A disassembler for what ran: it reads memory after the run (the game relocates its code), shows a block, a loop or a routine in `dasm` style with the loops indented, and takes labels from the names the user gives (the oracle protocol in `README.md`). Use case: disassemble a routine while analysing its structure; put twin routines side by side.
- The IPython workbench's first slice (`docs/workbench-ideas.md`, section 13): a session that holds the run, with the disassembler as its first command, plus `name()` and `comment()` saved in a session file under git.
- Prune the `instrumentation-*.md` documents: the inventory was done on 2026-10-02, the decisions are open.
- Alongside: the small code steps and the parked work in `TODO.md`.

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Worth settling before the IPython slice fixes its data model.
