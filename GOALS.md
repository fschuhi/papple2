# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is a system to disassemble and understand Apple II games by running them, with Lode Runner as the worked example (`DIRECTION.md`). The instrumentation is being rebuilt from scratch, following `docs/instrumentation-design.md`. The `scripts/lr_tiles.py` experiment now perfectly maps dynamic execution traces into strictly disjoint Basic Blocks (stretches) through a mathematically verified post-run transformer, fully resolving overlapping control flow with zero hot-loop overhead. Four boots run (`boot-basic`, `boot-robotron`, `boot-lode-runner`, `boot-bandits`), and the two disk stand-ins act as traps.

**What's next:**
- `read_immediate` in `core` (`TODO.md` section 7), the base for detecting self-modifying code.
- Refactor the `instrumentation-*.md` files.
- Discuss and expand `docs/reveng-catalogue.md`. Add AFK research on Ghidra and SourceGen.
- Generate more candidates for further experiments, to discuss: names from `main.nw` in the map (which named routines ran), the instruction count at which each address first ran (the game's phases), differential maps (with and without a dig), self-modifying code detection.
- Alongside: the small code steps in `TODO.md` section 8.
