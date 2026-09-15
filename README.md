
# papple2

**A small Apple II emulator written in Python, built as a debugging instrument rather than a player.**

---

## Vision

`papple2` is a small Apple II emulator written in Python. It is not meant to compete with full emulators on speed or completeness. Its purpose is to be a debugging instrument: a machine I can stop, inspect, rewind, and script from Python while it runs Apple II code.

The core comes from ApplePy by James Tauber, ported to Python 3 and stripped of what I did not need (the socket interface). Around that core I built tools that a normal emulator does not offer: an assembler and disassembler, breakpoints and hooks, a time machine that rewinds CPU and memory state, a log of every memory access, and a map of which instructions were executed and how control flowed between them.

**Core philosophy:**

- **Understandability over speed.** Python is slow for emulation, but that never mattered for the debugging use. What mattered was that the whole emulator is a few thousand lines I can read, change, and extend in an afternoon, and that the debugging tools can be written in the same language as the emulator, with no bridge in between.
- **A debugging instrument, not a player.** The point isn't to run Apple II software well -- it's to run it *observably*: stoppable, inspectable, rewindable, scriptable.
- **Runs with and without a screen.** The pygame window is for watching and interacting. Silent mode (`Emulator(no_display=True)`) is for tests and scripted analysis: boot, run to a point, press keys from code, read the buffers, done.

---

## Architecture

### Package split (M4, done 2026-09-12)

`papple2` is split into three layers:

```mermaid
graph TD
    SHOW["Robotron showcase<br/>examples/Robotron/: workbench, robotron_xl, excel bridge"]
    DEBUG["papple2.debug<br/>assembler, disassembler,<br/>memory_map, checkpoints, tiles, labels, annotations"]
    CORE["papple2.core<br/>cpu, memory, apple, window, emulator, hooks"]

    SHOW --> DEBUG
    DEBUG --> CORE
```

The showcase depends on the debugging tools, which depend on the core -- never the other way around.

`Hooks` lives in `papple2.core`, not `papple2.debug` as an earlier version of this diagram had it: `Emulator.__init__` unconditionally constructs `TimeMachine`/`MemAccessCollector` (the `time_machine`/`mem_access` flags only control whether they're activated, not whether they exist), so `Emulator` cannot run at all without `Hooks` importable. The split follows that real coupling.

### Emulator / Window / States (current, as of M2.5)

This part is real and current, as of the M2.5 refactor (`HISTORY.md`, 2026-09-11). `Emulator.run` no longer touches pygame directly -- it polls a `Window`, dispatches whatever comes back to `EmulatorStates`, and lets `EmulatorStates` decide what that means:

```mermaid
graph TD
    E["Emulator<br/>run(until=None)"]
    W["Window<br/>PygameWindow / NoWindow"]
    S["EmulatorStates<br/>composes a StateMachine"]
    R["Running"]
    ST["Stopped"]

    E -- "poll() -> events" --> W
    E -- "dispatch(event)" --> S
    E -- "status(text)" --> W
    S --> R
    S --> ST
    R -- "ctrlx / breakpoint" --> ST
    ST -- "ctrlx" --> R
```

`PygameWindow` and `NoWindow` share the same three methods (`poll`, `present`, `status`), so `Emulator` doesn't know or care whether a window exists. A watcher firing -- a real breakpoint, or an `until` condition passed to `run` -- dispatches the same `breakpoint` event that `ctrlx` uses, so `Running` -> `Stopped` always goes through the state machine, never around it.

---

## Settled decisions

This section is more useful to an LLM picking this project back up than to me -- which is exactly why it's here: `README.md` rides along in every session's `filesdump.txt` by default.

- **`papple2` is a real, installable Python package** (`src/papple2/`, `pyproject.toml`, editable install via `make setup`), split into `papple2.core` and `papple2.debug` sub-packages (M4, 2026-09-12); the Robotron showcase lives in `examples/Robotron/`, outside the installed package (`Robotron.py` itself still needs moving there). Internal imports are explicit (`from papple2.core.X import Y` / `from papple2.debug.X import Y`) -- star-imports were replaced project-wide back on 2026-09-06, earlier than this file previously said.
- **Python 3.12 for the venv, not whatever `python3` resolves to.** `pygame` 2.6.1 doesn't build or run correctly under Python 3.14 as of this writing (open upstream issue).
- **Paths come from `papple2.toml`** (local, gitignored; `papple2.example.toml` committed), not hardcoded Windows strings, and not `os.chdir`.
- **`EmulatorStates` composes a `StateMachine` rather than subclassing one.** It's the root of its own state tree and is never handed to code that expects a plain `StateMachine` -- the case for composition over inheritance. The individual states (`EmulatorRunningState`, `EmulatorStoppedState`) do legitimately subclass `StateMachine`, since they're genuinely registered as states via `add_state`.
- **`L` and `D` are reserved for debug hooks, and only while execution is `Stopped`.** `PygameWindow.poll()` turns those two keys into `Event('l')`/`Event('d')` instead of ordinary keystrokes -- but only in the `Stopped` state; while `Running`, they pass through like any other key, so typing them into the Monitor or BASIC works normally. `D`'s built-in use is `EmulatorStoppedState.on_d`, a generic CPU-register dump -- genuinely core behavior, not Robotron-specific. `L` has no built-in behavior at all; it's a bare hook slot, meaningful only once something external attaches to it (see `tests/test_emulator_debug_keys.py`).
- **The window (pygame) is a separate, swappable layer, not baked into `Emulator`.** `PygameWindow`/`NoWindow` share `poll() -> list`, `present()`, `status(text)`; `Emulator.__init__` picks one based on `no_display`. `Emulator.run`/`event_loop` and the state handlers contain no pygame reference.
- **A watcher firing dispatches `Event('breakpoint')` into the state machine, rather than hard-returning out of `run`.** Separately, `run(until=...)` returns to its caller once execution stops for any reason; a plain `run()`/`event_loop()` call (no `until`) keeps looping through pauses as before, and only stops on `halt`.
- **`time.monotonic()`, not `pygame.time.get_ticks()`, for frame pacing** -- works identically whether or not a window exists.
- **`QUIT` (closing the window) and the Print key both map to the same `halt` event.** There's no separate hard-exit path. Print exists mainly for the Windows heritage of this code; on macOS, closing the window is the primary way to trigger it.

---

## Relation to sibling projects

**`load-runner`:** a private educational project porting an Apple II game to Godot. `papple2` can help two ways: cycle counting, if timing fidelity turns out to matter for the port; and level extraction, by letting the original code load a level into memory and then reading the filled buffers instead of reverse-engineering the disk format by hand. Not started yet.

**`a2-hires-lab`:** a standalone Excel/VBA lab exploring Apple II hi-res graphics mechanics, built around Chapter 3 of the `load-runner` disassembly. No shared code or repo with `papple2`. Its NTSC color decision table, once fully verified by hand against the chapter's worked examples, is meant to become test fixtures for `papple2`'s `Display.update_hires`, which currently uses a simplified per-pixel color model with no neighbor-adjacency rules. That handoff hasn't happened yet.

---

## Testing strategy

`papple2` is verified at two tiers, deliberately:

- **Automated (`make test`).** The pytest suite covers 6502 instruction semantics and the classic hardware quirks, Apple II specifics (soft switches, the hi-res memory buffer), running headless with and without checkpoints/breakpoints, and the debugging hooks (`TimeMachine`, `MemAccessCollector`). All of it runs with `no_display=True` -- no pygame window involved, and none of it can be, meaningfully: a headless run has no way to assert "does this look right on screen."
- **Manual (`make run`).** The pygame window itself -- actual rendering, real keyboard input, the full event loop -- is verified by hand instead: booting the Robotron showcase and confirming it displays and responds to input the way it should. This makes the Robotron example in `examples/Robotron/` not just a demonstration of how to use `papple2`, but the manual test for the with-window half of the emulator. It gets run this way whenever `Apple2`, `Display`, `Window`, or the with-window parts of `Emulator`/`EmulatorStates` change (done for M2, and again after M4's split).

---

## Running

```bash
make setup   # create the venv (Python 3.12), install dependencies in editable mode
make test    # run the pytest suite
make run     # boot Robotron with the pygame window open
```

`make setup` will happily produce a broken install if your default `python3` resolves to 3.14. If needed: `rm -rf .venv && python3.12 -m venv .venv && make setup`.

---

## Technical notes & gotchas

- **`pygame` 2.6.1 does not build or run correctly under Python 3.14** -- `pygame.mixer` and `pygame.font` fail to import. Open upstream packaging issue, not specific to this machine. Use Python 3.12 for the venv until that's resolved.
- **A checkpoint that pauses execution (a real breakpoint, or an `until` condition) stays registered after it fires.** If something resumes via `ctrlx` within the same `run()` call and the checkpoint's condition is still true, it re-fires immediately. `run(until=...)`'s own checkpoint is cleaned up automatically at the start of the next `run()` call, so this only affects hand-registered checkpoints (`add_checkpoint`) used interactively -- none are currently active by default.
