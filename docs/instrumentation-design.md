# Instrumentation design

**Status:** decided in the design session of 2026-09-29. This document holds decisions; the raw material they came from is `docs/instrumentation-ideas.md` (the braindump), and the old design they replace is drawn in `docs/instrumentation-map.md` (the tag `pre-redesign`). Section 9 lists what is still open. Implemented so far (2026-09-29): the `Memory` methods per kind, the CPU calling them, and the hook lists in `Memory` (section 3). No hooks on `CPU` yet.

    **Purpose:** one place for the rules that span `Emulator`, `CPU` and `Memory`, so that they are not spread over comments in several modules.

---

## 1. Terms

Three kinds of instrumentation, each with its own small interface. There is no common base class: the difference between them is the point.

| | Breakpoint | Trap | Hook |
|---|---|---|---|
| Called by | `Emulator` | `Emulator` | `CPU` or `Memory` |
| When | at the boundary, before everything | at the boundary, after the breakpoints | inside the instruction, after an access or after the instruction |
| What it does | decides whether to stop; changes nothing | does a routine's work in Python instead of the 6502 code at its address | reports what just happened |
| Its answer | stop or not | served or not | none; the caller ignores it |

- **Breakpoint:** by address, or by condition (a conditional breakpoint; `until` is one today).
- **Trap:** the established term for doing a routine's work in the emulator's own language (high-level emulation). The disk stand-ins for Lode Runner (`$B7B5`) and Bandits (`$BF00`) are traps. A trap that cannot serve a request stops the run and says why; that is a trap failing, not a breakpoint.
- **Hook:** optional. Hooks of one kind share one interface, one set of rules, and a deterministic order (their order in the list).

## 2. The order at each instruction

```text
── boundary ─────────────────── Emulator
   breakpoints                  may stop: the instruction does not run
   traps                        served: continue at the PC the trap set
                                not served: stop, and say why
── do_next_step() ───────────── CPU and Memory
   Memory  read_opcode, after
   Memory  read_operand, after       (0, 1 or 2 times)
   Memory  read_pointer, after       (0 or 2 times)
   Memory  read_data / write_data / read_stack / write_stack, after
   CPU     after_instruction
── boundary ───────────────────
```

Only the `Emulator` stops execution, and only at the boundary, when its state machine receives an event. A hook runs inside `do_next_step()`, below the `Emulator`, and cannot stop anything; the machine cannot be halted in the middle of an instruction.

## 3. The `Memory` interface

The name of the method says *why* the CPU accesses a byte, not *where* the byte is: `LDA $0100,X` touches the stack page, but it is a data read.

| Method | Called from | Bytes per call site |
|---|---|---|
| `read_opcode(address)` | `do_next_step` | 1 |
| `read_operand(address)` | the addressing modes | 1 or 2 |
| `read_pointer(address)` | `JMP (abs)`, `(zp,X)`, `(zp),Y` | 2 |
| `read_data(address)` | the operations (`LDA`, `ADC`, `INC`, ...) | 1 |
| `read_stack(address)` | `RTS`, `PLA`, `PLP`, `RTI` | 1 or 2 |
| `read_vector(address)` | `reset()` (`$FFFC`), `BRK` (`$FFFE`) | 2 |
| `write_data(address, value)` | the operations (`STA`, `INC`, ...) | 1 |
| `write_stack(address, value)` | `JSR`, `PHA`, `PHP`, `BRK` | 1 or 2 |

- Each method is thin: it calls the shared `read_byte` or `write_byte`, where the device logic (soft switches, display) stays in one place, and then runs its own hook list.
- One after list per method, named after it with an `after_` prefix (`after_read_opcode` ... `after_write_stack`). A hook that only needs opcode reads is called once per instruction, not on every access. Each list is tested before its loop; with all lists empty, headless Lode Runner is about 3% slower (2026-09-29).
- Signatures: a read hook gets `(address, value)`, a write hook gets `(address, value, old_value)`. `Memory` keeps the old value before it overwrites it, taken straight from the memory list: going through `read_byte` would flip a soft switch at `$C0xx`.
- The addressing mode is not passed: every opcode has exactly one addressing mode, so it follows from the opcode. Zero page and `$00xx` absolute stay distinguishable that way.
- Only bytes reach the hooks. A 16-bit read is two byte reads of the same kind, low byte first: `read_operand_word`, `read_pointer_word` (with the page wrap: at `$xxFF` the high byte comes from `$xx00`), `read_vector_word`.
- **Immediate operands:** the operations read their operand with the same call they use for data, so an immediate operand (the `$05` in `LDA #$05`) is reported by `read_data`. The core leaves this as it is for now; a hook that cares corrects the label from the opcode (11 opcodes use immediate mode). To be revisited when an experiment shows the need; it matters for detecting self-modifying code, because changing an immediate operand is a classic trick.
- **Direct access to the memory list** (`mem[...]`) means "past devices and hooks, on purpose". There are no `peek` and `poke` wrappers. Loaders and traps write this way, and the disassembler reads this way; and traps log their whole task as one entry instead of reporting each byte.

## 4. The `CPU` side

- One list: `after_instruction`.
- Fields a hook may read during its call: instruction count, instruction PC, opcode. Hooks read what they need from fields instead of receiving it as arguments; only what is gone afterwards (address, value, old value) is passed.
- No saving of registers and flags before the instruction, and no switch for it. A hook that needs the state before an instruction keeps the values from the previous `after_instruction` call, or the trace does it afterwards. That approximation breaks right after a trap, which is one reason traps log what they did.

## 5. Position

- Every observation is placed by run and instruction count.
- A run is everything since a fresh start. Continuing after a breakpoint is the same run.
- The instruction count lives in `CPU` and is reset only at a fresh start. It is not `Emulator.instructions`, which every `run()` call resets and which `after_instructions(n)` relies on.

## 6. Rules

1. `CPU` and `Memory` ignore whatever a hook returns. (The old `write_hook` dropped a write when a logger returned `None`.)
2. Hooks may change the machine, by convention only at boundaries. Nothing prevents more; we are close to the machine on purpose.
3. A hook cannot stop execution. It can request a stop; the `Emulator` acts on the request at the next boundary.
4. `papple2.core` holds the hook lists and calls them through fixed interfaces, and nothing else. What a hook does with the data is none of the core's business: ring buffers, counters and logs are building blocks outside `core`.
5. Speed is measured, not assumed: before and after each change to the core, and with all hook lists empty, since that is the price every run pays.

## 7. Building blocks (outside `core`)

- **`RingBuffer`:** the black box for mass collection. It presents its content in order, so it can be sliced and searched backwards in time. A writer can count entries since the last flush and save blocks to disk, which turns the black box into a continuous log.
- **Per-address arrays:** for questions that need state per address, not history. Example: the execution-count map, with four counters per address (opcode fetch, operand fetch, data read, data write).
- Typical use in the beginning: standard observers fill ring buffers; analyzers act on after-hooks, do some analysis online, and write entries into a specialised log. No way of doing things is prescribed.

## 8. Deliberately left out (for now)

- Before lists on `CPU` and `Memory`. Breakpoints run before the instruction, at the boundary.
- Steps within an instruction as part of the position.
- A `CPU` position between decoding and executing: the dispatch table computes the address and executes in one expression, and the kind of each read makes such a position unnecessary.
- Save states. `pickle`/`unpickle` are removed; snapshots will be designed fresh when an experiment needs them.
- An event queue. `pysm` dispatches immediately; a queue would be a small wrapper of our own, drained at the boundary.

## 9. Open

- How a hook requests a stop, concretely.
- `until`: stays a parameter of `run()` for now; it could become a conditional breakpoint in the `Emulator`'s list. With a window it already pauses the run instead of ending it (2026-09-29). The ready-made conditions live outside `core`, in `papple2/debug/stop_conditions.py`.
- How an experiment gets its hooks into the lists: an `attach()` on `Emulator` that passes an object to `Memory` and `CPU`, or plain `append`. Decide with the first experiment.
- Devices: how the soft switches, the keyboard and the display fit with the hooks. Look at how they work today first.

## 10. First experiments

On Lode Runner, inside a level (the level loader comes later):

- a memory map with execution counts;
- detecting self-modifying code;
- finding lookup tables used together with screen writes.

These are prototypes of the tools, not yet sleuthing.
