# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## 1. Type hints follow-ups

- Annotate the attributes `mypy` can't figure out by itself, e.g. `self.ops_dispatch = [None] * 0x100` in `core/cpu.py` (it concludes the list only ever holds `None`); likewise `CPU.PC`, `CPU.branched`, `Memory.apple2`. PyCharm doesn't mind these, so this only matters if we ever adopt `mypy`.
- Test files: hints are optional there. Decide whether to add them; today they're mixed (some fixtures in `conftest.py` have hints, most local fixtures don't).

## 2. Direction follow-ups (from 2026-09-23)

See `DIRECTION.md` for the context of each item.

- _Needs investigation:_ is there an Apple II tool that saves per-byte code/data marks to a file (like FCEUX's Code/Data Logger), or tracks data provenance? microM8's heat map comes close.
- Jupyter primer, for a conscious decision on the monitor: Joel Grus's talk "I Don't Like Notebooks" (JupyterCon 2018), marimo's "why marimo", then a small hands-on notebook with `papple2` booting Lode Runner.
- Robotron leftovers in `papple2` (`make boot-robotron` and its script stay, as decided 2026-09-27): `Display.save_hires_bytes`/`load_hires_bytes` in `core/apple.py` (broken, no caller), and the three tests in `test_emulator_silent.py` that load `ROBOTRON.BIN` -- they could use small assembled programs instead, like the trap tests. The labels, the checkpoint classes, the `$51b6` exemption and the tiles pointer went with the pruning (2026-09-28).
- Research document with glossary (in progress, away from the keyboard): established reverse-engineering concepts, and what the tools for 6502 platforms (NES, C64, Apple II) offer to understand a game. Basis for renaming `papple2`'s concepts, or at least putting them into their proper context.

## 3. Parked decisions

- The window's hi-res colours ignore the NTSC neighbour rules (a pixel's colour depends on its neighbours), so they can look wrong. `a2-hires-lab` has worked out the rules; use them if accurate colour ever matters.
- `debug/assembler.py` calls `sys.exit(1)` on an error in the source it assembles. Fine for scripts and tests (`pytest` fails just that test), but it would end an interactive session (monitor, notebook) on a typo. Decide with the monitor: keep it, or raise an `AssemblerError` (stops just as fast, but can be caught -- and swallowed).
- Bandits from the `.do` (`Bandits (1982)(Sirius Software)[cr Nameless Cracker - Pirate Treck - Krakowicz][t +1].do`), parked 2026-09-26 in favour of the Total Replay files. What we know: its boot code (`$0801`-`$084C` of track 0 sector 0) is byte-identical to Lode Runner's DOS 3.3 boot sector. On the first entry it expects `$27 = $09` (the ROM's buffer page after loading the sector to `$0800`) and `$2B` = slot times 16; it builds `$C65C` in `$3E`/`$3F` and calls it once per sector with the sector number in `$3D` and the page in `$27`. It loads track 0 top down into `$B600`-`$BFFF` (first page `$B6` at `$08FE`, sector count minus one `$09` at `$08FF`), picking physical sectors from the table at `$084D` (`00 0D 0B 09 07 05 03 01 0E 0C 0A 08 06 04 02 0F`, the DOS 3.3 logical-to-physical order from general knowledge, unconfirmed), then `JMP ($08FD)` goes to `$B700`. Its DOS differs from Lode Runner's: only 7, 10 and 3 of the 16 sectors on tracks 0-2 are identical. The old plan: fake the ROM's boot, a hook at `$C65C` serving physical sectors, then a watch for the modified DOS's disk access. The `.dsk` of the same crack is byte-identical; the `[o]` overdump and the WOZ original are out.

## 4. Environment / packaging housekeeping

- Bring in automated `black` formatting, as in some of my other projects. Decide how it runs: a `make` target, PyCharm on save, or a pre-commit hook. A hook reformats on `git commit` and then stops the commit, so you have to `git add` and commit again; that's the "why do I have to commit twice" effect from other projects. Explain whichever choice plainly. Then reformat the whole codebase in one separate commit, so later diffs show only real changes, and list that commit in `.git-blame-ignore-revs`, so `git blame` looks past it.
- Python 3.14: `pygame-ce` 2.5.8 works there (imports with `mixer` and `font` on 3.14.5, checked 2026-09-24). Remaining: run `make test` under 3.14, then update the Python-version notes in `README.md` and the `Makefile`.
- Pin `pysm`'s version in `requirements.txt` (nothing is pinned today; `pip show pysm` shows the installed one). `pysm` first, because the emulator's state machine rests on it; decide whether to pin the others too.

## 5. Optional coverage

- Finish the `unittest` -> `pytest` conversion: `tests/test_memory.py` and `tests/test_assembler.py` still use `unittest` (`test_memory.py` already has two `pytest` functions next to its old class). In `test_assembler.py`, rename `test_dump`: it's a printing helper, but its `test_` name makes the runner run it as a test.

## 6. Performance (parked, 2026-09-23)

Measured with `cProfile` on the headless Lode Runner run (`HISTORY.md` 2026-09-23, at the tag `pre-redesign`). Since the pruning, windowed runs reach about 3.5 times real Apple II speed unthrottled and can be throttled to it (`HISTORY.md` 2026-09-27/28), so this isn't needed today.

- `is_executing()` runs about three times per instruction and asks the `pysm` state machine each time (about 8% headless, measured 2026-09-23). Since 2026-09-28, `executing` mirrors the state from construction on: Running's entry and exit actions set it, `initialize(fire_events_on_init=True)` runs the entry action, and `test_executing_follows_the_state_from_the_start` pins it down. Remaining: `return self.executing` in `is_executing()` -- decide together with the `pysm` discussion (section 7).

## 7. Redesign (from 2026-09-28)

The old instrumentation is gone (`HISTORY.md` 2026-09-27/28); the ideas for the new one are in `docs/instrumentation-ideas.md`.

- `pysm`, yes or no: an in-depth discussion with the arguments on both sides. The state machine is where run-level behaviour could grow (single step, run to here, recording modes); the risk so far was hollowing it out patch by patch (entry actions removed, `until` without an event). For now it does statechart work: state changes by events, entry and exit actions, the initial state entered on `initialize()`.
- Keeping what we've learned about an address across experiments: the old tile lists in Excel showed notes from `Annotations` next to each tile (removed 2026-09-27, at the tag). Decide how learnings persist in the new design.

## 8. Small code steps

- Assembler: a program whose first instruction has no operand (`INX`, `NOP`, `PHA`, ...) fails with `UnboundLocalError`. In `assemble()`, `operand` is only set on lines that have one, but `find_info(mnemonic, addressmode, operand)` always passes it; later lines reuse the previous line's value by accident. Reset `operand` at the start of each line, and add a test. Found 2026-09-28.
- `util.py`: `hexaddr()` and `hexbyte()` default to lowercase (`lower=True`), but the decision is uppercase with `$` (XekriRedmane's style, used in the CPU status line since 2026-09-28). Flip the defaults, or remove `lower`, so the disassembler, `Labels` and messages follow.
- The stand-ins' comments still say their writes go past "the CPU's write hook", which no longer exists: `RwtsHook`'s docstring in `scripts/boot_lode_runner.py`, `MliHook`'s docstring and the comment in `MliHook.read()` in `scripts/boot_bandits.py`.
- `graphviz` in `requirements.txt` is unused since `tiles.py` went (2026-09-27); remove it.
