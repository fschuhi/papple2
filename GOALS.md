# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` or `CHANGELOG.md`(on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** Theme 1 (the `unittest` -> `pytest` conversion) is done. This session finished it: shared `Emulator`/`Assembler` factory fixtures in `conftest.py`, `test_time_machine.py`/`test_mem_access_collector.py`/`test_emulator_debug_keys.py`/`test_tiles.py`/`test_emulator_silent.py` converted on top of them, `test_softswitches.py`/`test_display_memory.py` given their own smaller local fixtures, and `test_robotron_waves.py` deleted outright (dead WIP, never a working test). Along the way, the session took a real turn: instead of moving on to finish M7 (the Excel bridge) in place, we decided to carve Robotron and the Excel/PyXLL bridge out of `papple2` into their own repo entirely -- `papple2`'s near-term interest is the Lode Runner disassembly, not Excel tooling. `papple2` keeps a minimal, license-safe manual pygame smoke test instead (`tests/test_robotron.py`, done). The full carve-out plan is written up in `MIGRATE_ROBOTRON.md` for a dedicated future session; `ACTION_PLAN.md` now has M7.5 for it.

**What's next:** the migration itself (`ACTION_PLAN.md`'s M7.5) -- work through `MIGRATE_ROBOTRON.md` in a clean session. Documentation (M8) is postponed until after that, since it needs to describe `papple2`'s post-carve-out surface, not the current mixed one. The type-hints gap surfaced across today's conversions also needs its own session -- see `TODO.md`'s new "Type hints sweep" section for the concrete inventory and the open scope question.

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
