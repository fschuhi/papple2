# papple2 -- TODO

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

## Charter 

- Forward-looking only -- concrete, startable work: tasks specified well enough that next-session-me can begin within ten minutes, plus investigation items, test specs, and scratchpad ideas awaiting promotion or deletion.
- Items are unordered within their theme sections; open questions are marked _Needs investigation_ in the bullet.
- When an item is completed, record its durable outcome in `HISTORY.md` during the same session while the evidence and rationale are fresh, then strike it through in `TODO.md` with a concise handover note.
- Retain struck-through items through the next session because `TODO.md` is included in the standard filesdump while `HISTORY.md` normally is not; at the end of that next session, remove the already-archived items from `TODO.md`. Strategic direction, ordering, and milestones live in `GOALS.md` -- anything that needs a strategy discussion before it is actionable goes there.
- Architecture, contract, and settled decisions live in `README.md`.

---

## M3 -- Silent mode (done 2026-09-12)

~~`KeyScript` checkpoint class (instruction-count-driven scripted keypresses) in `Checkpoints.py`; first code-only test with a walkthrough docstring (`test_keypress_reaches_program`); fixed a real hang where a checkpoint-requested stop during a headless run never actually returned control (no window to resume or halt it from); `--nodisplay`'s help text in `Robotron.py` updated to match.~~ **Done when:** ~~the emulator can run to a breakpoint or for N instructions without opening a window, and a test can feed keypresses from code and check memory afterwards.~~ See `HISTORY.md` for the full account.

## M4 -- Split into core, debugging tools, and Robotron showcase

- **Robotron-specific code baked into the core emulator, found while working on M3:** `EmulatorStoppedState.on_l` in `Emulator.py` prints a fixed set of Robotron memory addresses (`$00`-`$05`, `$150a`, `$150b`, `$150c`, `$1407`); `Memory.write_byte`'s protected ranges (`0x2dfd`-`0x2dff`, `0x4000`-`0x4100`) are Robotron-specific write guards; `Emulator.handle_rts`'s assertion ("no address on the stack... possible but not happening in Robotron") assumes Robotron's call structure. Move all three out of the core, into Robotron-specific hooks or into `Robotron.py`/`RobotronXl.py`.
- **Decide module names and rename in one approved step** (lower case per PEP 8, e.g. `emulator.py`, `memory.py`) -- one step, not scattered across the other M4 work.
- **`Statemachines_example.py` and `Papple2.py`:** move to `examples/` or remove -- decide which, per file.
- **Package layout:** land on the actual split, e.g. `papple2.core`, `papple2.debug`, and an `examples/robotron/` directory (names open for discussion). `pysm` staying in the project is already decided; still open is whether the run/stop state machine (`EmulatorStates`) lives in `core` or `debug`.
- **`Memory.write_byte2`** looks like an older version of `write_byte`. Check whether anything still calls it; remove if not (carried over from the M3 scratchpad).

**Done when:** three clearly named parts exist, the core has no Robotron-specific lines, and `pysm` is only used in the debugging or showcase part.

**Look at first:** the import graph (documented in the first session), `Emulator.__init__`.

## Scratchpad

- `CPU.verbose_branch` has a copy-paste slip: the `BCS` case checks `opcode == BVS`. Harmless today (only used for printing), fix when we touch `CPU.py`.
- The Excel bridge (`RobotronXl.start_emulator`, `save_results`) had its signatures changed during M2 (`path` -> `data_dir` + `trace_dir`). Whenever M7 (PyXll bridge) work resumes, the Excel-side calls will need updating to match -- currently they'd fail with a clear `TypeError`, not silently misbehave.
- _Needs investigation_: pygame doesn't yet support Python 3.14 properly as of this session (open upstream issue). Revisit the Python-version pin in `README.md`/`Makefile` once pygame catches up.
- Pin the installed `pysm` version in `requirements.txt`, left over from M3 (the `manifest.lst` note this came from, about `Assembler` being commented out, turned out to be stale -- `Assembler` was already active).
- _Needs investigation, optional, carried over from M3:_ a second silent test that boots `A2ROM.BIN` (reset vector at `$FFFC`), runs for N instructions, presses a key, and asserts the ROM stored it in the input buffer at `$0200`. Not required for M3's Done-when, parked here in case it's still wanted.
