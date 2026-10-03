# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the machinery for reverse engineering Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). The reverse engineering itself is meant to happen with an LLM reading reports, without `papple2`'s code: the `lr-` targets are prepackaged analyses whose reports carry meaning on their own; IPython is for ad hoc exploration, and Lode Runner's dossier (`dossiers/lode_runner/annotations.json`, under git) keeps the labels and comments given there. **2026-10-03:** the architecture review began (workbench functions, no `Workbench` class). Every routine of the run is found in one place (`find_routines()`), `listing()` draws arrows everywhere, and `make lr-basic-blocks-analysis` is the first target whose reports are under git (`docs/reports/lr_basic_blocks_analysis/`, loop reports of `$0800` on every run).

**What's next:**
- First: reports under git for the other `lr-` targets (`lr-tiles` first, which `lr-overview` reads), and how a report says what it is and where it came from, so an LLM can read it cold (`TODO.md`).
- Then the rest of the architecture review: a workbench function for the standard run (`Tiling`, run, reports), used by the Lode Runner script and the walkthrough; the prompt's commands by entry (`TODO.md`, "Dossier and prompt").
- Then the first tool priority: tail calls and stack jump tables, integrated into the structural analysis -- unclear how; the dominator analysis may not cope, and this may be where stretches begin (below, and `TODO.md`). Also the tools a spike into Bandits needs.
- The second, a big theme: the HGR "ray" -- loads and stores into HGR1/HGR2, and which tiles and structures they fall on (`TODO.md`).
- Alongside: pruning the `instrumentation-*.md` documents (inventory 2026-10-02, decisions open).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Since 2026-10-03, the dossier keys labels and comments by address; stretches would add named, nested ranges to it. The first case may come with tail calls and stack jump tables (`TODO.md`), where routines stop being "the blocks reachable from a `JSR` target".
