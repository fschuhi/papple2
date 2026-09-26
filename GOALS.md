# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` (on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** `papple2` is to become a system to disassemble and understand Apple II and II+ games by running them, with Lode Runner as the worked example (`DIRECTION.md`). Two games run from their own files through a hook that stands in for the disk: Lode Runner plays real games (`RwtsHook` in `scripts/boot_lode_runner.py`, serving RWTS reads from the `.do`), and Bandits runs to level 1 from Total Replay's ProDOS files (`MliHook` in `scripts/boot_bandits.py`, `make boot-bandits`). The hook architecture review has begun: `op_hook` and the time machine are gone (`HISTORY.md` 2026-09-26). Both games run much faster than on a real Apple II.

**What's next:**
- `TODO.md` section 7, next item: write the checkpoint contract next to the `Checkpoint` alias in `core/emulator.py`. Then `post_op` as a hook point others register with, then the read/write hooks (registration instead of hand-chaining, reads a hook can answer). Test the design against `RwtsHook` and `MliHook` (their differences are in `HISTORY.md` 2026-09-26) and small assembled test programs.
- Discuss and expand `docs/reveng-catalogue.md`. Add AFK research on Ghidra and SourceGen. 
- The sweep's findings in `TODO.md` section 3 are a map, not a queue: pick them up when the fun work passes by them. For mechanical work, group files into bigger patches.
