# papple2 -- Documents

What each file in `docs/` is. What `papple2` is and how to start it: the top-level [`README.md`](../README.md). The plan and the record: `GOALS.md`, `TODO.md` and `HISTORY.md` in the repo root.

The files fall into five kinds:

- **Reference** describes what is built, and is kept true to the code.
- **Study** reads Lode Runner with `papple2`'s tools. It is dated and stays as it was written.
- **Ideas** says where things may go. Nothing in it is built yet.
- **Collected** is material from outside sources.
- **Derived** is made by a tool or from another file. Make it again rather than edit it.

---

## Reference

- [`glossary.md`](glossary.md) -- the words used across `papple2`'s code, tests, documentation and dialogue.
- [`workbench.md`](workbench.md) -- for the reverse engineer: the commands at the prompt, the experiments, the reports, hidden ranges and color ranges.
- [`routine.md`](routine.md) -- what a routine is, where one starts and where it stops, and what the tools show of it.
- [`architecture.md`](architecture.md) -- how the machine runs, its extension points, memory access by kind, and the speed control.
- [`instrumentation-design.md`](instrumentation-design.md) -- the rules for breakpoints, traps and hooks that span `Emulator`, `CPU` and `Memory`.
- [`data-files.md`](data-files.md) -- the Apple II files `papple2` needs, where to get them, and where to put them.
- [`diagrams/inner-loop-hooks.html`](diagrams/inner-loop-hooks.html) -- every call from the instruction boundary to `after_instruction`, per instruction, as of the tag `core-complete`.

Also reference, outside `docs/`: the walkthrough, `tests/test_walkthrough.py`, which teaches the pipeline on three small programs, told as tests.

## Study

- [`lr_structures.md`](lr_structures.md) -- the structures of Lode Runner, read from Xekri's source: the answer key, a catalogue of structures, and `find_routines()` graded (2026-10-15 to 2026-10-17).
- [`lr_answer_key.csv`](lr_answer_key.csv) -- one row per block of the attract play, with the Xekri subroutine it lies within. `make lr-grade` grades against it.
- [`lr_case_studies.md`](lr_case_studies.md) -- pieces of Lode Runner's real code read with `papple2`'s tools, the way the walkthrough reads its small programs; and the rules for the dossier's labels.
- [`TRY_GUARD_MOVE_DOWN-as-it-ran.html`](TRY_GUARD_MOVE_DOWN-as-it-ran.html) -- one subroutine with the counts of the attract play on every line, and its jumps as arrows.
- [`TRY_MOVING_LEFT_Inside_MOVE_PLAYER.html`](TRY_MOVING_LEFT_Inside_MOVE_PLAYER.html) -- why the run cannot tell `TRY_MOVING_LEFT` from `MOVE_PLAYER`, what rule could, and what that rule risks.
- [`lode-runner-routine-ranges.html`](lode-runner-routine-ranges.html) -- three places from the attract play where a jump leaves or stays inside a routine's range, drawn the way `edit()` draws a routine.

## Ideas

- [`DIRECTION.md`](DIRECTION.md) -- where the reverse engineering work is headed: the book, lessons from Robotron, prior art, and the technical direction.
- [`ui-ideas.md`](ui-ideas.md) -- ideas for reading code with `papple2`: windows, brushing, navigation, editing, search, stretches. An idea that gets started becomes an item in `TODO.md`.

## Collected

- [`reveng-catalogue.md`](reveng-catalogue.md) -- reverse engineering techniques for the Apple II, and the tools that offer them. A draft, with unchecked claims marked.
- [`advice_from_6502org.md`](advice_from_6502org.md) -- advice from the 6502.org thread on the Robotron project (2019).
- [`link_list.md`](link_list.md) -- links: Robotron gameplay, Apple II graphics, and more.

## Derived

- [`reports/`](reports/) -- the committed reports of the experiments, one reports folder per experiment.
- [`diagrams/`](diagrams/) -- the diagrams' Graphviz sources (`.dot`) and the SVGs `make presentation` renders from them; `routine_graph.svg` is an output of `show_routine_graph()`.
- [`listings/`](listings/) -- Xekri's listing: the whole of it as a table (`listing_clean.tsv`), and single subroutines (`.lst`).
- [`html/`](html/) -- the HTML pages, reading versions of the markdown, made by an LLM; with them the stylesheet `style.css`, the rules for making a page in `style-guide.md`, and the example `example.md` with its page `example.html`.
- [`lr_structures.html`](lr_structures.html) -- an HTML version of `lr_structures.md`.
- [`images/`](images/) -- the screenshots in the top-level `README.md`.
