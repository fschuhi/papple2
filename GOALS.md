# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the workbench for reverse engineering Apple II games by running them, with Lode Runner as the worked example. Dynamic first; the oracle only grades. Routines, blocks, loops and callers are available at the prompt and in the editor; what I learn stays in the dossier. Since 2026-10-09, `hide()` sets overwritten code aside as one grey row in `listing()` and `edit()`, persisted in `hidden.json`. Named color ranges persist separately in `colors.json`: every breadcrumb uses its assigned color, only the current one bold; long listings color code by location while comments and arrows stay unchanged. The editor deliberately has no line coloring. Copied listing text remains plain. Both hiding and initial coloring were checked in the real IPython workflow.

**What's next, in this order:**

1. Finish the agreed color views in small steps: referenced operands, Graphviz nodes, then the static memory map. The map is wanted for the presentation on Sunday, 2026-10-11; if time is tight, explicitly decide whether to move it ahead of the other views. `TODO.md`, "Coloring and memory map", carries the contracts and open presentation choices.
2. Navigation: Ctrl-based paging bindings for my Karabiner Elements remapping, plus `i` and `m` for the previous and next label. These are different movements, not substitutes.
3. The HGR ray: a design session first. The shape of 2026-10-08 (`Watching`, `show_watches()`, the frames of `StackTracking`, the callers filtered by the paths into a watched range) is not settled enough to build on. Actual store destinations can use the shared color system later; they are not part of static operand coloring.
4. An architecture and design review, with slides and a revised `README.md` where needed; a code review of single modules, starting with how to read a list comprehension; a script for the live demo on Sunday 2026-10-11 (which experiment, which routines in which order, which commands, when the editor).
5. Region recovery.

**Still to prune:** `README.md`. The Dev parts and the data files move out, `docs/decisions.md` gets thinned, and the Vision is rewritten (remember, appreciate, tinker, create; no history).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **Routines as stretches.** What goes into the dossier apart from the annotations? How things hang together. A stretch is an entity that persists, and that collects and presents what I know about a piece of code: where it reads from, where it writes, its parameters, how it returns its value, how it changes state, its side effects. Comments cannot carry this: they nail the understanding down at a very fine-grained level. Routines cannot either: they are nodes of one run and do not persist. Three steps: first, stretches that map 1:1 to routines; second, superstretches, composed of regions that may overlap; third, substretches, which make room for the noweb chunks of `main.nw`. Stretches are objects of their own, not annotations (2026-10-09). Hidden ranges and color ranges control presentation; neither is the first implementation of stretches.
