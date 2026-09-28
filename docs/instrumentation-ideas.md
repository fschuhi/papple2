# Instrumentation ideas -- braindump

**Status:** braindump, nothing decided. Collected 2026-09-26 to 28 while preparing the clean-slate redesign of `papple2`'s instrumentation.
**Sources:** each idea is labelled by who brought it in: **[user]** (project owner), **[Claude]** (this `papple2` conversation), **[Astra]** (a separate conversation with GPT-6-Astra), **[Gemini]** (a separate conversation about storage speed).
**Old code:** everything referred to as "old" is at the git tag `pre-redesign` (commit `0797250`).

This document is raw material for a later design document. Order within sections is loose, and ideas may contradict each other.

---

## 1. Starting point

- **[user]** The goal: trace logs and other execution artefacts that can go into Ghidra and other tools, to understand what Lode Runner does, and to compare that understanding against the oracle (`main.nw`, the literate source).
- **[user]** This is a redesign, not an improvement of the old hooks. The question is "what should this system be", not "how do we fix what we have". Existing mechanisms are evidence, not foundations. Existing uses matter; how they were implemented doesn't.
- **[user]** The machine stays: the parts of `cpu.py`, `memory.py`, `apple.py` and `emulator.py` that make up the Apple II itself (instruction semantics, memory, soft switches, display, keyboard). Hook call sites inside those files are instrumentation and may change.
- **[user]** Structure first, then experiments -- not the other way round. An experiment needs a structure to test.
- **[user]** A protocol that spans several modules doesn't work as comments near the code. It belongs in one document that can be held in view.
- **[user]** Wanted: an "example lifecycle" of one execution step, as the spine of the design.
- **[user]** The old tiles / basic blocks, the beginnings of data flow, and stretches (superblocks) are powerful paradigms. Functionality to keep in mind, not code to keep.
- **[user]** The disk stand-ins were a deliberate "deus ex machina": keeping Python out of the 6502 execution, because mingling the two felt like a category error. The same holds for their fake `RTS`.
- **[Astra]** Central principle: record what happened once; let independent tools interpret it in different ways. A memory write may interest a watchpoint, a screen-write analyzer, a last-writer index and a trace file; they should all consume the same observation.

## 2. Lessons from the old design (evidence)

- **[Claude]** One return shape for three jobs: checkpoints returned `(stay_active, execute)` but served as stop conditions (`until`, watches), input (`KeyScript`) and stand-ins (`RwtsHook`, `MliHook`). Two booleans can't describe all three, so the rules grew exceptions: `stay_active` was ignored when `execute` was `False`, and `PrintCharTester` returned `(False, False)` expecting to switch itself off, which it didn't.
- **[Claude]** After one checkpoint stopped execution, the remaining checkpoints still ran in the same pass. A checkpoint that changed `PC` made later checkpoints see the new `PC`.
- **[Claude]** A stand-in's fake `RTS` made `post_op()` record a jump that no instruction made, and the caller's `JSR` stayed on `jsr_stack`.
- **[Claude]** The stand-ins' memory writes were invisible to the access log: `RwtsHook` wrote into `em.mem` directly, `MliHook` through `Memory.write_byte`, and only `CPU.write_byte` called `write_hook`.
- **[Claude]** The rules lived in five places: `Emulator.run()`, `Emulator.post_op()`, `CPU.read_byte`/`write_byte`, `CPUHook`'s hand-chaining, and the scripts' own habits.
- **[Astra]**, **[Claude]** A `write_hook` returning a falsy value vetoed the write. An ordinary logging callback returns `None`, so installing a logger there silently swallowed writes.
- **[Astra]** `Memory.unpickle()` replaced `_mem` while `Emulator.mem` and `EmulatorStates.mem` kept references to the old list.
- **[user]** Some things broke, some didn't, depending on the order of checkpoints and on side effects between hooks.

## 3. Questions the system should answer

- **[Astra]** Which instructions execute? Why did execution reach this address? Who changed this value? Where did this value come from? What code draws this object? What happens when I press a key? Is the program modifying its own code? What differs between two runs?
- **[Claude]** Where did this byte come from, including from outside the CPU ("from disk, track `$0C`, sector `$0F`")? Which code in `main.nw` did we never execute? Which bytes did we execute that `main.nw` calls data?
- **[user]** How does the stack evolve, beyond simple `JSR`/`RTS` pairs? Its tricks will be important for identifying parts of the code.
- **[Astra]** Suggested first project: "who last wrote this address?", plus a short instruction history around that write.

## 4. Roles

- **[Claude]** Three roles:
  - **Stop conditions** ask "stop here?" and change nothing.
  - **Interventions** (stand-ins, key presses, experiments like poking an `RTS`) change the machine, and must report what they did.
  - **Observers** receive every report and change nothing.
- **[Claude]** Yardstick: *everything that changes the machine appears in the trace, and nothing that only watches can change the machine.*
- **[Claude]** Interventions may still do anything in Python. The freedom stays, but it gets a label, and the intervention has to say what it did.
- **[Astra]** Four responsibilities:
  - **Observers** receive facts and don't change emulation (`Observer = Callable[[Event], None]`).
  - **Analyzers** maintain derived knowledge (last writer per address, observed control-flow graph, tentative call stack, labels, self-modifying-code detection) and publish derived observations.
  - **Triggers** recognise conditions and request actions (`Trigger = Callable[[Event], ControlRequest | None]`).
  - **Interceptors** intentionally change behaviour (suppress a write, substitute input, patch memory, override a device response). Keep them separate from observers, or enabling a logger might change execution.
- **[Astra]** Analyzer output distinguishes observed facts from interpretations. Fact: an `RTS` finished with `PC=$3456`. Interpretation: it returned from a particular earlier `JSR`. Alternative: it was a computed jump.
- **[user]** Order matters for observers after all: some are useful before interventions, some after, some at the very beginning of a step, some at the very end.
- **[Claude]** Three different ordering questions:
  - *When in the step* an observer runs: real. Name the points (step start, after interventions, memory access, step end, plus run start and run end) instead of sorting a list. Stop conditions run at step start, before any intervention.
  - *Order within one phase*: shouldn't matter if observers can't change anything.
  - *One observer using another's results*: a dependency, modelled as a chain. The first observer publishes its own events ("call", "return", "return address discarded", "stack reset"), and others subscribe to those.
- **[Astra]** Dispatch order is deterministic (rule 3 in section 7).
- **[user]** "Specialists" are needed, e.g. one that tracks the evolution of the stack.

## 5. Lifecycle

- **[Astra]** Example lifecycle of one instruction:

  ```text
  evaluate pre-instruction breakpoints
  InstructionBegin
      MemoryRead
      MemoryRead
      MemoryWrite
      DeviceEffect
  InstructionEnd
  update analyzers
  evaluate post-instruction triggers
  apply pause request
  ```

  The precise memory/device ordering should match the implementation. A read can cause a device effect before the read returns; causal IDs can represent that.
- **[Claude]** Per step, with interventions:

  ```text
  1. stop conditions   "stop here?"                  change nothing
  2. interventions     stand-ins, key presses,       change the machine,
                       experiments                   and report what they did
  3. CPU executes      reports every read and write
  4. observers         receive every report          change nothing
                              |
                              v
        trace -> code/data marks, coverage, JSR/RTS pairs -> Ghidra, main.nw comparison
  ```

- **[user]** Can instrumentation be captured as a statechart, for implementation and for documentation? Possibly overthought.
- **[Claude]** Two levels. The run level is a statechart: running, paused, stopped at a breakpoint, and the events between them. One step is a fixed sequence, not a set of states, so a lifecycle list fits better. Two pictures in the design document.
- **[Astra]** Pause before versus pause after:
  - Execute breakpoints stop *before* the instruction.
  - Memory watchpoints detect during execution and stop *after* the instruction.
  - Instruction-count limits stop at an instruction boundary.
  - Never stop mid-instruction by raising an exception from a memory observer; that can leave CPU, memory and devices half-changed.

## 6. Events

- **[Astra]** A small vocabulary: `InstructionBegin`, `MemoryRead`, `MemoryWrite`, `DeviceEffect`, `InstructionEnd`, `InstructionFault`, `InputDelivered`, `StateRestored`, `MemoryPatched` / `ImageLoaded`.
- **[Astra]** Common fields: `event_sequence`, `run_id`, `instruction_id` (optional; not everything happens inside an instruction), `origin` (cpu, debugger, loader, input, replay, ...), `instruction_pc` (the stable start PC, not the mutable current PC).
- **[Astra]** Memory event fields: `address`, `value`, `operation`, `region` (RAM / device / other), `backing_old_value` (optional), `parent_event_id` (optional causal link).
- **[Astra]** A monotonic instruction ID, independent of `Emulator.instructions`, which `run()` resets.
- **[Astra]** Access roles such as "opcode fetch", "pointer read" or "data read" allow `unknown`. Don't present an inference as ground truth.
- **[Astra]** Operations outside CPU execution become explicit events (`ImageLoaded`, `MemoryPatched`), not thousands of invented CPU writes.
- **[Claude]** Interventions report their effects as events. The RWTS stand-in reports "256 bytes written to `$1F00`, from disk T$0C S$0F" and "returned as `RTS` to `$637C`, `SP` + 2". This keeps the user's category distinction (no fake `STA`s) and makes it visible, and it gives provenance for free: later, "where did this level byte come from?" has an answer.
- **[Claude]** The stand-in declares "returns as `RTS`" rather than letting a stack analyzer infer it from `SP` + 2 and `PC` = popped + 1. The analyzer can still check the declaration.
- **[Astra]** Device events reference the memory access that caused them: `read $C010 -> $00` causes "keyboard strobe cleared". Don't infer device changes merely from a write value.

## 7. Interaction rules

- **[Astra]**
  1. Observers cannot modify machine state.
  2. Events contain captured values, not references that consumers later read from mutable CPU state.
  3. Dispatch order is deterministic.
  4. Adding or removing subscriptions takes effect at a defined boundary, preferably the next instruction.
  5. Pause requests are combined centrally, rather than one callback overriding another.
  6. Observers do not recursively step the emulator.
  7. Failures and dropped events are explicit.
- **[Astra]** Capture the completed CPU observation before running more complicated analysis. An analyzer failure must not make a successfully executed instruction disappear from the trace. Separate instruction faults from instrumentation faults.
- **[Astra]** Never inspect devices by accidentally operating them: `read_byte` (emulated access, side effects allowed) versus `peek_byte` (inspection, no side effects). Reading `$C010` changes keyboard state; a disassembler or trace formatter must not do that just to show a value. Backing `_mem[address]` is not necessarily what an emulated read returns.

## 8. The machine seam: how reads and writes happen

- **[user]** Open question: how do `cpu.py`'s reads and writes, including indirect addressing, shape the architecture? Some of the old hook design was probably driven by how `cpu.py` (and the 6502) does things.
- **[Astra]** Facts from the old `cpu.py` and `memory.py`:
  - Opcode and operand fetches, and immediate reads, skip the CPU's read hook.
  - CPU word reads produce one word-valued callback.
  - `Memory.read_word()` and `read_word_bug()` read their bytes through `self.read_byte()`.
  - `LSR` on memory calls `read_byte()` twice.
  - Cycles are accumulated arithmetically; there is no per-bus-cycle interface.
- **[Astra]** Instrument `Memory`'s byte methods, not only the CPU's hooks. A subclass overriding `read_byte()` catches the internal word reads; a proxy that delegates `read_word()` to uninstrumented memory doesn't. Pick one canonical source for memory-access events: don't count a word callback and its two byte reads as three reads.
- **[Astra]** Describe the result honestly: "an instruction-level trace with memory-operation observations -- not a cycle-accurate hardware bus trace". Record access order and the emulator's cycle totals; don't assign exact hardware-cycle timestamps; don't silently correct duplicate accesses in the raw trace.
- **[Astra]** Direct `_mem` assignments and slice assignments bypass byte-method instrumentation.
- **[Claude]** Open: indirect addressing modes (`(zp),Y`, `(zp,X)`, `JMP (abs)`) read a pointer, then the data. Whether the seam can tell a pointer read from a data read decides whether "pointer read" is a fact or an inference.
- **[user]** Proposal: tell `read_byte()` what kind of read it is doing -- through a parameter or through separate methods -- and let that information flow into the trace. Then `Memory` knows it too; "only the CPU knows why" is a property of today's interface, not a law.
- **[user]** `hook=False` in the old `cpu.py` was a policy ("don't let anyone see this read"), not a fact. Together with the vetoing `write_hook`, it was where observing and modifying got mixed up, and it baked in the decision not to trace opcode and operand reads.
- **[Claude]** Keep the fact, drop the policy: report every access, deterministically, and say what kind of access it is.

## 9. The record per executed instruction

- **[user]** Open question: which information do we store for each executed opcode? Partly inspired by what trace tools need.
- **[Astra]** Capture: start PC, registers and status before and after, resulting PC, cycle counter before and after, opcode and instruction-byte evidence, associated memory and device events.
- **[Astra]** Prefer the bytes returned by the actual instruction-stream reads. Don't reconstruct old instructions later from current memory.
- **[Claude]** Proposals, from a sketch of the first RWTS call at `$B7B5`:
  - Registers *before* the instruction, as trace loggers usually do. "After equals the next line's before" breaks at interventions, which is why interventions list what they changed.
  - Record the executed bytes (1 to 3), not only `PC`, because with self-modifying code the same `PC` can run different bytes.
  - `SP` in every record, and every write to `$0100`-`$01FF`, so the stack can be reconstructed.
- **[user]** The CPU also reports the current flags.
- **[user]** The `$B7B5` sketch was premature: structure first. Kept here only as an example of what a record might need.

## 10. Stack specialists

- **[user]** The stack does much more than `JSR`/`RTS` pairs, and tracking it will be important for identifying code.
- **[Claude]** A shadow stack sees what a `JSR`/`RTS` matcher can't:
  - `PHA`/`PHA`/`RTS` as a jump table;
  - `PLA`/`PLA` throwing away a return address;
  - `TXS` resetting the stack;
  - `RTI`;
  - data after a `JSR` that the routine skips (the ProDOS MLI's three bytes);
  - direct writes into page 1.
- **[Astra]** Treat call tracing as a hypothesis: include uncertainty and unmatched returns, and keep the actual control-flow observations even when the inferred call stack becomes unreliable.

## 11. Self-modifying code and the oracle

- **[user]** Self-modifying code will be a major source of confusion, if not in Lode Runner, then certainly in Bandits (the Ngo brothers were known for it).
- **[Claude]** `main.nw` assembles byte-identically, so its listing says for every address whether it is code or data. Comparing a per-byte code/data log with it shows code we never executed (a coverage gap) and executed bytes `main.nw` calls data (self-modifying code, or our bug).
- **[Claude]** Limit: `main.nw` describes the bytes as loaded; the trace describes what ran. Where they differ, the cause is self-modifying code or a bug, and `main.nw`'s prose may say which.
- **[Astra]** For changing code, distinguish instruction versions by captured bytes, not just by address.

## 12. Storage and speed

- **[user]** Questions: how to store each piece (tuple, `dataclass`, ...) and the whole collection (list, array, ...)? Is writing to a socket, with another process saving into SQLite, faster than internal lists?
- **[Gemini]** Socket writes per event cost microseconds (serialisation, system call, context switch) and would slow a 500,000-instructions-per-second loop by one to two orders of magnitude. If out-of-process logging is ever needed: batch into byte buffers and flush in bulk. SQLite per-row inserts during execution are far too slow; fill SQLite in bulk afterwards, or from a binary log.
- **[Gemini]** Chunked, preallocated `bytearray`s written with `struct.pack_into`: write fixed-size binary records during the run, unpack later.
- **[user]** Measured on the M4 with Gemini's benchmark, 1M / 10M events: tuple + `list.append` 49 / 42 ns; `dataclass(slots=True)` 327 / 386 ns; chunked `bytearray` 102 / 100 ns to record, plus 396 / 379 ns to unpack into `dataclass`es.
- **[Claude]** Check in a Linux sandbox (Python 3.12.3, slower machine, 2M records; garbage collector on / off):

  | | on | off |
  |---|---|---|
  | keep tuples | 134 ns | 85 ns |
  | keep `dataclass`es | 542 ns | 160 ns |
  | create a `dataclass` without keeping it | 125 ns | 129 ns |
  | `pack_into` inside a method | 125 ns | 122 ns |
  | `pack_into` called directly | 75 ns | 74 ns |

- **[Claude]** Readings:
  - Keeping millions of objects is what hurts: the garbage collector walks them again and again, so the cost grows with how many are kept.
  - Bytes keep no objects: no collector cost, about 10 bytes per record instead of about 100.
  - Unpacking everything into objects brings the cost back. Instead, read the bytes with `numpy` (`np.frombuffer` with a record layout gives named columns without one Python object per record), or load them into SQLite.
- **[Claude]** The per-instruction budget: at about 1.9 µs per instruction (520,000 per second headless), the record format costs a few percent. The number of Python calls per instruction costs more, and every observer on the hot path adds at least one. So: few observers per instruction; specialists run on rare events, or later from the recorded trace.
- **[Astra]** Start with structured in-memory events, a readable text renderer, JSON Lines for short sessions, and counters and indexes that don't retain every event. Later: filters before formatting, buffered output, ring buffers, an explicit overflow policy, run metadata (image hashes, initial state, emulator version, enabled instrumentation).
- **[Astra]** Triggered history as the default investigative mode: keep a bounded recent-history buffer and save it when something interesting happens, rather than writing every event to disk.
- **[Astra]** A trace is replayable only with a known initial state, external inputs injected at recorded instruction boundaries, and all machine-state changes accounted for.
- **[Astra]** Decide on either tracking bytes or tracking semantic units, not both.
- **[user]** (devil's advocate) Record per access and just grow a list of tuples -- the one thing Python does really well. Offline trace readers, and online analyzers for specific situations, do the interpreting. Python means being very selective in what is done live.
- **[Claude]** A tuple append costs about 45 ns on the M4, so three or four accesses per instruction add roughly 150 to 200 ns to about 1 microsecond: affordable. What bites is growth, not speed: millions of kept objects per second are where the garbage collector cost showed up, so long runs need a ring buffer or regular flushing to disk. Tracing fetches as separate events roughly triples the number of events per instruction; one record per instruction carrying the bytes as fetched covers them for the price of one.
- **[user]** Measured on the M4 with the throttle (2026-09-27): 3.55x a real Apple II unthrottled, but only 1.51x while awake when throttled -- the emulator gets slower once it sleeps regularly. So the real headroom at Apple II speed is about 1.5x: the budget the new instrumentation has to fit into.

## 13. Consumers

- **[user]** Ghidra: not known yet. Other tools too.
- **[Claude]** Ghidra is the NSA's open-source reverse-engineering suite: a disassembler and decompiler with a per-address database, scriptable in Java and Python, with a 6502 processor module (general knowledge, to be checked). A Ghidra script could read our marks and labels. The trace shouldn't be shaped for Ghidra; if it's complete, any consumer can use it.
- **[Astra]** Last-writer index: `address -> most recent write event and instruction`. Simpler than full data flow and immediately useful.
- **[Astra]** Execution coverage and an *observed* control-flow graph: `instruction address -> count`, `(source, destination) -> count`. Unexecuted paths remain unknown.
- **[Astra]** Screen-write attribution: `writing instruction -> screen addresses touched`, to investigate "what draws this object?".

## 14. Reference points

General knowledge, not checked; terms to search for.

- **Frida:** `Interceptor.attach` (watch a function) versus `Interceptor.replace` (replace it). The disk stand-ins are replacements.
- **Unicorn engine:** one callback per event type (`UC_HOOK_CODE`, memory read/write); stopping and removing hooks are separate calls, not flags in a return value.
- **Intel Pin:** analysis calls inserted before an instruction, after it, or on the taken branch.
- **High-level emulation (HLE), traps:** doing a routine's work in the emulator's own language, as the disk stand-ins do.
- **MAME debugger:** watchpoints separating watched access, condition and action; `pcatmem` for "which PC wrote this memory" (per Astra).
- **Mesen, FCEUX:** trace loggers and code/data loggers.
- **Shadow call stack:** a second, analysis-side model of the stack.

## 15. Tiles and stretches

- **[user]** What they were for: tiles and stretches project the execution path onto the serial, one-dimensional listing, like the literate-source model of XekriRedmane's documentation. A stretch -- consecutive tiles stitched together -- has a good chance of being part of a subroutine, so stretches point to subroutine candidates. Typical cases: relative branches out of a tight loop that land right behind its end, or execution falling through a branch that loops upwards. The longer the stretches, the more compact the call graphs: like zooming out, or a folding editor.
- **[user]** The linked list (`link_next`/`link_prev`) was a faithful translation of what "stitching" means -- borrowing a concept from another domain and implementing it true to its meaning. More than one leap out of the same position never came up.
- **[Claude]** The three stitching rules of the old `tiles.py`: two tiles adjacent in memory are linked if execution fell through from one to the next, if the first ends in a branch that was always taken, or if it ends in a `JSR` whose `RTS` came back to the very next instruction.
- **[Claude]** Suggestions for the new design: control-flow edges (from, to, kind) as the data, and chains along the listing as one view computed from them -- a pointer allows one successor, real control flow has many. Tiles are basic blocks *as observed*: a leap target not yet executed doesn't split a block, so blocks change as coverage grows, and are best computed afresh from a recorded trace (with `numpy`, finding where blocks start is a few array operations). The stitching itself was never the cost; building `MemoryMap` live on every instruction was.
- **[Claude]** Search terms (general knowledge): superblock and extended basic block (a chain of blocks with one entry), trace, IDA's function chunk, QEMU's translation block chaining (several of these are already in `DIRECTION.md`'s glossary); function boundary detection or function identification (finding subroutines); structural analysis or control-flow structuring (collapsing loops and ifs into single nodes, as decompilers do); Ghidra's subroutine models, one of them named "Partitioned Code" (to be checked).

## 16. Keeping what we've learned

- **[user]** The old tile lists in Excel showed notes from `Annotations` (address -> topic -> value) next to each tile, which made the dumps much more readable. How learnings persist across experiments has to be revisited in the new design.

## 17. Open questions

- The machine seam: which events can the machine report as facts, and which are inferences (section 8)?
- The record per executed instruction (section 9).
- Which analyzers run live, and which run later from the recorded trace?
- Trace storage format, and how big a full Lode Runner trace gets.
- How stand-ins declare their effects, and what a stand-in's `RTS` looks like in the trace.
- Run-level statechart: which states and events are needed at all?
- Where the design document lives, and how tests pin its rules.
- Which of the old paradigms (tiles / basic blocks, stretches, data flow) come back, in which form, and when.
- How learnings persist across experiments (section 16).
- Tiles and stretches in the new design: which views, computed when (section 15).
