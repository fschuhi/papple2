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
> In pink, the listing editor: one screen on all of it.

**Right pane:**

- blue: watch the run, write reports
- red: find routines and loops
- grey: the state, and the dossier on disk
- green: the commands, the contract
- pink: one screen on it

**Worth knowing if asked:**
- `shell` still reaches past `session` to `basic_blocks_analysis`, `hidden` and `tiling`. Those are helpers kept next to the commands; moving them is Session step 2a in `TODO.md`.
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

### 4. The pipeline (`pipeline.png`)

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

---

## Things to show

1. **Where the run stops, in the window.** Lode Runner boots and runs 4 million instructions, the same count as the experiment, then stops as if Ctrl-X had been pressed. The next Ctrl-X continues.
   ```
   python scripts/boot_lode_runner.py data/bin/LODE_RUNNER.BIN --instructions 4000000
   ```
   - `Session.run()` always runs headless, so the experiment itself can't be watched; this is the way to show its stopping point.
   - There's no make target for it yet.
   - The script's docstring says the window mode with `--instructions` was never tried. Try it before the presentation.
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

- A slide on how a byte reaches the screen (see slide 3).
- Which slides get a code snippet instead of bullets.
- Order of slides and demos.
