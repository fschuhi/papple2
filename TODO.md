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

- Labels for `#$0b`. _Low priority (2026-10-07)._ A constant is a value, not an address, so the dossier needs a new kind of entry.
- Directions noticed after the `Session` (2026-10-10), none urgent:
  - Analysis on plain data types. `basic_blocks_analysis.py` works on `SplitTile`, `SplitTransition` and `ReturnRow`, and the CSV files only turn files into those. A later `TilingManager` held by the `Session` could hand over the same types from memory, with the files as one output. The rule "analysis works on reports" would become "analysis works on plain data types". It needs a test that both paths give the same result.
  - Names for what instrumentations write. Tiles, transitions and returns are recordings of one run, as counts, not reports; the loop CSVs and `lr_overview.txt` are reports. The word: `profile`; "trace" stays free for something with an order (e.g. a future `lr_frames.csv`). When it is applied, look at the file names and places together: the `lr_` prefix names Lode Runner, but `Tiling` writes it for any program (the walkthrough's files are `lr_unbroken_tiles.csv`), and `docs/reports/<experiment>/` sits apart from `dossiers/<program>/`. Until then, `lr_` stays. _Needs a discussion first._
  - `set_current_run()` leaves `run_program` and `run_instrumentations` as they were. It matters only when a run is set from reports made elsewhere.
  - A `pysm` state machine for the `Session`'s state (no run, run made, routines built), much later. A computed `state` property would come first.

## Routine structure (in this order)

- _Parked (2026-10-07): the new edges made the picture harder to read; more Graphviz doesn't pay off now._ The routine graph is complete but hard to read (2026-10-07). Directions: the neighbourhood of one routine, `show_routine_graph("lookup_hgr")` with only its callers and callees (the cheapest); a dispatcher's fan-out merged into one arrow ("`RTS` to 14 routines"); the layout, left to right, or boxes grouped by address range.
- `stack_tracking.py` rewritten in plain style and read together, line by line. Not recorded yet: `TXS`, direct writes to page 1, `RTI` and `BRK`; today only their effect shows (frames abandoned or redirected), not the instruction that caused it.
- Chromatix's four subroutine classes (sorted by what a routine does to the stack between entry and `RTS`) need to be implemented; they have surfaced several times now.
- Cases the new structure must explain, from `lr_returns.csv`:
  - `lr_returns.csv`: most unmatched rows pair with an abandoned frame of the same count, whose expected return is the unmatched row's target (frame `88cb -> 88d7` abandoned 169 times; unmatched returns to `88ce` 86 + 23 + 60 times; likewise `6c9b -> 6cdb` and `75cd`, `74ec -> 887c` and `8889`). _Needs investigation:_ does Lode Runner move its return addresses there, or is `_abandon` too eager? Read `88d7` first. *(2026-10-07: `stack_jumps()` leaves these out, since `88ce` lies right behind the `JSR` at `88cb`; the question stays open.)*
- Ways of looking at routines, all computable from the split reports: the call graph (who calls whom, how often); a profile per routine (pieces, calls, instructions run in it); leaf routines (call nothing; first candidates for names); kinds of entry (`JSR` target, `RTS`-trick target, tail-call `JMP`); blocks shared by several routines; blocks no entry reaches. Search terms: call graph recovery, function boundary detection.
- Region recovery: if/else and loops into structured form. Search terms: structural analysis Sharir, interval analysis Allen Cocke, Yakdan et al. No More Gotos. The step after tail calls and stack jumps.

## Reading at the prompt

- _Parked (2026-10-07), until a view needs it:_ `routine_of(address)`, the routine or routines any address lies in, not only an entry (shared code lies in several), and `meaning_of(address)`, its label or else those routines, next to bare addresses in a view such as `print_edges()` or `print_loops()`. `routine_at()` only accepts entries; `show_callers()` already names the routines of each site.
- Labels wherever an address is printed.
- _Important:_ `show_loops(entry)` and `show_edges(entry)` on the current run, like `show_blocks(entry)`; `print_loops()` and `print_edges()` take the objects.
- _Orientation (2026-10-04):_ `show_returns(entry)`, the rows of `lr_returns.csv` for one routine at the prompt, with the dossier's labels. Reports carry no labels: they are rebuilt by every run, while the dossier changes by hand.
- Views beyond an address range: a loop (by its header: its member blocks) and a routine (by its entry: the blocks of its graph in address order, with gaps between them). *(Partly done 2026-10-04: `listing(entry)` lists a routine from its lowest block to its highest, gaps included, unmarked. Open: a loop's view, and marking the gaps.)*
- Shelved (2026-10-02): counts next to the listing, in two columns right of the instructions: the runs on a block's first line, how often the arrow was taken on its leap. Not needed for the walkthrough, where every count is known. The first real case: `628a BPL $6292` in `LOAD_LEVEL` always jumps (224 of 224, since `AND #$0f` clears bit 7), which an arrow cannot show. Build it when reading a real routine shows the need.
- _Parked (2026-10-07):_ the hexdump in Apple screen codes, for text a game keeps that way: `$00`-`$3F` inverse, `$40`-`$7F` flashing, `$80`-`$FF` normal, e.g. `hexdump(start, end, text="screen")`. Until such text turns up.
- _Helpful:_ a `workbench()` overview at the prompt: one command that lists everything `%run` leaves there, by kind. *(Partly done 2026-10-04: the table in `README.md`, "At the prompt". Open: the command, which could read each name's kind from where it comes from: `shell.py` = command, the experiment = its own, an object of the run = machinery.)*
- A whole-run view at the prompt: `show_tiles(tiles)`, every basic block with its runs, with the pieces in no routine marked; designed together with `show_unreached()`. *(Partly done 2026-10-03: `show_routines()` lists every routine of the run, `show_blocks(entry)` shows one, both with the dossier's labels. Open: `show_tiles()`, `show_unreached()`.)*

## Coloring and memory map

- Operand-target colors, next: color the operand's referenced address independently of the instruction's location. Start with `ListingRow.target`: the table base in `LDA table,Y`, the pointer in `STA (pointer),Y`, the destination in a branch or direct call. Keep brackets and indexes intact, handle shortened local labels and `label+N`, and leave immediates alone. In `edit()`, color the referenced operand without coloring the whole line; preserve selection background, field positioning, truncation and clipboard text. In `listing()`, decide target-color precedence over the location color already covering the operand. Resolve that presentation rule before implementation. Runtime effective addresses are separate instrumentation work, not inferred from the static operand.
- Graphviz node colors: use the same whole-routine range lookup as breadcrumbs, with dossier definitions reloaded before drawing. First choose the presentation together: colored border, pale fill, label color, or a combination. Existing edge colors describe transfer kinds and must remain distinct from node classification. No graph-layout refactor in this step.
- Static memory map for the presentation on Sunday, 2026-10-11: show dossier knowledge about location across the whole 64 KB, independently of a run. First design a terminal rectangle using spaces with colored backgrounds, address labels and a legend; a 16 x 16 whole-memory grid would represent 256 bytes per cell, while a 16 x 16 page view would represent one byte per cell. Define the displayed address bounds separately from grid dimensions; terminal starting position is a rendering concern. Use the same color definitions and byte lookup as the other views.
- Map aggregation needs a decision before implementation. `color_for_range()` is containment lookup for a routine title, not a summary of all bytes in a map cell. Proposed summary: no classified bytes means uncolored; classified bytes with one shade retain it; different shades produce a defined mix color. Unclassified bytes do not dilute the assigned shade, and RGB averaging is not the proposed default. Distinguish overlapping classifications at one byte from separate differently colored bytes inside a cell. Decide whether partial coverage needs a visible indication and whether the mix color remains the existing fixed magenta.
- Hexdump colors remain later work: color individual bytes through the shared lookup, not by the line's first address. Do not require the hexdump to be built before the map.
- No general highlighting framework, syntax coloring or per-line editor location marker in the agreed first scope. Syntax coloring may follow later; keep it distinct from location and referenced-address colors.

## Listing editor

- `i` and `m`: the bar to the previous and the next row with a label, within the routine shown. Movements like the arrow keys, not steps: Backspace does not undo them. (`i`/`m`, not `j`/`k`: my Karabiner Elements cross.)
- Ctrl-based paging bindings: PageUp/PageDown handlers already exist, but Terminal.app keeps fn+Up/Down for its own scrolling and Option+Up/Down arrives as plain arrows. Choose Ctrl-based keys that reach the application and bind them to the existing page movements; I will do the Karabiner Elements mapping myself. Paging and `i`/`m` solve different navigation needs; neither replaces the other.
- Go To beyond routine entries, _higher priority (2026-10-09)_: e.g. `game_start` at `6056`, reached only by `JMP`. See also the item further below.
- A key to open the gaps that never ran, in place. _Low priority._
- Offset labels for data words: `LDA zp_hgr1_row_ptr+1` instead of a label of its own for the high byte (`zp_hgr1_row_ptr_hi`). Today `label+N` is shown only into instructions that ran, since a data byte read as an opcode would make up an instruction.
- `arrive()` in the editor calls `row_of()` twice for the same address; once is enough.
- The picker: typing to narrow its list, once 68 routines get long to scroll through.
- Go To beyond routine entries: local labels (`.loop1`) need `routine_of()`, see "Reading at the prompt"; data labels such as `hgr_rows_lo` need a hexdump view in the editor, since the disassembler would read a table as code.
- Folding labelled loops, after reading with the editor for a while: see `docs/editor-ideas.md`, "Folding". _Needs investigation first:_ does each of Lode Runner's loops span a contiguous range of rows in the listing?
- The editor's memory per routine (window and bar, `editor_views` in the `Session`) lasts as long as the run. Later, perhaps, in the dossier. _Low priority._
- `RTS`: Enter on it offers the targets the shadow stack recorded (`docs/editor-ideas.md`, "RTS Resolution"), in the picker.
- _Parked (2026-10-08):_ moving the bar down looks less smooth than moving it up. The terminal writes top to bottom: on Down, the old bar row is cleared before the new one is painted, so for a moment there is no bar.
- `listing()` shows a long comment whole, wrapped onto continuation rows. Their gutter continues only the arrows that pass the row; `draw_gutter()` knows which. Needs tests of its own.

## Ranges and stretches

- Code that ran and was overwritten afterwards, e.g. `JMP $2800` at `0800` and the relocation loop at `2800`-`2832`, which read `00` and `80` after the run. A listing reads memory after the run (`docs/decisions.md`), so it shows what was written there later. Option B to `hide`: `Tiling` keeps the bytes of each instruction as they ran, and the listing shows those. Harder with self-modifying code, whose bytes change between runs of the same instruction.

## Who writes where

- Who overwrote Lode Runner's start-up code (`0800`-`0803`, `2800`-`2832`, parts of `5f32`-`5fa6`) after it ran: a case for `Watching`. A guess, unchecked: the loop at `5f4b`, which runs 32,768 times.

- `run()` builds every instrumentation from the CPU (`instrumentation(emulator.cpu)`), while `attach()` sorts its hooks into `Memory` or `CPU` by name. Whether an instrumentation with memory hooks gets at the memory through the CPU (`conftest.py` builds `CPU(memory, ...)`) is unchecked; the shadow stack did not tell, since `StackTracking` needs no memory hooks.
- Who writes the relocated code: an `after_write_data` hook on `$6252` names the instruction (probably the loop at `$2821`, which runs 33,024 times, the size of the file).
- _Priority 2 among the tools, a big theme:_ the HGR "ray". Watch the loads and stores into a range like HGR1 (`$2000`-`$3FFF`) or HGR2 (`$4000`-`$5FFF`), then see which tiles and larger structures (routines, loops) the ray falls on. An instrumentation with hooks, or built from other reports; its report joins the tiling's. First slice: tag the tiles which write to HGR, from an `after_write_data` hook.
- The HGR ray as shaped on 2026-10-08, for the score: watch the score's row on the screen, find who wrote there (drawing and erasing, two ways in), walk up to the routine that knows the score, then watch the score's bytes: the routine that reads and writes them updates the score. Not taint (forward from a source), but write attribution (backward from the screen); in other tools "find out what writes to this address" (Cheat Engine) or write watchpoints with a call stack (Mesen, VICE, MAME). Steps:
  - `Watching`: an instrumentation for several named ranges, each watched for reads, writes or both; per watch, kind and instruction it counts the accesses and keeps the first and last `instruction_count`. Given to `run()` with `functools.partial(Watching, ...)`, so `run()` stays as it is. Colors come from the dossier's `colors.json`, not from the watch; the initial shared color lookup is now built.
  - A new experiment (`lr_score.py`, or a general one), and `show_watches()`: who wrote, with routine and labels.
  - `StackTracking` writes `lr_frames.csv`: per frame its call site, entry, and when it opened and closed. The backtrace of an access is the frames open at its `instruction_count`. No live access between instrumentations: their reports are joined afterwards, and asking for a backtrace without the frames report stops with a message.
  - The paths into a watched range form a tree, rooted at the writing instruction; in the editor, they filter the callers in the picker.
  - Known: during a memory hook, `cpu.last_PC` is the address of the instruction running (`do_next_step()` sets it before the opcode is read). The score uses `SED`. In the 4,000,000 instructions of the attract play, a gold piece is taken shortly before the end, so the score changes in the run.
- Actual store destinations can feed later coloring: `Memory.after_write_data` receives `(address, value, old_value)`, while `cpu.last_PC` identifies the executing instruction. This can connect code to the colors of the addresses it actually wrote. It is not part of the static operand-coloring step; design the report and its visible use before implementing instrumentation.
- Assume a memory range looks like sprite data (from hex and binary viewing). When a single byte in HGR1 changes: which `STA` wrote it, which tiles led there, and did the written value originate in the suspected sprite range?
- Notes for the HGR work (from the workbench ideas of 2026-10-01, section 10):
  - Tag each container with "writes to HGR" (`$2000`-`$5FFF`), from an `after_write_data` hook. Then work upwards from such a container to the `JSR` in the routine above it; a breakpoint there shows which call puts a sprite on the screen while the level is drawn. (In `LOAD_LEVEL` the `STA (PTR1),Y` at `$629c` writes into the level's sprite table, not to the screen; the drawing happens in the routine it calls at `$63b3`.)
  - Sprite tables on the 6502 are almost always split into lo and hi bytes, so containers that load with indirect addressing and store to HGR with indirect addressing should be easy to find.
- HGR1/HGR2 switchable in the `pygame` window. The level is probably built sprite by sprite on HGR2.

## Explaining `papple2`

- Architecture diagrams, made by a fresh session from the code and the artefacts around it (the packages and their imports, the pipeline from run to reports to prompt, the `Session` and its commands, the dossier), not from memory. For the presentation on Monday 2026-10-12, and as reference points when going into the code. Format: leaning to one or a few PDFs, something to take home, with the diagrams drawn as SVG; Mermaid in the docs and in Obsidian is the alternative for slides. First decide with me which diagrams.
- The walkthrough as an experiment with a recipe: a program setup for its twenty bytes in `papple2.programs`, then `run()` and `tiling_reports()` like Lode Runner. Today `scripts/walkthrough.py` still wires its run by hand.
- The walkthrough gets its own dossier (`dossiers/walkthrough/`) instead of `NAMES`. Tests: the fixture opens a dossier in `tmp_path`, seeded with the four names, and a chapter shows that labels given in one session are there in the next.
- The walkthrough program exists three times: `scripts/walkthrough.py` (`PROGRAM`), `tests/conftest.py` (`WALKTHROUGH_PROGRAM`) and `tests/test_tiling.py` (`PROGRAM`); its names twice (`NAMES`, `WALKTHROUGH_NAMES`). Tests can't import from `scripts/`, so a shared copy would live in the package.

## Code tidying

- Assembler: a program whose first instruction has no operand (`INX`, `NOP`, `PHA`, ...) fails with `UnboundLocalError`. In `assemble()`, `operand` is only set on lines that have one, but `find_info(mnemonic, addressmode, operand)` always passes it; later lines reuse the previous line's value by accident. Reset `operand` at the start of each line, and add a test. Found 2026-09-28; hit again 2026-10-04 by a test's stand-in program (`ENDLESS_PROGRAM` in `tests/test_shell.py` works around it).
- The indexed modes (`abs,X`, `abs,Y`, `(zp),Y`) don't wrap at `$FFFF` as the 6502 does, in the CPU. (The disassembler wraps since 2026-10-09.)
- `read_word_bug`: the three indirect modes in `core/cpu.py` call `memory.read_pointer_word()` directly; `CPU.read_word_bug()` goes; `Memory.read_word_bug()` has already gone. No change in behaviour: the page wrap lives in `read_pointer_word()`.
- A pass over all docstrings and comments, file by file: a docstring says what the thing is for and how to call it; no history, no dates. Known stale: the stand-ins' comments that mention "the CPU's write hook" (`RwtsHook` in `src/papple2/programs/lode_runner.py`, `MliHook` in `scripts/boot_bandits.py`), and the comment above `WINDOW_POLL_INTERVAL` in `core/emulator.py`, which leaves out the breakpoints.
- `call_sites()` in `shell.py` builds its result with a nested list comprehension; a plain loop would read more easily. Kept for the code review: reading list comprehensions is its first topic.
- ~~`from papple2.workbench.shell import *` imports the module's state (`routines`, `annotations`, ...) as copies of their values at import time, which then go stale. An `__all__` in `shell.py` listing only the commands would prevent it.~~ *(Done 2026-10-10 by the `Session`: `shell.py` no longer holds state under names that `import *` could copy, only `session`, one object that stays current.)*
- The `Session`, step 2 (decide first whether 2a and 2b are one step). `shell.py` still holds helpers next to the commands. **2a:** those that only read state become `Session` methods (`call_sites`, `caller_items`, `listing_range`, `current_listing_rows`, `routine_place`, `save_edit`, ...), so the commands become thin; `test_listing_colors.py` then patches `shell.session.current_listing_rows` instead of `shell.current_listing_rows`. **2b:** those that use no state (`listing_rows`, `ran_parts`, `never_ran`, `ran_in`, `scope_of`, `shorten_locals`, `arrows_in`, `assign_lanes`, `draw_gutter`, `hexdump_rows`, `apple_char`, `routine_graph`, `loop_ids`, `innermost_loop`, `Text`, `returns_text`) move into modules of their own (probably listing, hexdump, routine graph, text), which also takes them out of the contract. `shell.py` re-exports what scripts and tests import: `walkthrough.py`, `test_walkthrough.py` and `lr_overview.py` take functions from `shell`, and `test_hidden_listing.py` uses `shell.Disassembler` in a function annotation, which Python evaluates at import. No new commands, no changed output, the tests keep their assertions.
- `shell.py`'s `loop_ids()` and `innermost_loop()` repeat two pieces of `write_loop_reports()`. If they drift apart, the ids at the prompt and in the reports differ; a shared helper would prevent it.
- Loop reports: a test for a loop with two back edges (the parallel lists of sources and counts), when we look at the reports together.
- Describe the interfaces with `typing.Protocol`: first the hooks, then the breakpoints with them. Today the hook lists and `Emulator.breakpoints` are typed as `Callable`s, and `attach()`/`add_breakpoint()` rely on method names (duck typing).
- `tests/test_assembler.py`: `test_8bit_bitcount` runs its routine but asserts nothing.
- Python 3.14: `pygame-ce` 2.5.8 works there (imports with `mixer` and `font` on 3.14.5, checked 2026-09-24). Remaining: run `make test` under 3.14, then update the Python-version notes in `README.md` and the `Makefile`.
- Pin `pysm`'s version in `requirements.txt` (nothing is pinned today; `pip show pysm` shows the installed one). `pysm` first, because the emulator's state machine rests on it; decide whether to pin the others too.
