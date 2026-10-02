# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## Disassembler for what ran (from 2026-10-02)

- ~~A disassembler for what ran: a block, a loop or a routine in `dasm` style, read from memory after the run.~~ *(Done 2026-10-02, first slice: `dis(emulator, start, end, labels, graph)` in `papple2/workbench/shell.py`. It reads the emulator's memory inside the IPython session (option (a); option (b), a memory image as one more report, stays possible), takes half-open ranges like the blocks, shows names in the operands and in a column of their own (`Labels.label_at()`), and draws the jumps the run took as arrows in a gutter on the left. First real use: `LOAD_LEVEL` with `scripts/lr_basic_blocks_analysis.py`. See `HISTORY.md`.)*
- Uppercase hex: `dis()` follows `address()` and `hexaddr()`, both lowercase today; see the `util.py` item under "Small code steps".
- Twin routines side by side (`8336`/`83a7`, `71a2`/`720c`, ...): two listings next to each other.
- Views beyond an address range: a loop (by its header: its member blocks) and a routine (by its entry: the blocks of its graph in address order, with gaps between them). Today `dis()` takes `start` and `end`, which `show_blocks()` provides.
- Memory after the run shows code as it is at the end: code that ran early and was overwritten later is gone (the relocation routine at `$2800`-`$2831` lies in hi-res page 1), so such blocks disassemble as graphics.
- Bytes between blocks never ran, but `dis()` decodes them anyway, e.g. `LOAD_LEVEL`'s `629a` (`LDA #$00`, jumped over in the whole run) and `62b5`-`62c2`. Mark them, or show them as a gap. Where they are data, the decoding may not line up with the real instructions.
- Arrows only appear when both ends lie in the range. Arrows that leave the range: a marker at the edge, if a real routine needs it.
- Two arrows into one row (two branches to one target) are drawn, but no test covers how that looks.
- Shelved (2026-10-02): counts next to the listing, in two columns right of the instructions: the runs on a block's first line, how often the arrow was taken on its leap. Not needed for the walkthrough, where every count is known. The first real case: `628a BPL $6292` in `LOAD_LEVEL` always jumps (224 of 224, since `AND #$0f` clears bit 7), which an arrow cannot show. Build it when reading a real routine shows the need.

## Experiments 

- The instruction count at which each address first ran: the game's phases.
- Differential maps: a run with and without an action (e.g. a dig), showing only the difference.

## Workbench (from 2026-10-01)

See `docs/workbench-ideas.md`.

- The first slice: a workbench module for IPython that loads `lr_split_tiles.csv` and `lr_split_transitions.csv`; `dis(start, end)` through `disassembler.py`; a session file under git with `name()` and `comment()`; `show()` to open a map in the browser or image viewer. *(Partly done 2026-10-02: `papple2/workbench/shell.py` with `dis()` and `show_blocks()`/`show_edges()`/`show_loops()`; the session holds the run through `%run` of a script that leaves `emulator`, `tiling`, `graph` and `loops` in the namespace. Open: `name()`, `comment()`, the session file, `show()`.)*
- Names given in IPython must persist: written to a file (JSON or similar) under git, and the file always in sync with the session. `NAMES` in `scripts/walkthrough.py` is the stand-in until then. Part of the session file above.
- ~~Parked step 4a: `scripts/lr_basic_blocks_analysis.py` with a `make` target.~~ *(Done 2026-10-02: `analyse(binary, instructions, entry, folder)` boots, runs `Tiling`, writes the tiling and loop reports into `tmp/lr_basic_blocks_analysis/`, and builds the graph from `--entry` (default `6238`); the binary defaults to `data/bin/LODE_RUNNER.BIN`. `make lr-basic-blocks-analysis`; `%run` leaves the run, `dis()` and the `show_*` functions in the namespace.)*
- Parked step 4b: an integration test that calls `analyse()` and compares all seven reports with goldens in `tests/fixtures/<test name>/`; skips without `LODE_RUNNER.BIN`. Before creating the goldens: two runs must give identical reports. Once the goldens exist, they are the versioned copy of the reports, and `docs/reports/` can go.
- Reports under git: the scripts write into `docs/reports/<script>/` instead of `tmp/`. The runs are deterministic, so a tracked report works almost like a golden, and `git diff` shows every change. _Open:_ slices (one routine, like `docs/reports/load_level/`) next to complete runs, and how slice folders are named; how this relates to the goldens of step 4b; whether all scripts move at once.
- Ways of looking at routines, all computable from the split reports: the call graph (who calls whom, how often); a profile per routine (pieces, calls, instructions run in it); leaf routines (call nothing; first candidates for names); kinds of entry (`JSR` target, `RTS`-trick target, tail-call `JMP`); blocks shared by several routines; blocks no entry reaches. Search terms: call graph recovery, function boundary detection.
- Sharpen "routine = `JSR` target", which jump tables, tail calls and shared code blur: a shadow stack (a hook that tracks every stack operation, including direct writes to page 1) and signatures for jump tables, written as a report the basic blocks analysis reads. `docs/instrumentation-ideas.md`, section 10, has the cases.
- The 65 pieces in no routine, 61 of them in `$6F26`-`$70D5`: check whether the "RTS targets not behind an observed JSR" lines of `make lr-tiles` point there (a jump table?).
- Who writes the relocated code: an `after_write_data` hook on `$6252` names the instruction (probably the loop at `$2821`, which runs 33,024 times, the size of the file).
- Loop reports: a test for a loop with two back edges (the parallel lists of sources and counts), when we look at the reports together.
- ~~`disassembler.py` in `dasm` listing style, with labels and comments.~~ *(Done 2026-10-02 for labels: `Labels.label_at()` fills the label column, and `dis()` shows it. Comments are still open: `comment()` of the IPython slice.)*
- A whole-run view at the prompt: `show_tiles(tiles)`, every basic block with its runs, with the pieces in no routine marked; designed together with `show_unreached()`. Today the whole run is in `lr_split_tiles.csv` and, by routine, in `make lr-overview`.
- `lr_overview.py` takes the reports folder as an optional argument, so it can read `tmp/lr_basic_blocks_analysis/` right after the analysis, without a second run. Today it reads `tmp/lr_tiles/` only.
- `depth` in `lr_loop_members.csv` counts from 1 (inside one loop = 1), `nesting_depth` in `lr_loops.csv` from 0 (outermost = 0). Consistent, but easy to misread; rename one of them.
- `shell.py`'s `loop_ids()` and `innermost_loop()` repeat two pieces of `write_loop_reports()`. If they drift apart, the ids at the prompt and in the reports differ; a shared helper would prevent it.
- An experiment that tags the tiles which write to HGR (`$2000`-`$5FFF`), from an `after_write_data` hook.

## Emulator front end

- HGR1/HGR2 switchable in the `pygame` window. The level is probably built sprite by sprite on HGR2.
- A monitor for a stopped machine, instead of keys as commands: an Apple II-style monitor like AppleWin's, or a socket the event loop listens on.

## Type hints follow-ups

- Annotate the attributes `mypy` can't figure out by itself, e.g. `self.ops_dispatch = [None] * 0x100` in `core/cpu.py` (it concludes the list only ever holds `None`); likewise `CPU.PC`, `CPU.branched`, `Memory.apple2`. PyCharm doesn't mind these, so this only matters if we ever adopt `mypy`.
- Describe the interfaces with `typing.Protocol`: first the hooks, then the breakpoints with them. Today the hook lists and `Emulator.breakpoints` are typed as `Callable`s, and `attach()`/`add_breakpoint()` rely on method names (duck typing).
- Test files: hints are optional there. Decide whether to add them; today they're mixed (some fixtures in `conftest.py` have hints, most local fixtures don't).

## Direction follow-ups (from 2026-09-23)

See `DIRECTION.md` for the context of each item.

- _Needs investigation:_ is there an Apple II tool that saves per-byte code/data marks to a file (like FCEUX's Code/Data Logger), or tracks data provenance? microM8's heat map comes close.
- Robotron leftovers in `papple2` (`make boot-robotron` and its script stay, as decided 2026-09-27): the three tests in `test_emulator_silent.py` that load `ROBOTRON.BIN` -- they could use small assembled programs instead, like the trap tests. The labels, the checkpoint classes, the `$51b6` exemption and the tiles pointer went with the pruning (2026-09-28).
- Research document with glossary (in progress, away from the keyboard): established reverse-engineering concepts, and what the tools for 6502 platforms (NES, C64, Apple II) offer to understand a game. Basis for renaming `papple2`'s concepts, or at least putting them into their proper context.

## Parked decisions

- No speed sweep for `lr_count.py` (2026-10-01): its hot path is three one-line hooks, and the remaining cost is the call from `Memory` into each hook, which sits in `core`.

- The window's hi-res colours ignore the NTSC neighbour rules (a pixel's colour depends on its neighbours), so they can look wrong. `a2-hires-lab` has worked out the rules; use them if accurate colour ever matters.
- `debug/assembler.py` calls `sys.exit(1)` on an error in the source it assembles. Fine for scripts and tests (`pytest` fails just that test), but it would end an interactive session (monitor, notebook) on a typo. Decide with the monitor: keep it, or raise an `AssemblerError` (stops just as fast, but can be caught -- and swallowed).
- Bandits from the `.do` (`Bandits (1982)(Sirius Software)[cr Nameless Cracker - Pirate Treck - Krakowicz][t +1].do`), parked 2026-09-26 in favour of the Total Replay files. What we know: its boot code (`$0801`-`$084C` of track 0 sector 0) is byte-identical to Lode Runner's DOS 3.3 boot sector. On the first entry it expects `$27 = $09` (the ROM's buffer page after loading the sector to `$0800`) and `$2B` = slot times 16; it builds `$C65C` in `$3E`/`$3F` and calls it once per sector with the sector number in `$3D` and the page in `$27`. It loads track 0 top down into `$B600`-`$BFFF` (first page `$B6` at `$08FE`, sector count minus one `$09` at `$08FF`), picking physical sectors from the table at `$084D` (`00 0D 0B 09 07 05 03 01 0E 0C 0A 08 06 04 02 0F`, the DOS 3.3 logical-to-physical order from general knowledge, unconfirmed), then `JMP ($08FD)` goes to `$B700`. Its DOS differs from Lode Runner's: only 7, 10 and 3 of the 16 sectors on tracks 0-2 are identical. The old plan: fake the ROM's boot, a hook at `$C65C` serving physical sectors, then a watch for the modified DOS's disk access. The `.dsk` of the same crack is byte-identical; the `[o]` overdump and the WOZ original are out.

## Environment / packaging housekeeping

- Bring in automated `black` formatting, as in some of my other projects. Decide how it runs: a `make` target, PyCharm on save, or a pre-commit hook. A hook reformats on `git commit` and then stops the commit, so you have to `git add` and commit again; that's the "why do I have to commit twice" effect from other projects. Explain whichever choice plainly. Then reformat the whole codebase in one separate commit, so later diffs show only real changes, and list that commit in `.git-blame-ignore-revs`, so `git blame` looks past it.
- Python 3.14: `pygame-ce` 2.5.8 works there (imports with `mixer` and `font` on 3.14.5, checked 2026-09-24). Remaining: run `make test` under 3.14, then update the Python-version notes in `README.md` and the `Makefile`.
- Pin `pysm`'s version in `requirements.txt` (nothing is pinned today; `pip show pysm` shows the installed one). `pysm` first, because the emulator's state machine rests on it; decide whether to pin the others too.

## Optional coverage

- `tests/test_assembler.py`: `test_8bit_bitcount` runs its routine but asserts nothing.
- `tests/test_assembler.py`: its `compile` helper does what the `assemble` fixture in `conftest.py` does (and shadows Python's built-in `compile`). Use the fixture instead.
- `tests/test_assembler.py`: `dump_state` prints registers, flags and the stack once per instruction when passed as `dump=` to `run_to_RTS`. Use it as the model for a state dump in the new instrumentation (an `after_instruction` hook would be the natural home).

## Performance (parked, 2026-09-23)

Measured with `cProfile` on the headless Lode Runner run (`HISTORY.md` 2026-09-23, at the tag `pre-redesign`). Since the pruning, windowed runs reach about 3.5 times real Apple II speed unthrottled and can be throttled to it (`HISTORY.md` 2026-09-27/28), so this isn't needed today.

- `is_executing()` runs about three times per instruction and asks the `pysm` state machine each time (about 8% headless, measured 2026-09-23). Since 2026-09-28, `executing` mirrors the state from construction on: Running's entry and exit actions set it, `initialize(fire_events_on_init=True)` runs the entry action, and `test_executing_follows_the_state_from_the_start` pins it down. Remaining: `return self.executing` in `is_executing()` -- decide together with the `pysm` discussion.

## Redesign (from 2026-09-28)

The old instrumentation is gone (`HISTORY.md` 2026-09-27/28); the ideas for the new one are in `docs/instrumentation-ideas.md`.

- Optional, once, whenever it is of interest: the total cost of the instrumentation with all lists empty, measured against the commit before the `Memory` hook lists. Not per step (decided 2026-09-29).
- _Needs investigation:_ where the attract play's moves come from. Probably a table the demo code reads instead of the keyboard; `main.nw` may name it. A read hook on the demo code would show which table it reads. The same "script" could drive experiments. The block `main.nw` calls "random init data" (`levels.html`) looks like leftover memory from when the file was saved (loader code calling the ROM and reading the disk, fill patterns, hi-res bytes), not keystrokes.
- Benched (2026-10-01): a detector for self-modifying code (writes into bytes that ran as opcode, operand or immediate). `read_immediate` is in place for it; it comes back with the self-modifying parts of Lode Runner, or with Bandits.

## Documentation pruning (inventory 2026-10-02, decisions open)

- `docs/instrumentation-design.md`: the decisions of 2026-09-29, still the detailed reference for how `core` is instrumented. Outdated: the status line repeats `HISTORY.md`; section 9 lists points since resolved (breakpoints exist since 2026-09-30); section 10's experiments became `TODO.md` items; rule 6 says "experiment" where the workbench says "instrumentation". Sections 3 and 4 are repeated in `README.md` ("Memory access by kind", "Extension points"), so the two can drift. Proposal: keep it as the one detailed reference, and let `README.md` point to it.
- `docs/instrumentation-ideas.md`: the braindump of 2026-09-26 to 28, with sources. Still alive: section 10 (stack specialists: the shadow stack), section 11 (self-modifying code and the oracle), section 16 (annotations, which `name()`/`comment()` will answer). Superseded: section 15 (tiles and stretches), apart from its search terms. Several questions in section 17 are answered. Proposal: keep it as an archive; mark what is answered, delete nothing.
- `docs/instrumentation-map.md` with `docs/diagrams/` (three diagrams): the old code at the tag `pre-redesign`; its job is done, and `git show pre-redesign:docs/instrumentation-map.md` keeps it readable. Proposal: retire it with its diagrams.

## Small code steps

- `lr_count.py` as an instrumentation package, `workbench/counting.py`, the way `lr_tiles.py` became `Tiling`; then maybe `lr_trace_pc.py`. Making the experiments look alike helps the later refactoring.
- `Tiling.write_reports()` takes `rwts_reads`, and its measurements start with "LODE RUNNER TILE MEASUREMENTS": Lode Runner details in a workbench package (kept on purpose on 2026-10-02, "no generalization yet"). The walkthrough passes `rwts_reads=0` and gets the Lode Runner header too.
- The walkthrough program exists three times: `scripts/walkthrough.py` (`PROGRAM`), `tests/conftest.py` (`WALKTHROUGH_PROGRAM`) and `tests/test_tiling.py` (`PROGRAM`); its names twice (`NAMES`, `WALKTHROUGH_NAMES`). Tests can't import from `scripts/`, so a shared copy would live in the package.
- `Labels` doesn't name zero-page operands (the `TODO` in `labels.py`): `INC $10` keeps its address even with a name for `$10`.
- The column names of the split reports are a contract held by no one: `tiling.py` writes them and `basic_blocks_analysis.py` reads them, each as its own strings (only the file names are shared). The integration test (step 4b) would catch a drift.
- `lr_measurements.txt`: the "Split tiles" line always equals the tile count, by construction (`HISTORY.md`, 2026-10-02). Drop it, or count something that varies (the cuts, the glides).
- `split_tiles()` is an analysis by the workbench's own definition (reads tiles, writes new tables), but lives in the instrumentation. Move it only when there is a reason.
- The reports don't say where they come from (binary, instruction count, commit). Harmless with one script; with several, stale reports become a risk. Possibly the job of the "stretch" container (`GOALS.md`, "Strategic questions").
- `basic_blocks_analysis.write_rows()` nearly duplicates `tiling.write_table()`, which prints "measurement records".
- `scripts/lr_tiles.py` reads `emulator.instructions` before `run()`, but `run()` resets it to 0; the delta is right only because nothing ran before.
- Open questions from `briefing.md`: where `LOAD_LEVEL.lst` should live (a grading fixture, but XekriRedmane's work from `a2-lode-runner`); whether the `lr_` prefix stays now that each script has its own folder; how goldens are refreshed when a report changes on purpose; how an analysis package states which instrumentation it needs upstream (for now, the "speaking" import of `tiling`'s file names).

- Assembler: a program whose first instruction has no operand (`INX`, `NOP`, `PHA`, ...) fails with `UnboundLocalError`. In `assemble()`, `operand` is only set on lines that have one, but `find_info(mnemonic, addressmode, operand)` always passes it; later lines reuse the previous line's value by accident. Reset `operand` at the start of each line, and add a test. Found 2026-09-28.
- `util.py`: `hexaddr()` and `hexbyte()` default to lowercase (`lower=True`), but the decision is uppercase with `$` (XekriRedmane's style, used in the CPU status line since 2026-09-28). Flip the defaults, or remove `lower`, so the disassembler, `Labels` and messages follow.
- The stand-ins' comments still say their writes go past "the CPU's write hook", which no longer exists: `RwtsHook`'s docstring in `scripts/boot_lode_runner.py`, `MliHook`'s docstring and the comment in `MliHook.read()` in `scripts/boot_bandits.py`.
- `graphviz` in `requirements.txt` is unused since `tiles.py` went (2026-09-27); remove it.
- `Memory.read_word_bug` is unused since 2026-09-29; `read_pointer_word` took over its logic.
- `CPU.read_word_bug` reads pointers only now, so its name no longer fits.
- The disassembler's `read_byte`/`read_word` (2026-09-29): an underscore, or not.
- The indexed modes (`abs,X`, `abs,Y`, `(zp),Y`) don't wrap at `$FFFF` as the 6502 does.
- `core/emulator.py`: the comment above `WINDOW_POLL_INTERVAL` names only traps and `until` as checked before every instruction; breakpoints are checked there too since 2026-09-30.
- Flattening the kind methods in `Memory`, so they no longer call `read_byte`/`write_byte`. No priority.
