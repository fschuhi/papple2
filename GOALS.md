# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the workbench for reverse engineering Apple II games by running them, with Lode Runner as the worked example: dynamic first, the oracle only grades. Routines, blocks, loops and callers are available at the prompt and in the listing editor; what I learn stays in the dossier: labels, comments, hidden ranges and color ranges. The colors carry that knowledge into every view: listings by location, the editor by syntax and by the tables its operands name, the hexdump by byte, and `memory_map()` across any stretch of memory, from all 64 KB down to single bytes. One `Session` holds the state of a working session. Seven diagrams made from the code show the structure; `PRESENTATION.md` holds the script for presenting it. The walkthrough, a book of chapters that are tests, takes two tiny programs through the whole pipeline, and renders as a document. The first case study reads real code with all of it: drawing and erasing a sprite, in `docs/lr_case_studies.md`, with the naming rules every label follows. Since 2026-10-13 the cross reference counts every byte the code touches, by instruction, in `lr_xrefs.csv`; the walkthrough's third program, `memory_tour`, explains it.

**What's next:**

1. The cross reference, step 3: reading the report back, and `show_xrefs()` (`TODO.md`, "Cross reference"). First light, `show_xrefs("tbl_hx_byte")`, is mine to run at the prompt. How: one finding at a time, each with the rows or the command that shows it; nothing from code the program has overwritten (e.g. the relocation, hidden in `routine_0800`).

**Still to prune:** the Vision in `README.md`, a draft of 2026-10-12, for me to edit (`TODO.md`, "Explaining `papple2`").

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **The tool and its use** (2026-10-11). For a while now, every step in "What's next" has been about the tool or its documentation, none about reading a game with it, and the dossier grows slower than the tool. Deliberate for now: the presentation, and the de-spaghettification it prompts, come first. The overarching goal is not Lode Runner itself (XekriRedmane has done that), but what `papple2` becomes as a product, which only real use can shape. Open: when a reverse-engineering question goes back to the top of "What's next", and which one, e.g. what `routine_64bd`, the hub of nearly everything drawn, does, or how the score is updated.

- **Routines as stretches.** What goes into the dossier apart from the annotations? How things hang together. A stretch is an entity that persists, and that collects and presents what I know about a piece of code: where it reads from, where it writes, its parameters, how it returns its value, how it changes state, its side effects. Comments cannot carry this: they nail the understanding down at a very fine-grained level. Routines cannot either: they are nodes of one run and do not persist. Three steps: first, stretches that map 1:1 to routines; second, superstretches, composed of regions that may overlap; third, substretches, which make room for the noweb chunks of `main.nw`. Stretches are objects of their own, not annotations (2026-10-09). Hidden ranges and color ranges control presentation; neither is the first implementation of stretches.
