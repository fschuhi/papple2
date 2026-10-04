# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the machinery for reverse engineering Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). **2026-10-04:** the workbench is used through commands in `shell.py`, the contract between `papple2`'s developers and its reverse engineers. Experiments (`scripts/lr_*.py`) hold recipes of the same commands I type at the prompt -- `run(lode_runner, n, Tiling)`, `tiling_reports()`, `show_routines()`, `listing()`, `label()` -- and their own functions graduate to the shell once they prove useful beyond them. My role is shifting from junior developer towards product manager and reverse engineer; `README.md` ("Workbench": experiments and recipes, the namespace at the prompt, the glossary) is the reference. The first find of my own: `lookup_hgr` at `$7a3e`, the hi-res row address on both pages, called 30,406 times. The early experiments (`lr_count`, `lr_tiles`) are frozen as they are.

**What's next:**
- Quick win: the callers of a routine at the prompt (`JSR` and `JMP`, with counts); and the labels in snake case (`LOOKUP_HGR`, `ROUTINE 001`).
- Then the first slice of the shadow stack, observing only: an instrumentation through `run()` that records the stack operations, including direct writes to page 1, and a report of every `RTS` whose target lies behind no matching `JSR`. It also shows whether `run()` building instrumentations from the CPU is enough for memory hooks (`TODO.md`).
- Then folding it into the routines: tail calls and stack jump tables, and what they mean for the dominator analysis and for stretches (below, and `TODO.md`).
- Later: the listing editor (the prototype is ready), once labelling volume makes `label()` and `comment()` slow; the HGR "ray"; a spike into Bandits.
- Alongside: pruning the `instrumentation-*.md` documents (inventory 2026-10-02, decisions open).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Since 2026-10-03, the dossier keys labels and comments by address; stretches would add named, nested ranges to it. The first case may come with tail calls and stack jump tables (`TODO.md`), where routines stop being "the blocks reachable from a `JSR` target".
