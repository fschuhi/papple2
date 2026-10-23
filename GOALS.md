# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` reverse engineers Apple II games by running them, Lode Runner first: the run finds the routines, and Xekri's listing grades them (`make lr-grade`: 68 of 79). `make lr-current` opens the run at the prompt and in `edit()`. The documents speak one glossary (`docs/glossary.md`), and `make html` makes any of them a reading page, with listings in `edit()`'s colors and diagrams drawn by an LLM (`docs/html/`).

**What's next:**

1. Before the break, as time allows: `docs/lr_structures.md` brought up to date (`TODO.md`, "Documentation"); pruning (`TODO.md`, "Code tidying") and the project tree; a review of `TODO.md`.
2. After the break: the snapshot after relocation and the xrefs digest, then the cross reference, step 3, and xrefs while in `edit()` (`TODO.md`, "Cross reference").

**Still to prune:** the Vision in `README.md`, a draft of 2026-10-12, for me to edit (`TODO.md`, "Explaining `papple2`").

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **The tool and its use** (2026-10-11). For a while now, every step in "What's next" has been about the tool or its documentation, none about reading a game with it, and the dossier grows slower than the tool. Deliberate for now: the presentation, and the de-spaghettification it prompts, come first. The overarching goal is not Lode Runner itself (XekriRedmane has done that), but what `papple2` becomes as a product, which only real use can shape. Open: when a reverse-engineering question goes back to the top of "What's next", and which one, e.g. what `routine_64bd`, the hub of nearly everything drawn, does, or how the score is updated.

- **Routines as stretches.** What goes into the dossier apart from the annotations? How things hang together. A stretch is an entity that persists, and that collects and presents what I know about a piece of code: where it reads from, where it writes, its parameters, how it returns its value, how it changes state, its side effects. Comments cannot carry this: they nail the understanding down at a very fine-grained level. Routines cannot either: they are nodes of one run and do not persist. Three steps: first, stretches that map 1:1 to routines; second, superstretches, composed of regions that may overlap; third, substretches, which make room for the noweb chunks of `main.nw`. Stretches are objects of their own, not annotations (2026-10-09). Hidden ranges and color ranges control presentation; neither is the first implementation of stretches.
