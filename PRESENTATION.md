# Presentation

Scratchpad for walking a friend through papple2: what each slide shows, what I say, and what I show live. Not reference documentation; that stays in `README.md` and `docs/`.

The diagrams live in `docs/diagrams/*.dot`. `make presentation` renders each one to PDF and PNG in `tmp/presentation/`.

Slide layout: the diagram on the left, a smaller pane on the right with bullets or a code snippet. The pipeline is too wide for that; it takes the full width, with the pane below it.

---

## Slides

### 1. The packages (`packages.png`)

**What I say:**

> This is how papple2 is put together: four packages, and who uses whom. An arrow means "imports": the one at the tail uses the one at the head.
>
> At the bottom is `core`, the machine: the 6502, the memory, the Apple II with its display and soft switches, the window, the disk image, and the `Emulator` that runs it all. Below it there is only `util`, a handful of small helpers.
>
> Every arrow points down. The machine knows nothing of the tools around it. That was a decision, not an accident: the tools use the machine, never the other way round.
>
> In the middle are two packages. `debug` is a toolbox around the machine: the disassembler reads it, the stop conditions stop it, the assembler writes programs for it. `programs` knows how to load and start one particular program; today that's Lode Runner.
>
> At the top is the `workbench`, where the reverse engineering happens. It never imports `programs`: you hand it the program when you call `run()`, so the same workbench works for any program with a setup.
>
> Above everything, outside the package, are the scripts: the boot scripts and the experiments.

**Right pane:**

- Every arrow points down
- `core`: the machine, knows no tools
- `debug`: read, stop, write
- `programs`: one setup per program
- `workbench`: run, reports, analysis, commands

**Worth knowing if asked:**
- The assembler has no user inside papple2. Only the tests and `scripts/walkthrough.py` use it, to write small test programs.
- `stop_conditions` is "debug" by location, but it is really about controlling a run; `session.py` uses it for every run.

### 2. Inside the workbench (`workbench.png`)

**What I say:**

> This is the workbench from the inside. The colours are the roles; the title at the bottom uses the same colours.
>
> Read it from the bottom up. In blue, the instrumentations: `tiling` watches the run and records which code ran and where it leapt; `stack_tracking` keeps a second stack beside the real one, to tell real returns from tricks with the stack. Both write reports.
>
> In red, the analysis: `basic_blocks_analysis` reads those reports and finds the routines and loops.
>
> In grey, the state. `session` keeps the state of every step: the reports folder, the dossier, the current run, its routines and run graph, even where the editor was last left. Beside it, the dossier: what we know about the program, in three stores, the labels and comments, the hidden ranges, the colors. They import nothing; they just keep their files.
>
> In green, the commands in `shell`. They are the contract: what I type at the IPython prompt, and what the scripts call. The prompt is one client, the scripts are another. The tests even skip `shell` and talk to the `Session` directly.
>
> In lavender, `listing`: it builds the rows of a listing, which the prompt and the editor both show.
>
> In pink, the listing editor: one screen on all of it.

**Right pane:**

- blue: watch the run, write reports
- red: find routines and loops
- grey: the state, and the dossier on disk
- green: the commands, the contract
- lavender: the rows of a listing
- pink: one screen on it

**Worth knowing if asked:**
- `shell` still reaches past `session` to `basic_blocks_analysis` and `tiling`. Those are helpers kept next to the commands; moving them is Session step 2a in `TODO.md`.
- Headless use, e.g. writing reports for another tool, works today as "`shell` without the prompt".

### 3. Inside the machine (`core.png`)

**What I say:**

> This is the machine. On top, with the thick border, the `Emulator`. It builds everything else, the Apple II and the window, and it runs the loop: before each instruction it checks breakpoints, traps and the stop condition, then the hooks hear every memory access.
>
> Below it, `apple`: the Apple II itself. It builds the display, the speaker, the soft switches, the memory and the CPU. The CPU only knows the memory; the memory knows nothing below it.
>
> The window takes keys in and puts frames out; without a display, a `NoWindow` stands in, and nothing else changes.
>
> Two arrows go the wrong way, the dashed red ones. They aren't imports that run: the memory holds its Apple II, because a write to the screen area has to reach the display, and a write to `$C000-$CFFF` the soft switches. The window holds the emulator for the frame timing.

**Right pane:**

- `emulator`: builds it, runs it
- `apple`: what the Apple II is
- `cpu` -> `memory`, nothing further
- dashed red: references held back up
- pygame: only in `apple` and `window`

**Worth knowing if asked:**
- How a byte reaches the screen: `STA $2000` -> `memory.write_data()` -> `write_byte()` -> `Display.update()` draws into a pygame surface -> every 1000 passes of the loop, `window.present()` flips it onto the screen. Three modules take part; a diagram of its own would help (open).

### 4. One pass of the loop (`run-loop.png`)

**What I say:**

> This is the heartbeat of the machine: one pass of `Emulator.run()`. It goes round millions of times; 4 million for one run of the experiment.
>
> First, in amber, the checks before the instruction. The breakpoints, every one of them asked, so each sees every instruction. Then the trap: if a routine is stood in for at this address, like Lode Runner's disk routine, the trap does its work and says whether it served. Then `until`: should the run stop here?
>
> Any of the three can stop the machine, and they all stop it the same way, through the state machine. With a window, that's a pause, as if I had pressed Ctrl-X. Without a window, the run ends.
>
> Then, in grey, the instruction itself. The opcode is fetched, the operation runs, and every byte it touches goes through a method that says why the CPU touches it: an operand, a pointer, data, the stack. Each passes the access on to the memory, where the soft switches and the screen live, and then calls its hooks, in blue. That's where the instrumentations listen.
>
> And every thousandth pass, the window gets its turn: slow down to the Apple II's pace if asked, read the keys, show the frame.

**Right pane:**

- amber: may I run this instruction?
- grey: run it, byte by byte
- blue: who hears about it
- every 1000th pass: the window
- three ways to stop, one way of stopping

**Worth knowing if asked:**
- Why breakpoints before traps: a breakpoint at a trap's address stops before the trap moves `PC` away.
- Why every 1000th pass: asking pygame for events on every instruction took about a third of the windowed run time (measured 2026-09-23).
- The memory access kinds are named for why the CPU accesses a byte, not where it is: `LDA $0100,X` touches the stack page, but it is a data read.

### 5. The pipeline (`pipeline.png`)

**What I say:**

> This is what happens when I analyse a run, left to right. The arrows are data now, not imports.
>
> One: the session runs the program headless, 4 million instructions in the recipe, with the two instrumentations hooked into the memory accesses.
>
> Two: they write their reports, CSV files in a folder under git.
>
> Three: the analysis reads them back, from the files, not from the instrumentations. That's the point of the design: the reports are the interface. I can read them, another LLM can read them, and a later tool could, too.
>
> Four: the session keeps the result, the routines and the graph of every block that ran. Routines without a name get a label `routine_xxxx` in the dossier.
>
> Five: the commands work on that. `show_routines()`, `listing()`, the editor. And what I learn, labels, comments, goes into the dossier at once.

**Right pane (or below):**

```python
use_reports_folder(REPORTS_FOLDER)
use_dossier(DOSSIER)
run(lode_runner, 4_000_000, Tiling, StackTracking)
tiling_reports()
stack_tracking_reports()
loop_reports(0x0800)
```

The recipe from `scripts/lr_basic_blocks_analysis.py`: the same lines could be typed at the prompt.

### 6. The listing and the editor (`listing.png`)

**What I say:**

> This is how a listing comes about, top to bottom. The arrows are data again, as in the pipeline.
>
> At the top is the dossier: three small files with what I have learned about Lode Runner. The labels and comments, the ranges I have hidden, and the ranges I have colored.
>
> Next to it, the session holds the current run: the memory as the run left it, the graph of every block that ran, and the routines. When I ask for a routine's listing, `listing_range()` turns it into addresses, from its lowest block to its highest.
>
> Then `current_listing_rows()` reads the dossier again, every time, and hands everything to `listing_rows()`, in lavender. It builds the rows in four steps. A hidden range becomes one grey row. Code the run never reached becomes one grey row per gap. The disassembler decodes the rest, with my labels and comments. And the jumps the run actually took become arrows in the gutter.
>
> What comes out is a list of rows, and that is the point of the picture: both views get the very same rows. `listing()` prints them at the prompt, `edit()` shows them in the editor.
>
> Color comes in at exactly two places, the orange arrows. The listing colors each row by its address. The editor colors only the breadcrumbs, the routines I followed into. That is where syntax coloring will attach later.
>
> And the way back. When I change a label in the editor, `save_edit()` writes it into the dossier at once, and the rows are loaded again, so the new label shows everywhere it is used. The same goes for `label()` or `hide()` at the prompt. Nothing I learn is kept only in memory.

**Right pane:**

- dossier: what I know, in three files
- session: the run, and the range
- `listing.py`: the rows, in four steps
- one list of rows, two views
- orange: where color enters
- every change written at once, read again before every view

**Worth knowing if asked:**
- `listing.py` is new as of today: the code that builds the rows moved out of `shell.py`, and `listing_range()` and `current_listing_rows()` moved into the `Session`. `shell.py` lost about a third of its lines.
- Why read the dossier before every view: three small JSON files are cheap to read, and a change made by hand or by git shows at once.
- The editor's navigation (keys, going back and forward, the picker) is left out on purpose: it does not change where the rows come from.
- A listing that has already been printed does not change afterwards. It shows the dossier as it was when it was printed.

---

## Things to show

1. **Where the run stops, in the window.** `make boot-lode-runner-break`: Lode Runner boots and runs 4 million instructions, the same count as the experiment, then stops as if Ctrl-X had been pressed. The next Ctrl-X continues. The experiment itself always runs headless; this shows where it ends. Fits slide 4: `until` with a window is a pause.
2. **The experiment at the prompt.** In `make ipython`:
   ```
   %run scripts/lr_basic_blocks_analysis.py
   show_routines()
   show_blocks(0x6238)
   listing(0x6238, 0x62c4)
   edit(0x6238)
   ```
   `0x6238` is `LOAD_LEVEL`.
3. **The routine graph.** `show_routine_graph()` writes `tmp/routine_graph.svg` and puts its link on the clipboard, to paste into a browser.
4. **The inner loop, live.** `docs/diagrams/inner-loop-hooks.html`: seven instructions, call by call, through the kind methods and hooks.
5. **A tiny program through the whole pipeline.** `make walkthrough`, reports in `tmp/walkthrough/`.

---

## Open

- A slide on how a byte reaches the screen (see slide 3). The new hi-res renderer in `apple.py` belongs there: a write redraws its byte and both neighbours, because colours smear across byte boundaries.
- Which slides get a code snippet instead of bullets.
- Order of slides and demos.
