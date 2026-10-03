# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). **Milestones 2026-10-03:** it's a workbench now. What we learn stays: Lode Runner's dossier (`dossiers/lode_runner/annotations.json`, under git) keeps labels and comments across runs and IPython sessions, and `listing()` shows them. And the whole run is at the prompt: after `%run scripts/lr_basic_blocks_analysis.py`, `show_routines()` lists all 68 routines and `show_blocks(entry)` shows any one of them, both with the dossier's labels. Still rough around the edges; the next work streamlines it, so it's fun to work with and learning goes fast.

**What's next:**
- First, a quick win that has waited long: zero-page operands show their labels (`TODO.md`, "Small code steps").
- An architecture review, before new tools: what belongs in a script and what in the workbench (the Lode Runner script now finds routines and defines the prompt's commands), `shell.py`'s growth, where routines are found (`find_entries()` in a script).
- Then the first tool priority: tail calls and stack jump tables, integrated into the structural analysis -- unclear how; the dominator analysis may not cope, and this may be where stretches begin (below, and `TODO.md`). Also the tools a spike into Bandits needs.
- The second, a big theme: the HGR "ray" -- loads and stores into HGR1/HGR2, and which tiles and structures they fall on (`TODO.md`).
- Alongside: the prompt items in `TODO.md` ("Dossier and prompt"), and pruning the `instrumentation-*.md` documents (inventory 2026-10-02, decisions open).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Since 2026-10-03, the dossier keys labels and comments by address; stretches would add named, nested ranges to it. The first case may come with tail calls and stack jump tables (`TODO.md`), where routines stop being "the blocks reachable from a `JSR` target".
