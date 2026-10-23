# papple2 -- Glossary

The words used across `papple2`'s code, tests, documentation and dialogue, governed by two rules: *one name, one thing*, and *one thing, one name*.

---

## 1. Roles & Workflow

- **Hats:** the roles the user works in, each with its own question and its own artefacts. The **reverse engineer** asks what the code does (the prompt, the dossier, the reports); the **product manager** asks what the workbench should let me do, and in what order (`GOALS.md`, `TODO.md`, the contract in `workbench.md`); the **developer** asks how it works and whether it is right (PyCharm, patches, tests). At the prompt, the reverse engineer notes what feels awkward instead of fixing the tool. In conversation, a prefix names the hat: "RE:", "PM:", "Dev:".
- **Experiment:** one `lr_` script in `scripts/`: a recipe, and whatever analysis or functions of its own it adds. Some experiments only read the reports of others (`lr_current.py`).
- **Recipe:** the part of an experiment that wires up the run and writes the reports: a few lines of commands, the same ones you could type at the prompt. No object of its own.
- **Walkthrough:** the book that teaches the pipeline on three small programs, told as tests: each test in `tests/test_walkthrough.py` is one chapter, in the order the pipeline goes. `scripts/walkthrough.py` is its chapter 0: it runs a program's recipe and writes the reports into `tmp/walkthrough/<program>/`. Because the chapters are tests, the walkthrough stays true while the code changes. `make walkthrough-md` renders it as `tmp/walkthrough/walkthrough.md`.
- **Command:** a function in `shell.py` meant for the prompt and for experiments. The commands are the **contract** between `papple2`'s developers and its reverse engineers: documented, and kept working.
- **`show_` and `print_`:** a `show_` command works on the current run and takes at most one address or label, plus switches such as `raw` in `show_xrefs()`; a `print_` function takes the objects it prints. A `show_` command returns what it shows as text, as `listing()` and `hexdump()` do, for IPython to show as `Out[n]` and `clip()` to copy; a `print_` function prints. `show_routine_graph()` is the exception: it draws into `tmp/routine_graph.svg`, puts the link on the clipboard, and returns nothing.
- **Session:** the object that holds what the commands work on: the reports folder, the open dossier with its stores, and the current run with its routines. `shell.py` keeps one, `shell.session`; a second terminal has its own. It never prints: a command prints what it gives it.
- **Machinery:** everything else reachable at the prompt (`shell.session.run_emulator`, `shell.session.routines`, ...): there for debugging and curiosity, with no guarantee.
- **Graduate:** a function moves from its experiment into `shell.py`, once it proves useful beyond it.

---

## 2. Positions in Code

- **Lower, higher, before, after, backward, forward:** positions in code are named by address. A lower address comes before, a higher one after; a jump to a lower address goes backward, to a higher one forward. The instruction directly after a `JSR` starts 3 bytes after the `JSR`'s address. A comparison of values names the address: "the orphan with the lowest address". Above and below are used only for rows on the screen, in `listing()` and `edit()`, where the lower address is shown above. Order in time, during a run, is earlier and later. In `edit()`, Backspace goes back and f forward through the places shown: history, not positions. Not used for positions in code: behind, in front of, up, down.
- **Range, start, end:** a range of addresses is half-open: `start` is its first byte, `end` the first byte after it. `6004-6007` holds three bytes. `end` is never the last byte. A pair that includes both bounds is `first` and `last`. An inclusive range, from first to last, is written with two dots: `$0000..$1FFF`. The Monitor writes it with one dot, `0.1FFF`; outside sources are quoted as they are written.

---

## 3. The Machine, the Run & the Dossier

- **Program setup:** how `papple2` loads and starts one program, a module in `papple2.programs`: `lode_runner`, and the walkthrough's `nested_loops`, `rts_dispatch` and `memory_tour`. Not the program, not its dossier.
- **Breakpoint:** called by `Emulator` at the instruction boundary, before everything else; decides whether to stop and changes nothing. Made with `break_at(address)`, kept by the emulator across runs.
- **Trap:** called by `Emulator` at the instruction boundary, after the breakpoints; does a routine's work in Python instead of the 6502 code at its address (high-level emulation). The disk stand-ins for Lode Runner (`$B7B5`) and Bandits (`$BF00`) are traps. A trap that cannot serve a request stops the run and says why.
- **`until` condition:** a function passed to `Emulator.run(until=...)`, asked at the instruction boundary after the breakpoints and traps; returns True when the run should stop. Ready-made ones are in `stop_conditions.py`: `instruction_count_reaches(n)`, `at_address(address)`. Not a breakpoint: it belongs to one call of `run()`. The emulator names its stop event `'breakpoint'` for all three ways of stopping.
- **Hook:** a callback in `CPU` (`after_instruction`) or `Memory` (`after_read_opcode` ... `after_write_stack`), called inside the instruction after an access or after the instruction, reporting what just happened. Hooks cannot stop execution, and the caller ignores what they return.
- **Run:** one execution of an emulator for a number of instructions, from where its `PC` stands, with instrumentations attached. The **current run** is the one the commands work on. There is one at a time; a second one means a second terminal.
- **Instrumentation:** a class whose objects watch a run through the emulator's hooks: after every instruction, or after reads and writes of memory. `Tiling`, `StackTracking`, `CrossReferencing`, or a class typed at the prompt.
- **Report:** a file an experiment writes.
- **Digest:** a CSV derived from one or more reports, for reading in an editor or in Excel; it may join in the dossier's names. `lr_xrefs_compressed.csv` (`make xrefs-compress`) is one; planned: `lr_xrefs_digest.csv`.
- **Reports folder:** an experiment's home, `docs/reports/<experiment>/`: where its reports go, and where it reads its own. One at a time.
- **Dossier:** everything we know about one program, a folder under git: `dossiers/lode_runner/`. Annotations, hidden ranges and color ranges are separate files; snapshots may follow.
- **Annotations:** the labels and comments in a dossier, by address, in `annotations.json`.
- **Label:** the name of one address; one text names one address only. Snake case: `lookup_hgr`; the Apple II's standard labels stay uppercase (`r:KBD`), so they stand out. A local label is typed as `.loop1` and stored with the global label before it as its owner (`routine_6238.loop1`).
- **Hidden range:** a named range of addresses saved in `hidden.json`, shown as one collapsed row rather than decoded bytes.
- **Color range:** a named range of addresses and a shade saved in `colors.json`, used by shared lookup functions and rendered according to each view's purpose.

---

## 4. Tiles, Routines & Control Flow

- **Leap:** a branch, `JMP`, `JSR`, `RTS`, `RTI` or `BRK`. **Glide:** the CPU runs on into the next instruction, without a leap.
- **Entry point:** an address where a tile starts: where the run started, or where a leap led and code then ran. Split tiles are cut at every entry point. Not an entry, which is where a routine starts.
- **Tile:** a run of instructions from an entry point to the leap that leaves it, as recorded. Tiles as recorded ("unbroken") may overlap.
- **Split tile:** a tile cut at every entry point inside it; split tiles do not overlap. Each split tile becomes one **basic block** of the graph, **block** for short; the graph's connections are **edges**. A **call fall-through edge** joins the block holding a `JSR` to the block directly after it, instead of an edge into the callee. A call whose return was redirected gets one too, to where the return landed, e.g. past the bytes directly after the `JSR` that the callee read. Neither is drawn as an arrow in a listing.
- **Transition:** the run moving from one tile into another, counted by source tile, the leap's address and opcode, the outcome and the target tile, in `lr_unbroken_transitions.csv` and `lr_split_transitions.csv`. A branch's outcome is `taken` or `fall_through`. Between unbroken tiles every transition is a leap; between split tiles each cut adds one with the outcome `glide`. The graph's edges are built from the split transitions.
- **Back edge:** an edge whose target dominates its source; it closes a loop. A term of the graph, not a direction in memory: most back edges jump backward, but the graph decides, not the addresses.
- **Loop:** a natural loop (`Loop` in the code): the target of a back edge, its **header**, plus every block that reaches the back edge's source without passing the header; together they are the loop's **body**. Back edges with the same header make one loop. A loop inside another has that loop's header as its **parent**. A loop's **depth** counts the loops around it, 0 for the outermost; a block's depth counts the loops it lies in. `loop_reports()` names the loops `L01`, `L02`, ... in the order of their headers, in `lr_loops_<entry>.csv` and `lr_loop_members_<entry>.csv`.
- **Routine:** the code reachable from an entry, without following calls; every block of a run lies in exactly one routine. A routine is a hypothesis from one run: code that never ran belongs to no routine, and another run can show blocks this run never reached. Where a routine starts, where it stops, its span, and what the tools show of it: [`routine.md`](routine.md).
- **Entry:** the address where a routine starts.
- **Orphan:** a block an edge leads to, but that no routine holds. Of the orphans, the one with the lowest address becomes an entry.
- **Door:** an address where control enters a routine (or a Xekri subroutine) from outside other than at its entry, e.g. `6fb6 JMP` into `6f29` (`TRY_GUARD_MOVE_UP_inc_anim_state`), inside routine `6f26` (`TRY_GUARD_MOVE_UP_check_for_gold`). `ways_in()` and `u` in `edit()` list jumps through a door as ways into the routine.
- **Exit:** a `JMP`, a branch or a glide from a routine's block into another routine's entry. It is not followed; for the other routine, it is a way in. `show_routine_graph()` draws exits as arrows between routines.
- **Exit at the door:** the block directly before a routine's entry that ends right at it, e.g. the `RTS` at `71a1` before `SHOULD_GUARD_MOVE_LEFT`. A jump backward to it is followed; any other jump backward past the entry is not.
- **Way in:** how control entered a routine: a `JSR`, a `JMP`, a branch or a glide from another routine's block, or the `RTS` of a stack jump, into its entry or through a door. Its site is the address of the leap, or for a glide the start of the block that glides. `ways_in()`, `show_ways_in()` and `u` in `edit()` list them.
- **Span:** a routine from the block with the lowest address to the end of the block with the highest, gaps included, as `listing()`, `edit()` and `lr_listing.tsv` show it. The block with the lowest address may lie before the entry, and the span includes the code of other routines, or code that never ran, that lies between the routine's blocks. For a Xekri subroutine, its span runs from its start to the first address after its last instruction.
- **Lies within:** position only. Data, payload or code of another routine that lies within a span is not claimed as belonging to it. Whether it belongs is a question for stretches.
- **Call:** a `JSR`, and nothing else. Its routine is the callee, the routine holding the `JSR` the caller. A call need not return: the shadow stack (`StackTracking`) tells whether it did. Every other way in (a `JMP`, a branch, a glide, a stack jump) is no call.
- **Shadow stack:** a second stack outside the machine, kept by `StackTracking`. Each `JSR` opens a **frame** (call site, entry, expected return), kept by `SP` before the call. Frames at the same `SP` pile up, the newest on top: a routine may have taken its return address off the stack, into zero page, and call something meanwhile. Each `RTS` closes the top frame at the `SP` it returns to. **Outcomes:** matched (returned where expected), redirected (returned elsewhere: after bytes the routine read after its `JSR`, or to a rewritten return address), unmatched (no frame there: bytes pushed by hand, e.g. `PHA`/`PHA`/`RTS`), abandoned (a frame that can never return), open (still open when the run stopped). A tail call is matched: it shows as a frame closed in another routine's code.
- **Stack jump:** an unmatched `RTS` whose target lies directly after no `JSR` of the run: a jump made with `RTS`, e.g. a dispatch through a table (`stack_jumps()`). Its target is a routine's entry.
- **Dispatch by `RTS`:** one use of a stack jump: pushing an address minus one taken from a table onto the stack and doing `RTS` to choose among several routines (`MOVE_GUARD`, `6e96`).
- **Payload:** bytes directly after a `JSR` that the callee reads as data and returns past (`LOAD_SOUND_DATA`, `PUT_STRING`).
- **Return after a payload:** a redirected `RTS` that closes a `JSR`'s frame but lands further after the `JSR` than 3 bytes, because the routine read the inline bytes after the `JSR` (`LOAD_SOUND_DATA`, `PUT_STRING`). `redirected_returns()` turns it into a call fall-through edge in the caller.
- **Tail call:** a routine ends with `JMP X` (or a branch to `X`) instead of `JSR X` followed by `RTS`, so that `X`'s own `RTS` returns straight to the first routine's caller.
- **Xekri's subroutine concept:** how Xekri's source (`main.nw`) cuts code into static units, each from his `SUBROUTINE` mark to its last instruction, holding its code whether that code ran or not. One such unit is a **Xekri subroutine**; in the plural, prose says "Xekri's subroutines".
- **Unit:** what the answer key (`lr_answer_key.csv`) assigns a block to for grading (`make lr-grade`): a Xekri subroutine, or an **unmarked unit** (an `ORG` chunk of Xekri's source that starts with a global code label but has no `SUBROUTINE` mark: `MAIN`, `INIT_GAME_DATA`, `LONG_DELAY`).
- **Stretch:** a planned persistent object collecting what is understood about code, rather than a presentation setting or the structure of one run. See `GOALS.md`, "Routines as stretches".

---

## 5. Memory Access & Cross Reference

- **Kind:** why the CPU touched a byte, named after `Memory`'s hook lists: `read_immediate`, `read_pointer`, `read_data`, `write_data`, and the ones the cross reference doesn't count (`read_opcode`, `read_operand`, `read_stack`, `read_vector`, `write_stack`).
- **Target:** the address an operand names: `$1a85` in `LDA $1a85,Y`, the pointer `$1b` in `STA ($1b),Y`, a branch's target. `edit()`'s Operand field labels it, as the bytes stand after the run; the cross reference records it as it stood when the instruction ran, so a target the program wrote itself shows once per value it had. An immediate has none: it names no address.
- **Effective address:** the byte an access actually touches: the target plus the index, or, through a pointer, the pointer's value plus `Y`. `LDA tbl,X` has one target and as many effective addresses as `X` had values.
- **Base address:** the address an index is added to: the target for `abs,X`, `abs,Y`, `zp,X` and `zp,Y`, the pointer's value for `(zp),Y`. The effective address is the base address plus the index. `LDA tbl,X` has one base address; `STA (PTR1),Y` has as many as the pointer had values, e.g. one per row of a grid. With index 0, the effective address is the base address.
- **Index:** the value of `X` or `Y` that an addressing mode adds: for `abs,X`, `zp,X`, `abs,Y` and `zp,Y` to the target, for `(zp,X)` to find the pointer, for `(zp),Y` to the pointer's value. Also the `,X` part of an operand, as in the editor's syntax colors.
- **Cross reference (xref):** a link from an instruction to a byte it touched, with the kind of access. `CrossReferencing` counts them per instruction, kind, target and effective address, with the indexes, values and old values seen, into `lr_xrefs.csv`. "Xref" is the short form, for the prompt; "cross reference" the long one, for prose and the class.
