# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example (`DIRECTION.md`). The instrumentation is being rebuilt from scratch, following `docs/instrumentation-design.md`. Step 4 is complete: `Memory` reports every access by its kind to its own hook list (`after_read_opcode` ... `after_write_stack`), and `CPU` counts its instructions (`instruction_count`) and calls `after_instruction` after each one. Nothing uses the hooks yet. Every test module is in `pytest` style. Four boots run (`make boot-basic`, `boot-robotron`, `boot-lode-runner`, `boot-bandits`), and the two disk stand-ins are traps.

**How to work in the next session** (the user's feedback, `HISTORY.md` 2026-09-29, third session): one thing per message, in plain words, no idioms. Say what a step is for, and how it brings us closer to something the user can see, before saying how it is done. Keep the big picture in view: the hooks exist so that we can watch Lode Runner run and think in the terms we track. Do not suggest a fresh conversation unless asked.

**What's next:**
- Head for something visible soon: the execution-count map (Step 6) is the first thing the hooks can show. Discuss at the start whether Step 5 (breakpoints and traps at the `Emulator`'s boundary) must come first, or whether a first, simple count on Lode Runner can come before it.
- Step 6: the execution-count map on Lode Runner inside a level, the first real output of the new instrumentation, run together. Decide there how experiments attach their hooks.
- Reserve time for looking at the results: report generators in HTML, or queries in Jupyter.
- Alongside: the small code steps in `TODO.md` section 8.
- Discuss and expand `docs/reveng-catalogue.md`. Add AFK research on Ghidra and SourceGen.
