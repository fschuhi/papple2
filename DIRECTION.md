# papple2 -- Direction (working draft)

(Note: "I" in the following paragraphs refer to the user, "you" to the AI model.)

**Status:** working draft from the collection-mode session of 2026-09-23. Extended 2026-09-25 (oracle principle, lessons from Robotron). Nothing here is decided unless it sits under "Decided". Where this content finally lands (`GOALS.md`, `README.md`, `TODO.md`, or this document for good) is an open question at the end.

---

## 1. Direction in one paragraph

`papple2` becomes a system to disassemble and understand Apple II and II+ games (48k, hi-res, no aux or language card memory) by *running* them. It is not general disassembly software but a kit of fairly generic parts, put together per game. Its place in the landscape is the corner that is still mostly empty: dynamic analysis whose results accumulate into documentation, instead of evaporating when the debugger session ends. The central problem is **knowledge accumulation**, and the form it takes is **storytelling**: the path from first suspicion to understood routine should be recorded as it happens, the way Quinn Dunki's Choplifter article reads -- a sequence of experiments, each answering one question. `papple2` complements static and agent-driven approaches rather than competing with them.

## 2. Worked example and targets

- **Lode Runner** is the worked example. Xekri's `main.nw` tangles to `dasm` source that assembles byte-identically to the original, so it gives us both a runnable binary and an answer key (every routine, label, and data region named). Every tool can be graded against it.
- **Oracle principle:** develop the workbench *as if* we were disassembling Lode Runner, with Xekri's code as the oracle to develop and debug our own toolchain. Which structures can our tools determine that we already know about from `a2-lode-runner`? The measure of success: an analysis run plus a few hours of manual tinkering with the binary yields a very good first draft of `main.nw`. In a way, this reverse engineers Xekri's documentation process. `papple2` is one point in a triangle with `a2-lode-runner` and, pulling weight in the short term, `a2-hires-lab`.
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

|  | **Static: reads the bytes** | **Dynamic: runs the game** |
|---|---|---|
| **Knowledge accumulates** | SourceGen (project file); Xekri's agent (`main.nw`, byte-perfect) | _mostly empty -- `papple2`'s target_ |
| **Knowledge is thrown away** | monitor listing (read once, not kept) | AppleWin, microM8, MAME, Virtual II (break, step, inspect) |

- **Static, accumulating:** SourceGen (Windows, WPF; Wine reported to work), Ghidra, IDA, `da65`; Xekri's `reveng.md` process, an autonomous LLM agent that produces a byte-perfect `main.nw` from a disk image and deliberately uses no emulator.
- **Dynamic, thrown away:** AppleWin debugger, Virtual II (macOS; Quinn Dunki's main tool for Choplifter), MAME debugger.
  - **microM8** is the most advanced Apple II example found so far: a web-based debugger (browser as interface, buttons send actions to the emulator), a variety of breakpoints, stepping, memory editing, recording with rewind and playback, and a memory access heat map. Xekri's `main.nw` screenshots come from microM8. Its limits for us: no visible way to store findings (chunks, basic blocks, labels) -- the session's knowledge stays in the user's head. Not intuitive to use, no visible ongoing development.
- **Dynamic, accumulating -- the closest existing paradigms, mostly from other scenes:**
  - NES: FCEUX's Code/Data Logger (marks every byte as executed, read as data, or both, while the game runs); Mesen (trace logger, event viewer, memory access highlighting, sprite viewers, Lua scripting).
  - C64: C64 Debugger (live memory map colored by reads and writes).
  - General: omniscient debugging (record once, query any moment later; e.g. Pernosco on top of `rr`); shadow memory (Valgrind); dynamic taint tracking and data provenance (security research).
- _Needs investigation:_ microM8's heat map comes close to a Code/Data Logger. Is there an Apple II tool that saves per-byte code/data marks to a file for a disassembler to use, or that tracks provenance? Not known to us yet.
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

**Record and tell**
- Storytelling: record the path of discovery (question, experiment, result) as it happens, not only the final result. Two layers: the lab journal (how we found out, like Dunki's article) and `main.nw` (what the code does, like Xekri's document).
- Findings attach to lasting artefacts: noweb chunks, basic blocks, labels, runs.
- Snippets held lightly, so knowledge coagulates around them (stubs, provisional labels, hypotheses).
- Generate noweb Markdown for tangling and weaving.

**Interact**
- Interactive monitor mode (like AppleWin's debugger): break, inspect named zero page entries, ask which tile or stretch we are in, where a pixel came from; run Python at a breakpoint.
- Complex programmable breakpoints.
- Experiments while running, in Dunki's style: stub a routine with `RTS`, change memory, redirect a pointer, break and step out to find the main loop.
- Save and load complex state; time machine (reverse debugging).

**Report**
- Static HTML reports per named run, side by side, collapsible.

**Lessons from the Robotron workbench's heat map and time machine** (nice to look at, disappointing for learning; raw counts differed by orders of magnitude, and the display showed frequency, not evidence):
- Binary marks instead of counts: a Code/Data Logger only records *whether* a byte was executed or read.
- Log scale or rank coloring when counts are shown at all.
- Differential runs (coverage diffing): record a run with and without an action (e.g. digging a hole), show only the difference -- evidence is change relative to a baseline.
- Scrubbing for the time machine: drag a cursor along a timeline; jump from a line of code to each moment it ran, or from a value to the moment it was written (as in omniscient debuggers).

## 6. Glossary (first pass)

"Close" = same concept. "Related" = overlapping, forcing the standard name would mislead.

| `papple2` term | Established term | Match |
|---|---|---|
| tile | basic block | close |
| stretch | trace; extended basic block / superblock; function chunk (IDA); translation block chaining (QEMU) | under review -- a container for tiles; may not survive, see section 9 |
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
| _(none yet)_ | chunk (noweb / literate programming): a named piece of code or text that tangling assembles into the source | -- `papple2` has no concept that links findings to chunks yet |

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

- **Stretches:** should the concept survive? Research what other software uses as a container for basic blocks (candidates: traces, superblocks, IDA's function chunks, QEMU's translation block chaining, plain functions / call graph nodes).
- **Monitor form:** a web monitor in microM8's style (local web server, HTML pages, buttons), or Jupyter notebooks (cells to run, break, inspect; Markdown cells as lab journal; rich HTML output inline)? Or both: notebook as the working place, exported HTML as reports. Concerns: hidden state when cells run out of order (the Mathematica experience), JSON files in git (`jupytext`), a running emulator blocks its cell. marimo, a reactive notebook stored as plain `.py`, answers the first two -- but it tracks which cell defines a variable, not which cell changes an object like the emulator. Primer planned, see `TODO.md`.

- Where does this content land: `GOALS.md` (strategy), `README.md` (vision, glossary), `TODO.md` (startable items), or a document of its own?
- Do run reports live next to `a2-lode-runner`'s HTML research browser, or in their own site?
- Levels: the game loads them through its own disk routine. Option: a checkpoint at that routine's entry fills memory from the `.dsk` file in Python and skips the routine -- no floppy emulation needed.
- Three automated tests in `make test` load `data/bin/ROBOTRON.BIN` by hard-coded path, so a fresh clone cannot run the suite without Robotron. Replace with Lode Runner, make them skip when the file is missing, or keep?

## 10. Candidate next steps (unordered)

- ~~Boot Lode Runner in `papple2`~~ -- done 2026-09-23, headless, demo mode on level 1; needed the stack wrap and decimal mode fixes in `cpu.py`. Real play (levels from disk) still open.
- Interactive monitor mode.
- Provenance prototype for the question in section 7.
- Glossary into the documentation. Then compare each existing tool with its closest established counterpart and borrow what has proven itself (features, names, file formats) -- e.g. does `MemAccessCollector` have filter conditions like a trace logger?
- Robotron de-emphasis in `README.md` and the `Makefile` (`make run`), plus the test decision above.
- Type hints sweep: postponed, but gained weight now that `make patch` makes many-file changes cheap.

## 11. Lessons from Robotron (2019)

The Robotron work is documented in the 6502.org thread "reverse engineering Robotron 2084 for the Apple II" (https://6502.org/forum/viewtopic.php?t=5517, 98 posts, February 2019 to June 2020). The flame flickered and then went out: lack of expertise, all-consuming work projects, lack of collaboration. We are in a different place today. The lessons from the heat map and the time machine are in section 5, the open question about stretches in section 9.

**What worked** (what I deemed presentable in the thread):
- Dynamic execution tracking.
- Tiles and stretches for automatic grouping.
- Subtractive analysis, BigEd's "opposite of instrumentation, removing code": poke an `RTS` into a stretch, rerun, see what disappears.
- Saving and loading snapshots.
- Cycle-indexed memory heatmaps -- a functional equivalent to time-travel debugging?
- Chronological call trees: nodes ordered by the cycle of their first execution (White Flame: "a readable flowchart").

**What hurt:**
- I couldn't see the forest for the trees.
- Handling different binaries was necessary, but it was easy to lose oversight.
- Intent vs. mechanics: what an instruction did mechanically was straightforward; deducing why a specific comparison was made or a literal value was used was a massive conceptual leap.
- Incomplete understanding of 6502 idioms. Chromatix's four subroutine classes (sorted by what a routine does to the stack between entry and `RTS`) need to be implemented; they have surfaced several times now. I lacked Leventhal-level knowledge to recognise standard routines like multiplication (see Chromatix's analysis of `closed03`).
- No way to deal with self-modifying code. Lode Runner has some, which we will use to test our tools; Bandits reportedly has lots.
- Cause and effect separated: 6502 status flags are not updated by all instructions, so a branch taken or not taken is often the consequence of an operation several steps earlier.
- Steep learning curve for SourceGen and other tools; not-invented-here syndrome.
- Visual clutter: automated call graphs produced unwieldy webs of nodes and arrows, readable only after aggressive pruning and cycle-timed vertical realignment. No clear idea how to keep the lessons learned about pruning. Graphviz: impressive eye candy, but useless for understanding.
- Stretches: a single tile can belong to several logical stretches, depending on the game's runtime state. Fusing tiles onto an execution path only worked in easy cases; different states route through the same tiles in a different order.
- The data bottleneck: fine-grained load/store tracking in Python produced datasets too slow to process and too large to comprehend. It might be necessary to say goodbye to an IDE approach and work with professional tools on `papple2`-generated dumps.
- No native time-travel debugging: no register and status flag logging (performance). Scrolling backwards did not work; only incomplete ideas about synchronising memory changes with the program counter.

**Ideas this led to** (2026-09-25, collected, not yet discussed):
- Structural analysis and execution history go together in my head. Maybe that is the wrong approach, maybe not ("decoupled control flow graphs"). You suggested: the control-flow graph is one static map of the program, each execution path one walk across it; keep both, linked.
- A folding editor instead of graphs: linear, text-block based, very fast keyboard navigation. My brain needs to become a supercharged 6502 execution system, in a many-worlds setting.
- Relational trace logging: we need a database. Browsing experiments comes first, cross-experiment correlation later. Existing dynamic analysis tools may show how.
- Stack-based subroutine identification as a quick win, building on what we have: pair each `RTS` with the `JSR` whose return address it pops; mismatches are candidates for Chromatix's classes 3 and 4. Open: tail calls, jump tables.
- Data flow and taint analysis over one or more execution paths, presented in an Apple II specific memory overview. Brushing as the visualisation paradigm (selecting something in one view highlights it in all others).
- Workbench paradigm: mark something in the noweb document (Notepad++, autosave), press a key picked up by Karabiner-Elements; the workbench determines the context by comparing the current file with the passed snippet and offers what to do. It can also generate snippets to paste into the document. Documentation and experimentation are only loosely coupled at first.
- Overviews like the "genome sequence" of Lorenz Wiest's Star Raiders disassembly (https://github.com/lwiest/StarRaiders).
- Reverse engineering as an artistic endeavour: mastery and beauty.
