# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` or `CHANGELOG.md`(on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** M7 (Excel bridge via PyXll) is unchanged since last session -- verification from a live workbook and the `ExcelContext`/`raise_error` decision are still open. This session's work was entirely the `unittest` -> `pytest` conversion (Theme 1 below): all 11 remaining `test_cpu_*.py` files converted across four batches, parametrized wherever a clean shared table existed (branch, register transfer, inc/dec, arithmetic's ADC/SBC/compare), left as plain functions where the ops didn't share one (logical, shift). One real bug surfaced along the way: an `SBC` case that silently relied on `carry_flag` inherited from the previous case broke when pulled out as an independent parametrized row -- caught by the test run, fixed. `TODO.md` is now reorganized into five groups (test infrastructure, finishing M7, parked decisions, environment housekeeping, optional coverage) instead of a flat scratchpad.

**What's next:** finish Theme 1 -- design the shared `Emulator`/`Assembler` fixture in `conftest.py` that `test_emulator_silent.py`, `test_time_machine.py`, `test_mem_access_collector.py`, `test_emulator_debug_keys.py`, and `test_tiles.py` all need before they can convert; `test_softswitches.py` and `test_display_memory.py` need their own smaller local fixtures; `test_robotron_waves.py` stays separate since it loads the real `ROBOTRON.BIN`. Theme 2 (finishing M7) is the natural stop after that. Public-repo prep (Theme 4) stays parked until Theme 1 is done.

---

## 🎯 Strategic vision

### What papple2 is

`papple2` is a small Apple II emulator written in Python. It is not meant to compete with full emulators on speed or completeness. Its purpose is to be a debugging instrument: a machine I can stop, inspect, rewind, and script from Python while it runs Apple II code.

The core comes from ApplePy by James Tauber, ported to Python 3 and stripped of what I did not need (socket interface). Around that core I built tools that a normal emulator does not offer: an assembler and disassembler, breakpoints and hooks, a time machine that rewinds CPU and memory state, a log of every memory access, and a map of which instructions were executed and how control flowed between them.

### Why Python

Python is slow for emulation, but that never mattered for the debugging use. What mattered was that the whole emulator is a few thousand lines I can read, change, and extend in an afternoon, and that the debugging tools can be written in the same language as the emulator with no bridge in between. This is the trade-off `papple2` makes on purpose: understandability and scriptability over speed.

### Where it is going

1. **A macOS-native library.** The code was written on a Windows machine. It moves to the MacBook and becomes a proper Python package that other projects can import. (Note that 4. below means that we should still be able to use the library from Windows as well, possibly via a bridge layer between PyXll and a server on macOS, even though that would be only second-best.) 

2. **A clean split into three layers.** The core emulator (6502, memory, Apple II hardware), the debugging tools built on top of it, and the Robotron 2084 disassembly project as the worked example of how to use both. Today these are mixed; separating them is what makes `papple2` reusable.

3. **Runs with and without a screen.** With the pygame window for watching and interacting, and silently for tests and for scripted analysis: boot, run to a point, press keys from code, read the buffers, done.

4. **Reviving the Robotron work.** The Robotron 2084 disassembly was hibernated, but its workbench (call trees from tiles and stretches, the Excel front end) is the proof that the debugging tools work on a real program. It gets a second life in the project as a worked-through showcase. The Excel bridge moves from xlwings to PyXll.

5. **Serving `load-runner`.** My private educational project ports an Apple II game to Godot. `papple2` can help in two ways: cycle counting, if I decide that timing fidelity matters for the port; and level extraction, by letting the original code load a level into memory and then reading the filled buffers instead of reverse-engineering the disk format by hand.

### What I want to learn along the way

This project taught me Python the first time. This time it should teach me how a Python project is shaped when it is meant to be reused: package layout, pytest, and separating a library from the programs that use it. I am also fascinated by state machines; `pysm` stays in the project for that reason, even where a simpler mechanism would do.
