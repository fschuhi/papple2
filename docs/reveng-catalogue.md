# Reverse Engineering on 6502 Platforms -- Techniques and Tools

**Status:** Draft 0.1 (2026-09-24). Seeded from a research dialog with Gemini, restructured and partly corrected. Claims not yet checked against primary sources are marked ⚠ and collected in section 8.

**Purpose:** A catalogue of reverse engineering ("reveng") techniques used on MOS 6502-family machines (Apple II, Commodore 64, NES), the names each major tool gives them, and what that means for the `papple2` pipeline. The catalogue is organised by *technique*, not by tool: the question it answers is "what can be done, and who does it well", so that `papple2` can pick deliberately what to build, what to borrow, and what to skip.

**Scope:** 8-bit 6502 / 65C02 / 6510 / 2A03 software, with the Apple II / II+ 48k as the primary target. General-purpose reveng tools (x86/ARM world) are included only where the *concept* transfers, even if the tool itself does not run 6502 code.

---

## 1. How to read an entry

Each technique in section 3 uses the same fields:

- **Also called** -- other names for the same thing, across tools and literature.
- **Question it answers** -- in one sentence, what you learn from it.
- **How it works** -- the mechanism.
- **6502 specifics** -- where the 8-bit world differs from modern binaries.
- **Tools** -- who implements it, and under which name.
- **papple2** -- status in `papple2`: *exists*, *wished* (on the wish list from our sessions), or *open* (not discussed yet). These statuses come from our past conversations, not from reading the current code.

Two words used throughout:

- **Static** analysis looks at the bytes without running them.
- **Dynamic** analysis runs the program (in an emulator) and watches what happens.

---

## 2. Overview

| # | Family | Technique | Static / Dynamic | papple2 |
|---|---|---|---|---|
| 3.1 | Getting the program | Disk image extraction | static | open |
| 3.2 | Getting the program | Memory dump after load / unpack | dynamic | exists (implicitly, via emulator state) |
| 3.3 | Setting the stage | Memory map and banking model | static | open |
| 3.4 | Setting the stage | Platform symbol tables | static | wished (partly) |
| 3.5 | Code vs. data | Flow-tracing disassembly | static | exists (disassembler) |
| 3.6 | Code vs. data | Code/data logging | dynamic | exists (execution map, memory access log) |
| 3.7 | Annotating | Data typing (bytes, words, text, address tables) | static | wished (lo/hi tables) |
| 3.8 | Annotating | Labels, comments, cross-references | static | open |
| 3.9 | Control flow | Basic blocks and control-flow graph | both | exists (tiles, stretches) |
| 3.10 | Control flow | Loop detection | both | wished |
| 3.11 | Stopping the machine | Execution breakpoints | dynamic | exists |
| 3.12 | Stopping the machine | Watchpoints (memory access breakpoints) | dynamic | exists? (via hooks) |
| 3.13 | Stopping the machine | Video-position breakpoints | dynamic | open |
| 3.14 | Watching the machine | Trace logging | dynamic | exists (memory access log) |
| 3.15 | Watching the machine | Instrumentation and hooks | dynamic | exists / wished (richer) |
| 3.16 | Watching the machine | Time travel (rewind, snapshots) | dynamic | exists (time machine) |
| 3.17 | Finding variables | RAM search | dynamic | open |
| 3.18 | Finding variables | Relational search and co-change profiling | dynamic | open |
| 3.19 | Comparing | Snapshot diffing | dynamic | open |
| 3.20 | Comparing | Binary diffing | static | open |
| 3.21 | Following data | Data-flow analysis and taint tracking | both | open |
| 3.22 | Following data | Program slicing | both | open |
| 3.23 | Understanding meaning | Structure recovery | both | open |
| 3.24 | Understanding meaning | Idiom recognition, lifting, decompilation | static | open |
| 3.25 | Understanding meaning | Symbolic execution | static | open |
| 3.26 | Assets | Graphics, compression, sound | both | open (graphics partly in `a2-hires-lab`) |
| 3.27 | Output | Reassemblable source | static | wished (noweb) |

---

## 3. Techniques

### 3.1 Disk image extraction

- **Also called:** file extraction, image mounting.
- **Question it answers:** Which files are on the disk, and at which address does each one load?
- **How it works:** A disk utility reads the filesystem (DOS 3.3, ProDOS, Commodore DOS) and exports the files as raw binaries, together with their load address and length.
- **6502 specifics:** Many commercial games do not use a filesystem at all. They boot their own loader and read sectors directly ("booter" disks), often with copy protection. For those, extraction fails and 3.2 is the way in.
- **Tools:** CiderPress II and AppleCommander (Apple II); DirMaster (C64, Windows).
- **papple2:** open. For Lode Runner, Xekri's work already covers this.

### 3.2 Memory dump after load or unpack

- **Also called:** RAM dump, snapshot extraction, "let the game unpack itself".
- **Question it answers:** What does the program look like in memory once it has loaded, decrypted, or decompressed itself?
- **How it works:** Boot the game in an emulator, stop it at a point after loading (often at the jump into the main program), and write memory to a file.
- **6502 specifics:** On the C64, most commercial and demo-scene releases are compressed ("crunched") and unpack themselves with self-modifying code; the standard move is a breakpoint on the final jump, then the dump. On the Apple II, the typical range is `$0800`--`$BFFF` for a 48k game.
- **Tools:** any debugging emulator (AppleWin, MAME, VICE, C64Debugger, Mesen).
- **papple2:** exists in substance, since the whole emulator state is accessible from Python.

### 3.3 Memory map and banking model

- **Also called:** address regions, memory blocks, overlays (Ghidra), bank selectors.
- **Question it answers:** Which address range holds RAM, ROM, I/O, and which contents are visible at a given moment?
- **How it works:** The analyst tells the tool where each loaded chunk lives in the 64 KB address space. Where the same addresses can show different contents (banking), each variant becomes its own block; Ghidra calls this an *overlay*.
- **6502 specifics:** Raw 8-bit binaries carry no header saying where they belong. Banking differs per platform: NES cartridge mappers (MMC1, MMC3, ...), the C64 processor port at `$0001` switching BASIC/KERNAL/I/O, the Apple II language card and auxiliary memory. A 48k Apple II game avoids all of this, which is one reason these games are good first targets.
- **Tools:** Ghidra (Memory Map window, overlays); SourceGen (address regions); da65 (config file).
- **papple2:** open. For 48k Apple II games the fixed map is: zero page `$0000`--`$00FF`, stack `$0100`--`$01FF`, RAM up to `$BFFF`, soft switches and slot I/O `$C000`--`$CFFF`, ROM `$D000`--`$FFFF`.

### 3.4 Platform symbol tables

- **Also called:** project symbols, platform symbols, hardware labels.
- **Question it answers:** What is that address? (`$C030` is the speaker, `$FDED` is the ROM routine COUT that prints a character.)
- **How it works:** A predefined list of names for hardware registers and ROM routines is applied to the listing, so `LDA $C000` reads as `LDA KBD`.
- **6502 specifics:** Apple II soft switches (`$C000` keyboard, `$C010` keyboard strobe, `$C030` speaker, `$C050`--`$C057` graphics mode switches); Monitor ROM routines (`$FDED` COUT, `$FD1B` KEYIN, `$F800` PLOT).
- **Tools:** SourceGen ships symbol files for Apple II, DOS 3.3, ProDOS, C64; Ghidra via scripts; VICE and C64Debugger via label files.
- **papple2:** wished, as part of "infer table semantics from known Apple II memory layout (e.g. HGR row addresses)".

### 3.5 Flow-tracing disassembly

- **Also called:** recursive descent disassembly, auto-analysis, code/data classification (SourceGen).
- **Question it answers:** Which bytes are instructions, judged by following the program's jumps from its entry points?
- **How it works:** Start at known entry points (reset and interrupt vectors, load address), decode instructions, and follow every `JSR`, `JMP` and branch. Everything reached is code; the rest is presumed data.
- **6502 specifics:** Fails at indirect jumps (`JMP ($xxxx)`), jump tables built with the `RTS` trick (pushing an address minus one and returning into it), and self-modifying code. These gaps are why static tracing needs help from 3.6.
- **Tools:** Ghidra, SourceGen, Regenerator, JC64dis, da65 (driven by a config rather than tracing).
- **papple2:** a disassembler exists; whether it traces flow is to be checked.

### 3.6 Code/data logging

- **Also called:** CDL (Mesen, FCEUX), execution heatmap, coverage map.
- **Question it answers:** Which bytes did the CPU actually execute, and which did it only read as data?
- **How it works:** While the game runs, every byte is marked by how it was accessed: fetched as an instruction, read as data, written. After play, the marks classify memory far more reliably than static tracing -- but only for the paths that were actually exercised.
- **6502 specifics:** On the NES the log also records what the graphics chip read (tiles), which separates graphics from other data. The log can be fed into a static disassembler as a starting point.
- **Tools:** Mesen (CDL), FCEUX (CDL export), C64Debugger (live memory map).
- **papple2:** exists: the memory access log and the map of executed instructions.

### 3.7 Data typing

- **Also called:** format operand (SourceGen), data definition (Ghidra), block type assignment.
- **Question it answers:** What kind of data is this: single bytes, 16-bit words, text, or a table of addresses?
- **How it works:** The analyst (or a heuristic) marks byte ranges with a type; the tool then displays and exports them accordingly.
- **6502 specifics:** Text on the Apple II is often "high ASCII" (bit 7 set); on the C64 it is PETSCII or screen codes. Address tables are frequently split into two tables, one with the low bytes and one with the high bytes ("lo/hi tables"), because the 6502 can index those with a single register. Recognising a lo/hi pair and its length is a core 6502 skill.
- **Tools:** all static disassemblers; SourceGen additionally renders Apple II hi-res bitmaps and C64 sprites inline.
- **papple2:** wished: "lo/hi lookup table detection, automated reasoning about table size".

### 3.8 Labels, comments, cross-references

- **Also called:** symbols, user labels; XREFs; line, side, plate comments.
- **Question it answers:** Where is this address used, and what have we learned about it so far?
- **How it works:** Names and notes are attached to addresses; the tool lists every instruction that refers to a given address (the cross-reference list).
- **Tools:** all static disassemblers; VICE and C64Debugger can load label files for the monitor.
- **papple2:** open. Related wish: "collect snippets and hold them lightly, so knowledge coagulates slowly around them".

### 3.9 Basic blocks and control-flow graph

- **Also called:** CFG, function graph; in `papple2`: *tiles* and *stretches*.
- **Question it answers:** How do the pieces of code connect -- which block can follow which?
- **How it works:** A *basic block* is a run of instructions with one entry and one exit. The graph connects blocks by jumps and branches (predecessors and successors). Built statically from 3.5, or dynamically from the observed execution.
- **Tools:** Ghidra (function graph), IDA-style tools generally; dynamically: `papple2`.
- **papple2:** exists (tiles, stretches, call trees from the Robotron work).

### 3.10 Loop detection

- **Also called:** loop nesting analysis, hierarchical loop recovery.
- **Question it answers:** Where are the loops, and how are they nested (main loop > per-frame loop > per-sprite loop)?
- **How it works:** In the control-flow graph, a jump back to an earlier block that dominates it marks a loop; nesting follows from which loops contain which.
- **Tools:** Ghidra's decompiler does this internally (it shows loops as `while` / `do`).
- **papple2:** wished: "semi-automated hierarchical loop detection".

### 3.11 Execution breakpoints

- **Also called:** breakpoint, exec break.
- **Question it answers:** What is the state of the machine when the CPU reaches this address?
- **How it works:** The emulator stops when the program counter hits the address; optionally only if a condition is true (conditional breakpoint).
- **Tools:** every debugging emulator; VICE monitor `break`; AppleWin debugger; MAME debugger.
- **papple2:** exists (checkpoints dispatch a `breakpoint` event into the state machine). Wished: "complex programmable breakpoints" and an interactive monitor mode that stops and lets you run Python.

### 3.12 Watchpoints

- **Also called:** memory access breakpoint, read/write breakpoint; VICE `watch load` / `watch store`.
- **Question it answers:** Who reads or writes this address?
- **How it works:** The emulator stops whenever any instruction accesses the watched address, regardless of where the instruction is.
- **6502 specifics:** Especially useful on hardware addresses: writes to `$C030` (speaker), reads of `$C000` (keyboard), or writes into the hi-res screen buffer to find out who drew a pixel.
- **Tools:** Mesen, FCEUX, VICE, C64Debugger, AppleWin, MAME.
- **papple2:** probably covered by hooks on memory access -- to be confirmed.

### 3.13 Video-position breakpoints

- **Also called:** raster breakpoint (C64), scanline/cycle breakpoint (Mesen).
- **Question it answers:** What is the CPU doing while the video beam is at this line?
- **How it works:** The emulator stops when the video circuitry reaches a given screen line or cycle.
- **6502 specifics:** Essential on the C64 and NES, where programs change the display mid-frame. Much less relevant on the Apple II, whose programs rarely synchronise with the beam (a few do, via the "vapor lock" trick).
- **Tools:** C64Debugger, VICE ⚠, Mesen.
- **papple2:** open; low priority for 48k Apple II games.

### 3.14 Trace logging

- **Also called:** trace logger (Mesen), instruction trace, execution history.
- **Question it answers:** What exactly happened, instruction by instruction, leading up to this point?
- **How it works:** Every executed instruction is recorded with the registers and flags; the log can be searched afterwards or analysed with external scripts.
- **Tools:** Mesen, FCEUX, VICE `trace`, C64Debugger, AppleWin.
- **papple2:** exists (memory access log); wished: "complex tracers, watchers, listeners, observers, loggers via hooks".

### 3.15 Instrumentation and hooks

- **Also called:** dynamic binary instrumentation (DBI), scripting API, memory/event callbacks.
- **Question it answers:** Can I attach my own code to events in the running program, without changing the program?
- **How it works:** The emulator calls user code on events (instruction at address X, write to address Y, start of frame). The user code can log, count, change values, or stop the machine. *Shadow memory* is a variant: a parallel buffer holding facts about each byte, e.g. which instruction last wrote it.
- **Tools:** Mesen (Lua scripting), FCEUX (Lua), VICE (remote monitor over a network socket, usable from Python), MAME (Lua); outside the 6502 world: Frida, DynamoRIO.
- **papple2:** exists (hooks). This is where Python-in-the-emulator is the strongest argument for `papple2`: the hook *is* Python, no bridge.

### 3.16 Time travel

- **Also called:** rewind, step back, reverse debugging, save states.
- **Question it answers:** How did we get here? (Step backwards from the moment something went wrong.)
- **How it works:** The emulator keeps periodic snapshots and replays forward from the nearest one; or it records enough to undo each instruction.
- **Tools:** Mesen (rewind, step back), C64Debugger (snapshots, step back), most emulators (save states).
- **papple2:** exists (time machine, rewinding CPU and memory). Wished: save and load complex state.

### 3.17 RAM search

- **Also called:** RAM search / RAM watch (FCEUX), cheat search, value scanning (Cheat Engine).
- **Question it answers:** Where does the game keep the number of lives, the player's position, the level number?
- **How it works:** Take a snapshot, change something in the game (lose a life), then filter all addresses by how they changed (decreased by one). Repeat until few candidates remain.
- **Tools:** FCEUX, Mesen, Cheat Engine (attached to an emulator process).
- **papple2:** open. Cheap to build on top of the time machine.

### 3.18 Relational search and co-change profiling

- **Also called:** correlated / comparative search; access profiling.
- **Question it answers:** Which addresses belong together -- e.g. a 16-bit position split into a low and a high byte, or the X and Y of the same object?
- **How it works:** *Relational search* filters addresses by relations to other addresses (A equals B plus an offset). *Co-change profiling* samples memory over many frames and groups the addresses that change at the same moments.
- **6502 specifics:** Because of the lo/hi split (3.7), related bytes are often *not* adjacent: object X positions may sit in `$0200`--`$020F` and the matching high bytes in `$0210`--`$021F`.
- **Tools:** FCEUX and Mesen (comparative search) ⚠; the co-change part is mostly done with custom scripts over trace logs.
- **papple2:** open.

### 3.19 Snapshot diffing

- **Also called:** state comparison, memory diff.
- **Question it answers:** What changed in memory between "just before" and "just after" an event?
- **How it works:** Two snapshots are compared byte by byte; the differences are the candidates for the variables involved.
- **Tools:** emulator snapshot tools ⚠; easily scripted.
- **papple2:** open; natural extension of the time machine.

### 3.20 Binary diffing

- **Also called:** BinDiff, function matching, graph matching.
- **Question it answers:** What differs between two versions of a program (revisions, regional versions, ports)?
- **How it works:** Instead of comparing raw bytes (useless once code shifts by one byte), the tool matches functions and basic blocks by their graph structure.
- **Tools:** BinDiff (with Ghidra via the BinExport plugin), Diaphora ⚠; for raw bytes: VBinDiff.
- **papple2:** open. Possibly relevant for different releases of the same Apple II game.

### 3.21 Data-flow analysis and taint tracking

- **Also called:** DFA; dynamic taint analysis (DTA), taint propagation.
- **Question it answers:** Where does this value come from, and where does it go?
- **How it works:** *Data-flow analysis* follows values through registers and memory. *Taint tracking* marks an input (e.g. the keyboard byte from `$C000`) and propagates the mark to everything computed from it: `LDA $20 / CLC / ADC $21 / STA $22` makes `$22` depend on `$20` and `$21`.
- **Tools:** Ghidra (static, internally); Triton, PANDA, angr (dynamic) -- ⚠ none of these supports the 6502 out of the box as far as I know; for 6502 this is custom work over an emulator.
- **papple2:** open. With shadow memory (3.15) this is a realistic `papple2` feature.

### 3.22 Program slicing

- **Also called:** backward slice, forward slice.
- **Question it answers:** Backward: which instructions contributed to this value? Forward: which later instructions are affected by it?
- **How it works:** Starting from one value at one point (the *slicing criterion*), keep only the instructions connected to it through data flow and control flow; everything else is removed from view.
- **6502 specifics:** Example: "who computed the byte just written to the hi-res screen at this pixel?" -- exactly the "trace back where a pixel came from" wish.
- **Tools:** Ghidra decompiler (highlight forward/backward slice); dynamically: scripts over trace logs.
- **papple2:** open, but closely matches a stated wish.

### 3.23 Structure recovery

- **Also called:** structure inference, dynamic structure recovery, data type recovery.
- **Question it answers:** Which bytes form one record (e.g. one enemy: X, Y, direction, state)?
- **How it works:** Observes which offsets are accessed together relative to a base (a pointer, or an index register) and groups them into a record.
- **6502 specifics:** 6502 programs rarely use pointers to records; they use *parallel arrays* indexed by X or Y (all X positions in one table, all directions in another). Recovery therefore means grouping tables that are indexed by the same register in the same loop.
- **Tools:** Ghidra (data type manager, static); Cheat Engine "dissect data/structures"; dynStruct and Howard (x86 research tools, concept only).
- **papple2:** open.

### 3.24 Idiom recognition, lifting, decompilation

- **Also called:** IR lifting, P-code (Ghidra), decompilation.
- **Question it answers:** What does this code *mean* at a higher level (a 16-bit addition, a multiply routine, a loop over objects)?
- **How it works:** Instructions are translated into a simpler, uniform intermediate language (*IR*, intermediate representation), which is then simplified and printed as pseudo-C. *Idiom recognition* spots known patterns, such as two zero-page bytes used together as a 16-bit pointer.
- **6502 specifics:** Hand-written 6502 code has no calling convention and uses flags and registers freely, so decompilers often produce awkward output. Idiom recognition may be more useful than full decompilation.
- **Tools:** Ghidra (built-in 6502 and 65C02 support via its SLEIGH processor descriptions); RetDec, Rellic ⚠ (no 6502 front end known to me).
- **papple2:** open.

### 3.25 Symbolic execution

- **Also called:** constraint solving, SMT-based path exploration.
- **Question it answers:** Which input makes the program reach this branch?
- **How it works:** Values are treated as unknowns; each path accumulates conditions; a solver finds inputs that satisfy them.
- **Tools:** angr, Triton, Miasm -- ⚠ none targets the 6502 out of the box as far as I know.
- **papple2:** open; likely low value for games compared to its cost.

### 3.26 Assets: graphics, compression, sound

- **Also called:** asset extraction, format reverse engineering.
- **Question it answers:** How are pictures, levels, and music stored and decoded?
- **How it works:** Viewers display memory as bitmaps or tiles under various layouts; compression schemes (run-length, LZ variants) are recovered from the loader code; sound is recovered by logging writes to the sound hardware per frame.
- **Tools:** YY-CHR, Tile Studio (tile viewers); SourceGen visualisers; SIDDump (C64 sound, logs writes to `$D400`--`$D41C`); `a2-hires-lab` for Apple II hi-res.
- **papple2:** open. Lode Runner's 104 sprites and level format are a concrete test case.

### 3.27 Reassemblable source

- **Also called:** round-trip disassembly, source generation, "byte-identical rebuild".
- **Question it answers:** Is the disassembly complete and correct? (Proof: it assembles back into exactly the original bytes.)
- **How it works:** The tool writes source for a target assembler; assembling it and comparing with the original verifies the work.
- **Tools:** da65 + ca65 (cc65 toolchain), SourceGen (verifies against several cross-assemblers), Regenerator, JC64dis. Xekri's Lode Runner source rebuilds byte-identically with `dasm`.
- **papple2:** wished: "generate noweb markdown for tangling and weaving".

---

## 4. Terminology matrix

What each tool calls a technique. "--" means the tool does not do it (usually because it is static-only or dynamic-only). Keyboard shortcuts from the Gemini draft are left out until verified.

| Technique | Mesen | Ghidra | SourceGen | Regenerator | VICE monitor | C64Debugger |
|---|---|---|---|---|---|---|
| Code/data logging (3.6) | Code/Data Logger (CDL) | -- | -- | -- | -- | memory map view |
| Flow-tracing disassembly (3.5) | -- | auto-analysis | code/data analyzer | block type assignment | -- | -- |
| Data typing (3.7) | -- | data types | format operand / data | byte, word, text, address table | -- | -- |
| Labels (3.8) | labels | labels / symbols | user labels, project symbols | labels | `al` (add label) | label files ⚠ |
| Cross-references (3.8) | -- ⚠ | XREFs | references | cross-references | -- | -- |
| Banking (3.3) | mapper / bank view | overlays | address regions | -- | CPU port `$0001` | bank state view ⚠ |
| Execution breakpoint (3.11) | breakpoint | breakpoint (Ghidra debugger) | -- | -- | `break` | breakpoint |
| Watchpoint (3.12) | read/write breakpoint | read/write breakpoint | -- | -- | `watch load`/`watch store` | read/write breakpoint |
| Video-position breakpoint (3.13) | scanline/cycle breakpoint | -- | -- | -- | ⚠ | raster breakpoint |
| Trace logging (3.14) | Trace Logger | trace (debugger) | -- | -- | `trace` | trace history |
| Time travel (3.16) | rewind, step back | -- | -- | -- | -- | step back ⚠ |
| RAM search (3.17) | memory search ⚠ | -- | -- | -- | `hunt` ⚠ | -- |
| Scripting / hooks (3.15) | Lua | Java/Python scripts (static) | -- | -- | remote monitor | ⚠ |
| Slicing (3.22) | -- | forward/backward slice | -- | -- | -- | -- |
| Reassemblable source (3.27) | -- | -- (export only) | generate source | save source | -- | -- |

---

## 5. Tools directory

| Tool | Platforms (target) | Kind | Runs on | Notes |
|---|---|---|---|---|
| Mesen 2 | NES (and other consoles) | debugging emulator | Win, Linux, macOS ⚠ | reference-grade NES debugger |
| FCEUX | NES | debugging emulator | Win, Linux | RAM search, Lua, CDL; TAS community |
| VICE (`x64sc`) | C64 | emulator with monitor | Win, Linux, macOS | cycle-exact; remote monitor for scripting |
| C64Debugger | C64 | visual debugger | Win, Linux, macOS | author: Marcin Skoczylas ("slajerek") -- Gemini's attribution was wrong ⚠ |
| AppleWin | Apple II | emulator with debugger | Windows | the monitor-style debugger Frank wants in `papple2` |
| MAME | Apple II and many others | emulator with debugger | Win, Linux, macOS | Lua scripting; macOS-native option for Apple II |
| Ghidra | 6502, 65C02 built in | static analysis suite | Win, Linux, macOS | decompiler, graphs, slicing; NES loader: GhidraNes |
| 6502bench SourceGen | Apple II, C64, NES, IIgs | interactive disassembler | Windows ⚠ | symbol tables, visualisers, verified round trip |
| Regenerator | C64 | interactive disassembler | Windows | assembler-ready output |
| JC64dis | C64 (and others) | interactive disassembler | Java (any) | reads PRG, CRT, VICE snapshots, SID |
| da65 / cc65 | any 6502 | config-driven disassembler + assembler | any | reproducible, scriptable |
| NESicide | NES | IDE incl. debugger | Win, Linux | ⚠ maintenance status |
| CiderPress II | Apple II | disk image utility | Win, Linux, macOS | file extraction |
| AppleCommander | Apple II | disk image utility | Java (any) | file extraction, scriptable |
| DirMaster | C64 | disk image utility | Windows | |
| SIDDump | C64 | sound logger | any | logs SID register writes per frame |
| Cheat Engine | any (via emulator process) | memory scanner | Win, macOS ⚠ | value search, structure dissect |
| angr, Triton, Miasm | x86/ARM etc. | symbolic execution / taint | any | concept only for 6502 ⚠ |
| BinDiff, Diaphora | via Ghidra/IDA | binary differ | any | ⚠ Diaphora is IDA-centred |
| `papple2` | Apple II | Python emulator as debugging instrument | macOS (primary) | hooks, time machine, access log, tiles/stretches |

---

## 6. Glossary

Short definitions, alphabetical. Each term points to its section.

- **Address table** -- a table of 16-bit addresses, e.g. jump targets. (3.7)
- **Basic block** -- a run of instructions with one entry and one exit. (3.9)
- **Breakpoint** -- stop when the CPU reaches an address. (3.11)
- **CDL (code/data log)** -- a per-byte record of how memory was accessed at runtime. (3.6)
- **Control-flow graph (CFG)** -- basic blocks connected by the jumps between them. (3.9)
- **Co-change profiling** -- grouping addresses that change at the same moments. (3.18)
- **Cross-reference (XREF)** -- a list of all places that refer to an address. (3.8)
- **Decompilation** -- turning machine code into readable higher-level pseudo-code. (3.24)
- **High ASCII** -- Apple II text encoding with bit 7 set. (3.7)
- **Lo/hi tables** -- an address table split into a table of low bytes and a table of high bytes. (3.7)
- **Overlay** -- Ghidra's term for alternative contents at the same addresses (banking). (3.3)
- **Program slice** -- the subset of instructions that affect (backward) or are affected by (forward) one value. (3.22)
- **Shadow memory** -- a parallel buffer with metadata about each memory byte. (3.15)
- **Soft switch** -- an Apple II I/O address that changes hardware state when accessed. (3.4)
- **Stretch, tile** -- `papple2`'s terms for units of observed control flow (related to basic blocks). (3.9)
- **Taint tracking** -- marking a value and following everything computed from it. (3.21)
- **Watchpoint** -- stop when any instruction reads or writes an address. (3.12)

---

## 7. References

### Sites

- **Nesdev Wiki** (nesdev.org/wiki) -- the reference for NES hardware: memory map, graphics and sound chips, cartridge mappers.
- **Nesdev Forums** (forums.nesdev.org) -- NES homebrew and reverse engineering community.
- **RetroReversing** (retroreversing.com) -- walkthroughs incl. Ghidra setup for NES.
- **NesCartDB** -- cartridge hardware database. ⚠ URL from the Gemini draft was garbled.
- **Xekri's `reveng.md`** (github.com/XekriRedmane/ultima1_reveng) -- a practitioner's method note from the author whose `main.nw` underlies `a2-lode-runner`. To be read and summarised here.
- **Lancaster (1984), *Tearing Into Machine-Language Code*** -- classic method text. To be summarised here.

### Videos

- **Displaced Gamers** (YouTube) -- NES mechanics and bugs explained from the assembly, often with Mesen.
- **NesHacker** (YouTube) -- 6502 assembly and NES ROM hacking tutorials.
- **Michael Steil's congress talks** (media.ccc.de) -- "The Ultimate Commodore 64 Talk" (25C3), "The Ultimate Game Boy Talk" (33C3), and the Visual 6502 talk on reverse engineering the 6502 chip itself (27C3). ⚠ Gemini listed an "Ultimate NES Talk", which I believe does not exist.

---

## 8. Verification log

Claims from the Gemini draft that need checking before this document is relied on:

1. C64Debugger authorship (Gemini: "Denis V / D-Bug"; my understanding: Marcin Skoczylas).
2. Mesen scripting languages (Gemini: Lua and C#; my understanding: Lua).
3. VICE: existence of a raster breakpoint command and a `hunt` command; remote monitor vs. binary monitor options.
4. Snapshot comparison built into Mesen and C64Debugger.
5. Comparative/relational search in FCEUX and Mesen (exact feature names).
6. SourceGen: runs only on Windows? (relevant for a macOS-native workflow).
7. Diaphora support for Ghidra.
8. Any 6502 support in angr, Triton, Miasm, RetDec, Rellic.
9. NESicide maintenance status; NesCartDB current URL.
10. Regenerator authorship.

---

## 9. Open questions for `papple2`

To be discussed, not decided here:

- Which techniques should `papple2` build natively (where Python hooks give an edge), and which should it hand off to existing tools (e.g. export to SourceGen or Ghidra, import their labels back)?
- Should `papple2` speak a common format -- label files, CDL-style access logs -- so it can cooperate with those tools?
- How do the techniques line up with the Lode Runner "answer key" idea: which ones can be measured against Xekri's `main.nw`?
