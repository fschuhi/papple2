# papple2 -- Glossary

Definitions for the vocabulary used across `papple2`'s code, tests, documentation, and dialogue. Governed by the rules: *one name, one thing*, and *one thing, one name*. Positions in code are named by address as a 6502 programmer would.

---

## 1. The Machine & Core

* **Machine (`papple2.core`)**: The emulated hardware stack: `Emulator`, `Apple2`, `CPU` (6502), `Memory` (64 KB), `Display`, and `Speaker`.
* **Hook**: A callback function attached to a specific instruction or memory access point (`Memory` or `CPU`), reporting what just happened without stopping or altering control flow.
* **Trap**: High-level emulation of a routine at a fixed address (such as disk stand-ins for Lode Runner or Bandits), executed in Python instead of 6502 code. If unserved, it halts execution.
* **Breakpoint**: A condition or address evaluated by the `Emulator` at instruction boundaries that decides whether to pause execution.

---

## 2. The Run & Reports

* **Run**: One execution of the emulator for a specified number of instructions, starting from the current program counter (`PC`) with instrumentations attached.
* **Tile ("Unbroken Tile")**: A run of instructions from an entry point to the leap that leaves it, as recorded by `Tiling`. Tiles may overlap.
* **Split Tile / Basic Block**: A contiguous span of executed bytes cut at every observed entry point so that tiles never overlap.
* **Edge**: A control-flow connection between two basic blocks in a `BlockGraph`.
* **Call Fall-Through Edge**: An edge joining the block holding a `JSR` directly to the block following it, carrying the call's count.
* **Shadow Stack**: A secondary call stack maintained independently by `StackTracking` to record every `JSR` frame (`call_site`, `entry`, `expected_return`) and resolve `RTS` outcomes (*matched, redirected, unmatched, abandoned, open*).
* **Cross Reference (Xref)**: A recorded link between an instruction and a memory byte it touched, classified by access kind (*read_immediate, read_pointer, read_data, write_data*).
* **Target**: The address named by an instruction's operand as it ran (e.g., table base, pointer address).
* **Effective Address**: The actual memory address accessed by an instruction after applying indexing registers (`X`, `Y`) or pointer dereferencing.

---

## 3. Structure & Routines

* **Routine**: The set of basic blocks reachable from an entry point during a specific run, without following calls. Every executed block belongs to exactly one routine.
* **Entry**: The address where a routine starts (e.g., run start, `JSR` target, stack jump target, shared entry point, orphan).
* **Range**: The address bounds of a routine from its entry up to the next entry in memory.
* **Span**: The continuous address range from a routine's lowest block to its highest block, including unreached gaps.
* **Door**: An address where control enters a routine from outside other than at its primary entry (e.g., jumping into a shared tail or inner block).
* **Tail Call**: Ending a subroutine with a `JMP` to another routine instead of a `JSR` + `RTS`, saving stack space and return overhead.
* **Dispatch by `RTS`**: A computed jump where a routine pushes an address minus one from a table onto the stack and executes `RTS`.
* **Orphan**: A basic block reached by an edge that no existing routine claims, which then becomes a new routine entry.
* **Return Behind a Payload**: An `RTS` that returns for a `JSR` but lands further after it than 3 bytes because the subroutine read inline payload data.

---

## 4. The Workbench & Dossier

* **Dossier**: A persistent program folder under version control (`dossiers/lode_runner/`) holding human-authored definitions that survive across runs: `annotations.json`, `hidden.json`, and `colors.json`.
* **Annotation**: Human-authored labels and comments bound to memory addresses.
* **Hidden Range**: A named address span saved in `hidden.json` that collapses into a single grey summary row in listings and the editor.
* **Color Range**: A named address span and color shade saved in `colors.json` used for visual orientation across views, memory maps, breadcrumbs, and routine graphs.
* **Session (`papple2.workbench.session.Session`)**: The state object holding the active reports folder, open dossier, and current run.

---

## 5. Positions in Code

Positions in code are named strictly by address as a 6502 programmer would:
* **Lower / Higher**: Relative numerical comparison of memory addresses (lower = closer to `$0000`, higher = closer to `$FFFF`).
* **Before / After**: Relative placement in address order (before = at a lower address; after = at a higher address).
* **Backward / Forward**: The direction of a control transfer (jump or branch) relative to the current instruction pointer (`PC`).
* *(Note: "Above" and "Below" are reserved exclusively for vertical screen coordinates and rows in terminal UI listings; "behind" and "in front of" are avoided for code position).*
