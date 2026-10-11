# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the workbench for reverse engineering Apple II games by running them, with Lode Runner as the worked example. Dynamic first; the oracle only grades. Routines, blocks, loops and callers are available at the prompt and in the editor; what I learn stays in the dossier. Since 2026-10-09, `hide()` sets overwritten code aside as one grey row in `listing()` and `edit()`, persisted in `hidden.json`. Named color ranges persist separately in `colors.json`: every breadcrumb uses its assigned color, only the current one bold; long listings color code by location while comments and arrows stay unchanged. The editor deliberately has no line coloring. Copied listing text remains plain. Both hiding and initial coloring were checked in the real IPython workflow. Since 2026-10-10 the state of a working session lives in one `Session` object, `shell.session`, and the commands are thin wrappers around it. Since 2026-10-11, seven diagrams made from the code show the packages, the workbench by role, the machine, one pass of the run loop, the pipeline, the listing and the editor, and the emulator's states; `make presentation` renders them, and `PRESENTATION.md` holds the script for each slide and the demos. The code that builds a listing lives in `listing.py`, the part that reads state in the `Session`.

**What's next, in this order:**

1. Syntax coloring, in the editor only; `listing()` keeps its range colors as beacons (`TODO.md`, "Coloring and memory map").
2. Operand colors by the address the operand names, e.g. the table base in `LDA table,Y` (`TODO.md`, "Coloring and memory map"). By the final address, for `(zp),Y`, only once the cross reference exists.
3. The static memory map, and colors in `hexdump()`, which has none yet (`TODO.md`, "Coloring and memory map").
4. Revisit the walkthrough and write `walkthrough.md` (`TODO.md`, "Explaining `papple2`").
5. Real-world examples for `Tiling` and `StackTracking` from Lode Runner, homing in with `show_routines()`, added to `walkthrough.md`.
6. The cross reference (`TODO.md`, "Cross reference").
7. The README pruning (`TODO.md`, "Explaining `papple2`").

**Still to prune:** `README.md`. The Dev parts and the data files move out, `docs/decisions.md` gets thinned, and the Vision is rewritten (remember, appreciate, tinker, create; no history). Details, with the additions of 2026-10-11: `TODO.md`, "README pruning".

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **The tool and its use** (2026-10-11). For a while now, every step in "What's next" has been about the tool or its documentation, none about reading a game with it, and the dossier grows slower than the tool. Deliberate for now: the presentation, and the de-spaghettification it prompts, come first. The overarching goal is not Lode Runner itself (XekriRedmane has done that), but what `papple2` becomes as a product, which only real use can shape. Open: when a reverse-engineering question goes back to the top of "What's next", and which one, e.g. what `routine_64bd`, the hub of nearly everything drawn, does, or how the score is updated.

- **Routines as stretches.** What goes into the dossier apart from the annotations? How things hang together. A stretch is an entity that persists, and that collects and presents what I know about a piece of code: where it reads from, where it writes, its parameters, how it returns its value, how it changes state, its side effects. Comments cannot carry this: they nail the understanding down at a very fine-grained level. Routines cannot either: they are nodes of one run and do not persist. Three steps: first, stretches that map 1:1 to routines; second, superstretches, composed of regions that may overlap; third, substretches, which make room for the noweb chunks of `main.nw`. Stretches are objects of their own, not annotations (2026-10-09). Hidden ranges and color ranges control presentation; neither is the first implementation of stretches.
