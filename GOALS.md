# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example (`DIRECTION.md`). The instrumentation is being rebuilt from scratch. The decisions are in `docs/instrumentation-design.md` (2026-09-29), and the first part is in place: `CPU` and `Memory` name every access by its kind (`read_opcode`, `read_operand`, ..., `write_stack`) at no measurable cost, and the disassembler reads the memory list directly. There are no hooks yet. Four boots run (`make boot-basic`, `boot-robotron`, `boot-lode-runner`, `boot-bandits`), and the two disk stand-ins are traps.

**What's next:**
- Step 4: the hook lists and the fields a hook may read, measured with all lists empty (`TODO.md` section 7).
- Step 5: breakpoints and traps at the `Emulator`'s boundary.
- Step 6: the execution-count map on Lode Runner inside a level, the first real output of the new instrumentation, run together.
- Alongside: the small code steps in `TODO.md` section 8.
- Discuss and expand `docs/reveng-catalogue.md`. Add AFK research on Ghidra and SourceGen. 
