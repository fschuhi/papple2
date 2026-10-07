# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.


---

## Scratchpad (waiting to be assigned to sections)

- ~~I need some support for massaging labels and comments in different Terminal sessions. Any `listing` or `edit` (and potentially also other shell methods) should read the annotations before executing the main functionality. Otherwise something I enter in another Terminal session is not picked up, even though it is in the `annotations.json`.~~ *(Done 2026-10-07: every change in `Annotations` reads the file first, and every view reads it before it shows. In `edit()`, Enter+Enter on any line picks up the other session.)*
- ~~Should be possible in the `edit()` to also edit zero page labels.~~ *(Done 2026-10-07: the Operand field in `edit()` labels the address an operand names, zero page included.)*
- ~~Save last output to clipboard (for e.g. listings).~~ *(Done 2026-10-07: the commands that show something return it as text, shown as `Out[n]`; `clip()` copies the last one, `clip(Out[12])` an older one.)*
- Labels for `#$0b`. _Low priority (2026-10-07)._ A constant is a value, not an address, so the dossier needs a new kind of entry.

## Routine structure (in this order)

- _Parked (2026-10-07): the new edges made the picture harder to read; more Graphviz doesn't pay off now._ The routine graph is complete but hard to read (2026-10-07). Directions: the neighbourhood of one routine, `show_routine_graph("lookup_hgr")` with only its callers and callees (the cheapest); a dispatcher's fan-out merged into one arrow ("`RTS` to 14 routines"); the layout, left to right, or boxes grouped by address range.
- ~~The routine graph: every routine of the run (about 70) in one `graphviz` picture, with `JSR` edges and the dossier's labels on the nodes. Routines only; loops stay in `listing()` and `edit()`. Made before the next item, so that the picture shows what the shadow stack changes.~~ *(Done 2026-10-06: `show_routine_graph()`, `JSR` edges only, SVG in `tmp/`. Shared code gives each routine holding it the site's whole count.)*
- ~~The shadow stack goes into the structure detection: tail calls and stack jumps (`PHA`/`PHA`/`RTS`) become edges of their own kind, each in its own colour in the routine graph. Why: `build_graph()` keeps the edge of a `JMP` but drops the one of an `RTS`, so a tail call pulls the callee's blocks into the caller's graph, and a stack jump leaves its target unreached. Before that: `stack_tracking.py` rewritten in plain style and read together, line by line. Not recorded yet: `TXS`, direct writes to page 1, `RTI` and `BRK`; today only their effect shows (frames abandoned or redirected), not the instruction that caused it.~~ *(Done 2026-10-07: a routine ends where another begins; `routine_exits()` and `stack_jumps()` give the cut edges and the stack jumps their kinds, drawn in the routine graph. The rest moved to the next item.)*
- `stack_tracking.py` rewritten in plain style and read together, line by line. Not recorded yet: `TXS`, direct writes to page 1, `RTI` and `BRK`; today only their effect shows (frames abandoned or redirected), not the instruction that caused it.
- Chromatix's four subroutine classes (sorted by what a routine does to the stack between entry and `RTS`) need to be implemented; they have surfaced several times now.
- Cases the new structure must explain, from `lr_returns.csv`:
  - `lr_returns.csv`: most unmatched rows pair with an abandoned frame of the same count, whose expected return is the unmatched row's target (frame `88cb -> 88d7` abandoned 169 times; unmatched returns to `88ce` 86 + 23 + 60 times; likewise `6c9b -> 6cdb` and `75cd`, `74ec -> 887c` and `8889`). _Needs investigation:_ does Lode Runner move its return addresses there, or is `_abandon` too eager? Read `88d7` first. *(2026-10-07: `stack_jumps()` leaves these out, since `88ce` lies right behind the `JSR` at `88cb`; the question stays open.)*
  - ~~`lr_returns.csv` records no `JMP`: a tail call shows only by inference, an entry whose return site lies in another routine's code (`four_blocks`, `8a69`, returning at `8b0b` in `8af6`). If needed, record a `JMP` into a routine's entry while a frame is open.~~ *(Done 2026-10-07: a `JMP` into another routine's entry is an exit of kind `jmp`, found from the transitions.)*
  - ~~`lr_returns.csv`: the `RTS` at `7b23` goes to fourteen places, most of them once: a dispatcher, the first candidate for a stack jump table.~~ *(Done 2026-10-07: its targets are routines now, reached by stack jumps, the purple `RTS` arrows.)*
  - ~~The 65 pieces in no routine, 61 of them in `$6F26`-`$70D5`: check whether the "RTS targets not behind an observed JSR" lines of `make lr-tiles` point there (a jump table?). *(2026-10-04: `lr_returns.csv` has unmatched returns into that range, from the `RTS`s at `6e96` and `74f6`, to `6f33`, `6f39`, `6f66`, `6fbc`, `6ff4`, `7041`, `7047`, `7081`, `70d2`.)*~~ *(Done 2026-10-07: with the stack jumps, every piece that ran belongs to a routine.)*
- Ways of looking at routines, all computable from the split reports: the call graph (who calls whom, how often); a profile per routine (pieces, calls, instructions run in it); leaf routines (call nothing; first candidates for names); kinds of entry (`JSR` target, `RTS`-trick target, tail-call `JMP`); blocks shared by several routines; blocks no entry reaches. Search terms: call graph recovery, function boundary detection.
- Region recovery: if/else and loops into structured form. Search terms: structural analysis Sharir, interval analysis Allen Cocke, Yakdan et al. No More Gotos. The step after tail calls and stack jumps.

## Reading at the prompt

- _Parked (2026-10-07), until a view needs it:_ `routine_of(address)`, the routine or routines any address lies in, not only an entry (shared code lies in several), and `meaning_of(address)`, its label or else those routines, next to bare addresses in a view such as `print_edges()` or `print_loops()`. `routine_at()` only accepts entries; `show_callers()` already names the routines of each site.
- Labels wherever an address is printed.
- _Important:_ `show_loops(entry)` and `show_edges(entry)` on the current run, like `show_blocks(entry)`; `print_loops()` and `print_edges()` take the objects.
- _Orientation (2026-10-04):_ `show_returns(entry)`, the rows of `lr_returns.csv` for one routine at the prompt, with the dossier's labels. Reports carry no labels: they are rebuilt by every run, while the dossier changes by hand.
- Views beyond an address range: a loop (by its header: its member blocks) and a routine (by its entry: the blocks of its graph in address order, with gaps between them). *(Partly done 2026-10-04: `listing(entry)` lists a routine from its lowest block to its highest, gaps included, unmarked. Open: a loop's view, and marking the gaps.)*
- Bytes between blocks never ran, but `dis()` decodes them anyway, e.g. `LOAD_LEVEL`'s `629a` (`LDA #$00`, jumped over in the whole run) and `62b5`-`62c2`. Mark them, or show them as a gap. Where they are data, the decoding may not line up with the real instructions.
- Shelved (2026-10-02): counts next to the listing, in two columns right of the instructions: the runs on a block's first line, how often the arrow was taken on its leap. Not needed for the walkthrough, where every count is known. The first real case: `628a BPL $6292` in `LOAD_LEVEL` always jumps (224 of 224, since `AND #$0f` clears bit 7), which an arrow cannot show. Build it when reading a real routine shows the need.
- Colored ranges, in the hexdump, `listing()` and `edit()`: `color("sprites", start, end, "red")` sets a range by a string ID (again with the same ID: replaced), `colors()` lists them, `uncolor("sprites")` removes one. Start and end as addresses or labels, kept as addresses; colors by name (`red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`). A byte in two or more ranges gets the one overlap color, `overlap_color("magenta")`. Kept in `annotations.json`, a third section. In the listing, the hex bytes are colored byte by byte. Steps: the dossier, the hexdump, `listing()`, `edit()`; in the editor, widths must be counted without the color codes.
- _Parked (2026-10-07):_ the hexdump in Apple screen codes, for text a game keeps that way: `$00`-`$3F` inverse, `$40`-`$7F` flashing, `$80`-`$FF` normal, e.g. `hexdump(start, end, text="screen")`. Until such text turns up.
- _Helpful:_ a `workbench()` overview at the prompt: one command that lists everything `%run` leaves there, by kind. *(Partly done 2026-10-04: the table in `README.md`, "At the prompt". Open: the command, which could read each name's kind from where it comes from: `shell.py` = command, the experiment = its own, an object of the run = machinery.)*
- A whole-run view at the prompt: `show_tiles(tiles)`, every basic block with its runs, with the pieces in no routine marked; designed together with `show_unreached()`. *(Partly done 2026-10-03: `show_routines()` lists every routine of the run, `show_blocks(entry)` shows one, both with the dossier's labels. Open: `show_tiles()`, `show_unreached()`.)*
- _Next (2026-10-07):_ the listing editor's instruction column follows its widest instruction, as the label column does; since the Operand field, labels in operands overflow its 16 characters. Listing editor, open: how labels in operands, and long labels in general, fit the horizontal layout; more will break it. `termios` is macOS/Linux only, so not in the Windows VM. Its docstrings and comments are German with umlauts; English and ASCII, like the rest of the project. *(Partly done 2026-10-05: English and ASCII. Open: the layout.)*

## Who writes where

- `run()` builds every instrumentation from the CPU (`instrumentation(emulator.cpu)`), while `attach()` sorts its hooks into `Memory` or `CPU` by name. Whether an instrumentation with memory hooks gets at the memory through the CPU (`conftest.py` builds `CPU(memory, ...)`) is unchecked; the shadow stack did not tell, since `StackTracking` needs no memory hooks.
- Who writes the relocated code: an `after_write_data` hook on `$6252` names the instruction (probably the loop at `$2821`, which runs 33,024 times, the size of the file).
- _Priority 2 among the tools, a big theme:_ the HGR "ray". Watch the loads and stores into a range like HGR1 (`$2000`-`$3FFF`) or HGR2 (`$4000`-`$5FFF`), then see which tiles and larger structures (routines, loops) the ray falls on. An instrumentation with hooks, or built from other reports; its report joins the tiling's. First slice: tag the tiles which write to HGR, from an `after_write_data` hook.
- Assume a memory range looks like sprite data (from hex and binary viewing). When a single byte in HGR1 changes: which `STA` wrote it, which tiles led there, and did the written value originate in the suspected sprite range?
- Notes for the HGR work (from the workbench ideas of 2026-10-01, section 10):
  - Tag each container with "writes to HGR" (`$2000`-`$5FFF`), from an `after_write_data` hook. Then work upwards from such a container to the `JSR` in the routine above it; a breakpoint there shows which call puts a sprite on the screen while the level is drawn. (In `LOAD_LEVEL` the `STA (PTR1),Y` at `$629c` writes into the level's sprite table, not to the screen; the drawing happens in the routine it calls at `$63b3`.)
  - Sprite tables on the 6502 are almost always split into lo and hi bytes, so containers that load with indirect addressing and store to HGR with indirect addressing should be easy to find.
- HGR1/HGR2 switchable in the `pygame` window. The level is probably built sprite by sprite on HGR2.

## Explaining `papple2`

- ~~The inner loop of the new design as a page, the sibling of `docs/diagrams/inner-loop.html`: the same seven instructions, each call with the hook list that hears it. Built together, one instruction first. It then replaces the sketch in `docs/instrumentation-design.md`, section 2.~~ *(Done 2026-10-06: `docs/diagrams/inner-loop-hooks.html`, all seven instructions; section 2 now points to it.)*
- The walkthrough as an experiment with a recipe: a program setup for its twenty bytes in `papple2.programs`, then `run()` and `tiling_reports()` like Lode Runner. Today `scripts/walkthrough.py` still wires its run by hand.
- The walkthrough gets its own dossier (`dossiers/walkthrough/`) instead of `NAMES`. Tests: the fixture opens a dossier in `tmp_path`, seeded with the four names, and a chapter shows that labels given in one session are there in the next.
- The walkthrough program exists three times: `scripts/walkthrough.py` (`PROGRAM`), `tests/conftest.py` (`WALKTHROUGH_PROGRAM`) and `tests/test_tiling.py` (`PROGRAM`); its names twice (`NAMES`, `WALKTHROUGH_NAMES`). Tests can't import from `scripts/`, so a shared copy would live in the package.

## Code tidying

- Assembler: a program whose first instruction has no operand (`INX`, `NOP`, `PHA`, ...) fails with `UnboundLocalError`. In `assemble()`, `operand` is only set on lines that have one, but `find_info(mnemonic, addressmode, operand)` always passes it; later lines reuse the previous line's value by accident. Reset `operand` at the start of each line, and add a test. Found 2026-09-28; hit again 2026-10-04 by a test's stand-in program (`ENDLESS_PROGRAM` in `tests/test_shell.py` works around it).
- The indexed modes (`abs,X`, `abs,Y`, `(zp),Y`) don't wrap at `$FFFF` as the 6502 does.
- `read_word_bug`: the three indirect modes in `core/cpu.py` call `memory.read_pointer_word()` directly; `CPU.read_word_bug()` goes; `Memory.read_word_bug()` has already gone. No change in behaviour: the page wrap lives in `read_pointer_word()`.
- A pass over all docstrings and comments, file by file: a docstring says what the thing is for and how to call it; no history, no dates. Known stale: the stand-ins' comments that mention "the CPU's write hook" (`RwtsHook` in `src/papple2/programs/lode_runner.py`, `MliHook` in `scripts/boot_bandits.py`), and the comment above `WINDOW_POLL_INTERVAL` in `core/emulator.py`, which leaves out the breakpoints.
- `from papple2.workbench.shell import *` imports the module's state (`routines`, `annotations`, ...) as copies of their values at import time, which then go stale. An `__all__` in `shell.py` listing only the commands would prevent it.
- `shell.py` holds helpers next to the commands (`write_report()`, `current_annotations()`, `address_of()`, `current_routines()`, `routine_at()`, `loop_ids()`, `innermost_loop()`, `assign_lanes()`, `draw_gutter()`, `arrows_in()`). Mark them as not part of the contract (an underscore, or a module of their own).
- `shell.py`'s `loop_ids()` and `innermost_loop()` repeat two pieces of `write_loop_reports()`. If they drift apart, the ids at the prompt and in the reports differ; a shared helper would prevent it.
- Loop reports: a test for a loop with two back edges (the parallel lists of sources and counts), when we look at the reports together.
- Describe the interfaces with `typing.Protocol`: first the hooks, then the breakpoints with them. Today the hook lists and `Emulator.breakpoints` are typed as `Callable`s, and `attach()`/`add_breakpoint()` rely on method names (duck typing).
- `tests/test_assembler.py`: `test_8bit_bitcount` runs its routine but asserts nothing.
- Python 3.14: `pygame-ce` 2.5.8 works there (imports with `mixer` and `font` on 3.14.5, checked 2026-09-24). Remaining: run `make test` under 3.14, then update the Python-version notes in `README.md` and the `Makefile`.
- Pin `pysm`'s version in `requirements.txt` (nothing is pinned today; `pip show pysm` shows the installed one). `pysm` first, because the emulator's state machine rests on it; decide whether to pin the others too.
