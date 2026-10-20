# papple2 -- Direction

(Note: "I" in the following paragraphs refer to the user, "you" to the AI model.)

**What this is.** Where my reverse engineering work is headed, and the material I collect on the way. I write it as the book author. It may grow, and it is not part of the per-session dump.

**The Book.** I want to turn `papple2`, `a2-hires-lab` and `a2-lode-runner` into a series: posts, a blog or videos. The form is open. It is about Apple II games, how they work under the hood, and how to find that out.

**Why.** I love learning and I love teaching. I want to pass on my appreciation of the games, of the platform, and of reverse engineering itself. The dominator algorithms gave me goosebumps, and a reader should get the chance to feel that too.

**For whom.** The reverse engineering and retro crowds, first of all 6502.org, where my Robotron thread of 2019 lives. I want the connection to these people.

**Why I do the work myself.** A model can produce a disassembly in an afternoon. That is not what this is about.

- **Remember.** I was in high school, in the computer room. Nobody can go down that lane for me.
- **Appreciate.** Doug, the Ngo brothers, Jordan and countless others made the impossible possible. Putting in the time, with my own tools, is how I pay homage, as XekriRedmane and Quinn Dunki did.
- **Tinker.** Knowing how a game works lets me change it: sprites, texts, keys, levels, lives.
- **Create.** Knowing how Lode Runner's sprites work lets me build a game of my own.

**What follows for the projects.**

- I make the finds. Tools and models help me see; they do not hand me answers.
- What I cannot explain, I have not understood. So I ask for pictures and small examples.
- A story is recorded when it happens: how I found out, not only what the code does.

---

## Lessons from Robotron (2019)

The Robotron work is documented in the 6502.org thread "reverse engineering Robotron 2084 for the Apple II" (https://6502.org/forum/viewtopic.php?t=5517, 98 posts, February 2019 to June 2020). The flame flickered and then went out: lack of expertise, all-consuming work projects, lack of collaboration. We are in a different place today.

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
- No way to deal with self-modifying code. Lode Runner has some, which we will use to test our tools.
- Cause and effect separated: 6502 status flags are not updated by all instructions, so a branch taken or not taken is often the consequence of an operation several steps earlier.
- Steep learning curve for SourceGen and other tools; not-invented-here syndrome.
- Visual clutter: automated call graphs produced unwieldy webs of nodes and arrows, readable only after aggressive pruning and cycle-timed vertical realignment. No clear idea how to keep the lessons learned about pruning. Graphviz: impressive eye candy, but useless for understanding.
- Stretches: a single tile can belong to several logical stretches, depending on the game's runtime state. Fusing tiles onto an execution path only worked in easy cases; different states route through the same tiles in a different order.
- The data bottleneck: fine-grained load/store tracking in Python produced datasets too slow to process and too large to comprehend. It might be necessary to say goodbye to an IDE approach and work with professional tools on `papple2`-generated dumps.
- No native time-travel debugging: no register and status flag logging (performance). Scrolling backwards did not work; only incomplete ideas about synchronising memory changes with the program counter.

**Lessons from the Robotron workbench's heat map and time machine** (nice to look at, disappointing for learning; raw counts differed by orders of magnitude, and the display showed frequency, not evidence):
- Binary marks instead of counts: a Code/Data Logger only records *whether* a byte was executed or read.
- Log scale or rank coloring when counts are shown at all.
- Differential runs (coverage diffing): record a run with and without an action (e.g. digging a hole), show only the difference -- evidence is change relative to a baseline.
- Scrubbing for the time machine: drag a cursor along a timeline; jump from a line of code to each moment it ran, or from a value to the moment it was written (as in omniscient debuggers).

## Landscape (prior art)

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

## Glossary (first pass)

"Close" = same concept. "Related" = overlapping, forcing the standard name would mislead.

The `papple2` terms name the old instrumentation, removed 2026-09-27 (at the tag `pre-redesign`); they stay here as vocabulary for the redesign.

| `papple2` term                     | Established term | Match |
|------------------------------------|---|---|
| tile                               | basic block | close |
| stretch                            | container of tiles with entry and exits; region / abstract node (structural analysis); trace; extended basic block / superblock; function chunk (IDA); translation block chaining (QEMU) | related -- see section 1 and section 5, Interpret |
| call tree                          | call graph; control-flow graph at block level | close |
| collect tiles while executing      | dynamic CFG recovery; code coverage | close |
| heatmap of loads/saves/executions  | Code/Data Logger; memory access heatmap | close |
| time machine                       | reverse debugging; time-travel debugging; record/replay | close |
| record everything, step through it | omniscient debugging | close |
| `MemAccessCollector` (deprecated)  | memory access trace | close |
| mem of interest                    | logging filter; trace condition; watch range | close |
| hooks                              | instrumentation; taps (MAME); probes | close |
| where did this byte come from      | data provenance; dynamic taint tracking; backward slicing | close |
| JMP instead of JSR + RTS           | tail call | close |
| lo/hi tables                       | split address tables; "RTS trick" for jump tables | close |
| snippet held lightly               | stub; provisional label | related |
| _(none yet)_                       | chunk (noweb / literate programming): a named piece of code or text that tangling assembles into the source | -- `papple2` has no concept that links findings to chunks yet |

## Stories

One line each for now.

- The unnecessary double indirection in Doug's sprite placement code (it is in `a2-hires-lab`).
- Bandits, in my high school times.
- The ill-fated Robotron project.

## Technical direction (moves to `README.md`)

### Direction in one paragraph

`papple2` becomes a system to disassemble and understand Apple II and II+ games (48k, hi-res, no aux or language card memory) by *running* them. It is not general disassembly software but a kit of fairly generic parts, put together per game. Its place in the landscape is the corner that is still mostly empty: dynamic analysis whose results accumulate into documentation, instead of evaporating when the debugger session ends. The central problem is **knowledge accumulation**, and the form it takes is **storytelling**: the path from first suspicion to understood routine should be recorded as it happens, the way Quinn Dunki's Choplifter article reads -- a sequence of experiments, each answering one question. `papple2` complements static and agent-driven approaches rather than competing with them.

**Dynamic first, static fills the holes** (2026-10-01). `papple2` analyses what actually ran. Andy McFadden argued for static analysis: without seeing what is left out, the paths not taken, it is hard to build a mental model of what code does. The answer here is a hybrid: dynamic analysis finds the structure (tiles, transitions, loops, calls), and static disassembly fills the holes inside that structure, marked "not run", because a hole may be data rather than code. The bet: the 6502 and the Apple II lend themselves to dynamic analysis, and Lode Runner's attract mode exercises nearly everything the game does (sprites, guard AI, player movement) within about 4 million instructions. Every dynamic result is a hypothesis that later parts of the game may revise; the "not run" marks show where coverage is thin. If static analysis ever gave us everything the dynamic one does, we would switch -- which is also why SourceGen is not the path for now.

### Worked example and targets

- **Lode Runner** is the worked example. Xekri's `main.nw` tangles to `dasm` source that assembles byte-identically to the original, so it gives us both a runnable binary and an answer key (every routine, label, and data region named). Every tool can be graded against it.
- **Oracle principle:** develop the workbench *as if* we were disassembling Lode Runner, with Xekri's code as the oracle to develop and debug our own toolchain. Which structures can our tools determine that we already know about from `a2-lode-runner`? The measure of success: an analysis run plus a few hours of manual tinkering with the binary yields a very good first draft of `main.nw`. In a way, this reverse engineers Xekri's documentation process. The oracle only grades; it never feeds the tools. Labels and the listing from `main.nw` are for checking results and for debugging, not inputs to any analysis. `papple2` is one point in a triangle with `a2-lode-runner` and, pulling weight in the short term, `a2-hires-lab`.
- **Later targets:** games without an answer key, e.g. Choplifter, which fits the 48k II/II+ focus.
- **Robotron** stays a test case (`make boot-robotron`) and one of the three games in `README.md`. `probotron` is hibernated and stays private.
