# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the workbench for reverse engineering Apple II games by running them, with Lode Runner as the worked example. Dynamic first; the oracle only grades. I can run a game, see its routines, blocks and loops at the prompt, and all its routines in one picture. A routine ends where another begins, and every way into it is an arrow of its kind, stack jumps included: no code that ran is left without a routine. What I learn stays in the dossier. Two terminals can work on one dossier, `hexdump()` shows data tables, and `clip()` copies what a command showed. Since 2026-10-08 I read code in the new editor: `edit()` opens a routine right under the prompt, Enter follows a `JSR` into the routine it calls, Backspace brings me back and `f` forward again, `g` goes to any routine, breadcrumbs say where I am, and labels and comments are given in place.

**What's next, in this order:**

1. Callers in the editor's picker: a key opens the callers of the routine shown, as `show_callers()` knows them, and Enter goes up to the `JSR`. Short; the picker is there since Go To.
2. The HGR ray, shaped 2026-10-08: from a pixel of the score up to the code that keeps the score. First slice: `Watching`, an instrumentation for named address ranges, in a new experiment on the score row; `show_watches()` lists who wrote there, with routine and labels. See `TODO.md`, "Who writes where".
3. The way up: `StackTracking` writes when each frame opened and closed (`lr_frames.csv`); the backtrace of a write is the frames open at its moment. The paths that led into a watched range then filter the callers in the picker.
4. Region recovery.

**Still to prune:** `README.md`. The Dev parts and the data files move out, `docs/decisions.md` gets thinned, and the Vision is rewritten (remember, appreciate, tinker, create; no history).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **Routines as stretches.** What goes into the dossier apart from the annotations? How things hang together. A stretch is an entity that persists, and that collects and presents what I know about a piece of code: where it reads from, where it writes, its parameters, how it returns its value, how it changes state, its side effects. Comments cannot carry this: they nail the understanding down at a very fine-grained level. Routines cannot either: they are nodes of one run and do not persist. Three steps: first, stretches that map 1:1 to routines; second, superstretches, composed of regions that may overlap; third, substretches, which make room for the noweb chunks of `main.nw`.
