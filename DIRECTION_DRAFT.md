# papple2 -- Direction (working draft, 2026-09-23)

(Note: "I" in the following paragraphs refer to the user, "you" to the AI model.)

**Status:** first draft from a collection-mode session. Nothing here is decided unless it sits under "Decided". Where this content finally lands (`GOALS.md`, `README.md`, `TODO.md`, or a document of its own) is an open question at the end.

---

## 1. Direction in one paragraph

`papple2` becomes a system to disassemble and understand Apple II and II+ games (48k, hi-res, no aux or language card memory) by *running* them. It is not general disassembly software but a kit of fairly generic parts, put together per game. Its place in the landscape is the corner that is still mostly empty: dynamic analysis whose results accumulate into documentation, instead of evaporating when the debugger session ends. It complements static and agent-driven approaches rather than competing with them.

## 2. Worked example and targets

- **Lode Runner** is the worked example. Xekri's `main.nw` tangles to `dasm` source that assembles byte-identically to the original, so it gives us both a runnable binary and an answer key (every routine, label, and data region named). Every tool can be graded against it.
- **Later targets:** games without an answer key, e.g. Bandits (the dream project) or Choplifter. Both fit the 48k II/II+ focus.
- **Robotron** steps back from the documentation. `probotron` is hibernated and stays private.

## 3. Decided this session

- `papple2` accepts patches via `make patch` (done: `Makefile` target, `*.patch` in `.gitignore`).
- Work is fully macOS native.
- No Excel workbench and no PyXLL bridge going forward. One-way `.xlsx` reports are a dead end without a back channel.
- MAME is not a base for `papple2` (large C++ codebase, Lua instead of Python, breaks the "emulator and tools in one language" idea). It may still serve as a reference for what real hardware does.
- For byte-perfect reassembly, use `dasm` (the syntax of `main.nw`). `papple2`'s own assembler stays a test tool.
- Reports are static HTML pages: run, break, inspect, generate specific reports, show them alongside other named runs, expand and collapse parts with JavaScript.

## 4. Landscape (prior art)

Two axes: static (reads the bytes) vs. dynamic (runs the game), and knowledge thrown away vs. knowledge accumulated.

- **Static, accumulating:** SourceGen (Windows, WPF; Wine reported to work), Ghidra, IDA, `da65`; Xekri's `reveng.md` process, an autonomous LLM agent that produces a byte-perfect `main.nw` from a disk image and deliberately uses no emulator.
- **Dynamic, thrown away:** AppleWin debugger, Virtual II (macOS; Quinn Dunki's main tool for Choplifter), MAME debugger.
- **Dynamic, accumulating -- the closest existing paradigms, mostly from other scenes:**
  - NES: FCEUX's Code/Data Logger (marks every byte as executed, read as data, or both, while the game runs); Mesen (trace logger, event viewer, memory access highlighting, sprite viewers, Lua scripting).
  - C64: C64 Debugger (live memory map colored by reads and writes).
  - General: omniscient debugging (record once, query any moment later; e.g. Pernosco on top of `rr`); shadow memory (Valgrind); dynamic taint tracking and data provenance (security research).
- _Needs investigation:_ is there an Apple II emulator with a Code/Data Logger or provenance tracking? Not known to us yet.
- The Robotron workbench independently arrived at two of these ideas: the memory heatmap (a Code/Data Logger) and "record everything, step through the recording" (omniscient debugging). "Mem of interest" corresponds to logging filters / trace conditions.

## 5. Vision (curated brain dump, grouped)

Nothing here is prioritized yet. Established terms in parentheses.

**Observe**
- Collect tiles while executing (dynamic CFG recovery, code coverage).
- Mark bytes as executed / read / written (Code/Data Logger, access heatmap).
- Which addresses are loaded from (memory access trace, with logging filters).
- Detect self-modifying code (writes into bytes that were executed).
- Track `JSR`/`RTS` and tail calls to identify subroutines (function boundary detection).
- Complex tracers, watchers, listeners, loggers via hooks (instrumentation).

**Interpret**
- Trace a hi-res byte back to its sources (data provenance via shadow state; see section 7).
- Semi-automated hierarchical loop detection (natural loops, back edges).
- Lo/hi table detection and table size reasoning (split address tables).
- Infer table semantics from the Apple II memory layout (e.g. hi-res row base address tables).
- Hypotheses about the game loop.

**Record**
- Snippets held lightly, so knowledge coagulates around them (stubs, provisional labels, hypotheses).
- Generate noweb Markdown for tangling and weaving.

**Interact**
- Interactive monitor mode (like AppleWin's debugger): break, inspect named zero page entries, ask which tile or stretch we are in, where a pixel came from; run Python at a breakpoint.
- Complex programmable breakpoints.
- Experiments while running, in Dunki's style: stub a routine with `RTS`, change memory, redirect a pointer, break and step out to find the main loop.
- Save and load complex state; time machine (reverse debugging).

**Report**
- Static HTML reports per named run, side by side, collapsible.

## 6. Glossary (first pass)

"Close" = same concept. "Related" = overlapping, forcing the standard name would mislead.

| `papple2` term | Established term | Match |
|---|---|---|
| tile | basic block | close |
| stretch | trace; extended basic block / superblock | related -- a JIT trace is a hot path, a stretch is a chain of fixed transitions |
| call tree | call graph; control-flow graph at block level | close |
| collect tiles while executing | dynamic CFG recovery; code coverage | close |
| heatmap of loads/saves/executions | Code/Data Logger; memory access heatmap | close |
| time machine | reverse debugging; time-travel debugging; record/replay | close |
| record everything, step through it | omniscient debugging | close |
| `MemAccessCollector` | memory access trace | close |
| mem of interest | logging filter; trace condition; watch range | close |
| hooks | instrumentation; taps (MAME); probes | close |
| where did this byte come from | data provenance; dynamic taint tracking; backward slicing | close |
| JMP instead of JSR + RTS | tail call | close |
| lo/hi tables | split address tables; "RTS trick" for jump tables | close |
| snippet held lightly | stub; provisional label | related |

## 7. First concrete question (candidate)

Assume a memory range looks like sprite data (from hex and binary viewing). When a single byte in HGR1 changes: which `STA` wrote it, which tiles led there, and did the written value originate in the suspected sprite range?

Approach: next to each register and memory byte, keep a set of source addresses (shadow state). Loads set the source, combining instructions (`ORA`, `EOR`, `AND`) merge sets, stores pass the set on. The changed screen byte then carries its sources; the tile path comes from the recorded instructions before the store. Lode Runner's `main.nw` provides the answer to check against.

Could-extension: run over a whole frame, every byte that ever flows to the screen is marked -- automatic sprite data detection without hex viewing.

## 8. Critique notes (collected, not brakes)

- Collecting everything produces floods (Robotron, Excel). Question-driven reports and logging filters keep output readable.
- Domain knowledge did the heavy lifting in Dunki's Choplifter work (game-dev patterns, knowing the gameplay). Tools support that recognition; they do not replace it.
- Breadth: answer one real question end-to-end before building the next tool, so tools get graded by use.
- Provenance through lookup tables mixes sprite data with table addresses; reports must separate them, probably by frequency.
- Some glossary mappings are loose; keep the "related" column honest.
- Renaming existing classes touches the tests; glossary first, code renames later (or never, where our term earns its keep).

## 9. Open questions

- Where does this content land: `GOALS.md` (strategy), `README.md` (vision, glossary), `TODO.md` (startable items), or a document of its own?
- Do run reports live next to `a2-lode-runner`'s HTML research browser, or in their own site?
- Levels: the game loads them through its own disk routine. Option: a checkpoint at that routine's entry fills memory from the `.dsk` file in Python and skips the routine -- no floppy emulation needed.
- Three automated tests in `make test` load `data/bin/ROBOTRON.BIN` by hard-coded path, so a fresh clone cannot run the suite without Robotron. Replace with Lode Runner, make them skip when the file is missing, or keep?

## 10. Candidate next steps (unordered)

- Boot Lode Runner in `papple2` (`LODE RUNNER` is a `B` file at `$0800`, 33024 bytes; `load_image` should handle it).
- Interactive monitor mode.
- Provenance prototype for the question in section 7.
- Glossary into the documentation; polish existing tools by proximity to established ones.
- Robotron de-emphasis in `README.md` and the `Makefile` (`make run`), plus the test decision above.
- Type hints sweep (postponed, still wanted).
