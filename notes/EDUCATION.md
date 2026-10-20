# papple2 -- Education

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- This file is for you, the AI model, in your role as educator: notes on what I know and what I don't, how I want things explained, and the topics we work through. Read it at the start of a session, together with `CRITICAL_RULES.md` and `LLM_INSTRUCTIONS.md`.
- You write it and you keep it up to date: whenever a session shows that you misjudged what I know, or a topic moves on, change this file in the session's docs patch. I rarely read it, as with `docs/decisions.md`.
- What goes in: facts about me as a learner, and rules for explaining, each grounded in something that happened. What stays out: rules that hold for every project (those are in `LLM_INSTRUCTIONS.md`), and knowledge about the code (that is in `README.md`, `docs/workbench.md` and the code).
- Keep entries short and concrete. Date an entry when it comes from a specific session.

---

## What I know well

Do not explain these; using the word is enough.

- Software development as a craft: git, patches and `make patch`, refactoring, tests and test-driven work, callbacks, state machines, separation of concerns, dependency direction between packages.
- Product thinking: priorities, scope, the cost of building the wrong thing. I am the product manager of `papple2`.
- The workbench from the prompt side: the commands in `shell.py`, the experiments, the reports, the dossier, the editor's keys. I designed most of it in conversation.
- Excel and VBA (`a2-hires-lab`), Obsidian, PyCharm.

## What I am learning

Explain these when they come up, briefly, with a pointer to read more.

- Python idioms beyond the basics: list comprehensions (see "Topics"), name mangling with `__` (learned 2026-10-09), frozen dataclasses, nested functions and closures, generators.
- The 6502 and the Apple II: addressing modes, the stack, self-modifying code, the hi-res screen.

## What I know of the code

The gap that hurts most: code you wrote that I have not read with you. Track it per module. "Prompt side" means I know what it does, not how.

- `papple2.workbench.listing_editor`: prompt side only. On 2026-10-09 I did not know `arrive()`, `step()`, `remember()`, or what the picker holds.
- `papple2.workbench.shell`: prompt side; the helpers behind the commands not read.
- `papple2.workbench.annotations`: unknown; ask.
- `papple2.workbench.basic_blocks_analysis`, `tiling`, `stack_tracking`: the ideas yes (tiles, blocks, dominators, loops, the shadow stack); the code not read.
- `papple2.debug.disassembler`: changed together on 2026-10-09 (`ran`, `label+N`, the wrap at `$FFFF`); the rest not read.
- `papple2.core`: read together during the redesign (2026-09-27 to 2026-10-01); may need a refresher.

## How I want things explained

Each rule comes from a session where its absence cost time.

- When I say I don't understand, first ask one targeted question: the problem, the names, or who calls whom? Do not guess the level and write a long answer. (2026-10-09: you lowered the level across the board and explained patches, callbacks and refactoring, which I know; the gap was the editor's internals.)
- Start with the concrete case from the run, with addresses, then the names in the code. (2026-10-09: "Enter opens `r_11x2_1` at `8336`, the bar on `8352`, the `JSR`" made the picker's change clear at once; "entries with text, routine and target row" did not.)
- When you name a function I have not read, say who calls it and when.
- Before I read code that is new to me, show a small picture of who calls whom. Without it, reading alone takes too long, and I stop reading.
- When you quote a report, use its own column names, and explain them on one real row. Never a table with headers you made up. (2026-10-09: `lr_split_transitions.csv`.)
- Do not reassure after the fact. If something was not thought through, say so. (2026-10-09: "the ranges are the persistent part of a stretch", said to calm a worry, was wrong.)

## Why this matters

If I stop understanding how `papple2` works for long, I stop working on it. Keeping me close to the code is part of every step, not a courtesy.

---

## Topics

### Python, for the code review

1. Reading a list comprehension: the `for`, then the `if`, then the expression in front. Example: `call_sites()` in `shell.py`, nested. When a loop reads better.
2. Nested functions in `edit_rows()`: why the editor's helpers live inside one function, and what they share.
3. Dataclasses: `ListingRow`, `Place`, `PickerItem`, `CallSite`; `frozen=True` and why tuples go with it.
4. Decorators: `@returns_text` in `shell.py`, `@bindings.add` in the editor.

### papple2, for the code review

1. The listing editor: `edit_rows()`, the state, the steps (`history`, `future`) and the memory per routine (`remembered`), the picker.
2. From reports to routines: `find_routines()`, `build_graph()`, `ran_parts()`.
3. The disassembler: the modes, `__name_of()`, `ran` and `is_code`.
