# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is the machinery for reverse engineering Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`: dynamic first, static fills the holes; the oracle only grades). The workbench is used through commands in `shell.py`, the contract between `papple2`'s developers and its reverse engineers; experiments (`scripts/lr_*.py`) are recipes of the same commands I type at the prompt (`README.md`, "Workbench"). Finds of my own: `lookup_hgr` (`$7a3e`), and through `show_callers()` its four callers, the twins `8336`/`83a7`, `88d7` and `four_blocks` (`8a69`) with its `first_tail_call` at `8af2`. **2026-10-04, second session:** a first shadow stack, observing only (`StackTracking`, `lr_returns.csv`), built, tested and run -- and unreadable for me: addresses only, no labels, and code I don't understand. The same path that ended Robotron (`HISTORY.md`, 2026-10-04). Orientation comes before more analysis.

**What's next:**
- First, orientation: the listing editor (`TODO.md`, "Dossier and prompt": the prototype is ready, steps 1 to 4 are specified), so that labels and comments come at the speed of reading. Confirm at the start of the session that this is the next step, and size its first slice small.
- With it, small views that give a sense of location: `routine_of(address)` (the routine or routines an address lies in), and labels wherever an address is printed.
- The shadow stack stays as it is: observing, tested, its report under git. Before it is extended, `stack_tracking.py` is rewritten in plain style and read together, line by line (`TODO.md`, "Workbench").
- Later: folding the shadow stack into the routines (tail calls, stack jump tables); the HGR "ray"; a spike into Bandits.
- Alongside: pruning the `instrumentation-*.md` documents (inventory 2026-10-02, decisions open).

---

## Strategic questions

Goals that need a strategy discussion before they are actionable.

- **Orientation before analysis** (2026-10-04, from the first shadow stack report, and from Robotron before it). An analysis only helps when its result arrives where I can read it: at the prompt, in a listing, with labels, ideally as a picture of trees and woods. A report only an LLM can read does not advance my understanding. Open: how each new analysis is checked against this before it is built -- e.g. by asking first what I will see at the prompt, and in which listing, when it is done.

- **Routines as stretches.** A routine might map onto a "stretch". Still fuzzy: stretches that contain substretches (a routine's loops, entries into shared code); how stretches get their names (the oracle protocol); and how they relate to the noweb chunks of `main.nw`, which are named, nested pieces of code as well. Note: until now "stretch" was reserved for a container of reports; this would give the word a meaning in the code. Since 2026-10-03, the dossier keys labels and comments by address; stretches would add named, nested ranges to it. The first case may come with tail calls and stack jump tables (`TODO.md`), where routines stop being "the blocks reachable from a `JSR` target".
