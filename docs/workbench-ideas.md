# papple2 -- Workbench ideas (braindump)

(Note: "I" in the following paragraphs refer to the user, "you" to the AI model.)

**Status:** braindump from the session of 2026-10-01, collected, not decided. It holds the raw material for the workbench, the way `docs/instrumentation-ideas.md` held it for the instrumentation. The direction it serves is in `DIRECTION.md` (section 1: dynamic first, static fills the holes; section 2: the oracle only grades). Section 12 lists what is open.

---

## 1. Why a workbench

The experiments (`scripts/lr_count.py`, `scripts/lr_tiles.py`) answer one question per run and write their results to `tmp/`. Every further question means editing the script, waiting about 6 seconds for the run, finding the right file in `tmp/`, and opening it in Finder, Total Commander or IrfanView. The 6 seconds are the brick wall for interactive work; the file hunting is a distraction and a time sink.

The wish: a reverse engineering language (a "reveng DSL") that a fast typist can think in. Short commands like "disassemble this", "show the map of that", "find the container of tile x", acting on a shared session state, so that the parts of a session build on each other. Learning goes faster when we build the workbench while we use it.

## 2. Two kinds of questions

- **Questions about the recorded run:** disassemble, show a map, name a tile, find loops. These need no emulator. The run's results are already on disk (`lr_split_tiles.csv`, `lr_split_transitions.csv`, the maps), and loading them takes milliseconds. Only `make` reruns the emulation.
- **Questions that need the machine running:** "what does this `JSR` draw?" These cost a run of about 6 seconds, or later a start from an emulator snapshot.

Most reverse engineering questions are of the first kind, so the interactive loop can be instant. The CSVs and the objects built from them are the database; real databases come later.

## 3. Front end: IPython

IPython is the interactive Python shell Jupyter is built on, running in the terminal: tab completion, a persistent history, `thing?` for help, and `%autoreload`, which picks up changes to the workbench code without losing the session. It is a better prompt for the Python we already write, not a new tool. A session might look like this:

```
In [1]: from papple2.workbench import *
In [2]: wb = load("lode_runner")
In [3]: dis(0x6238, 0x62c7)
In [4]: name(0x627e, "load_level.col_loop")
In [5]: show("execution_map")
```

`show()` opens a map or a graph directly: `webbrowser.open(path)` from the standard library opens HTML (and PNG) in the default browser on macOS and Windows; for the system's image viewer, `open` on macOS and `os.startfile` on Windows, chosen by platform the way the `Makefile` does.

Jupyter stays an option for later, when inline pictures matter. Not first, because of hidden state (cells run out of order leave a state no one can reproduce) and because the workbench module is the same either way.

## 4. Session state

- Names, labels and comments live in a plain text file under git, changed only by explicit commands. A session can always be rebuilt from the recorded run plus that file.
- The session is implicit: `load()` starts it, every command works on it, nothing has to be passed around.
- Names are dotted paths, e.g. `load_level.row_loop.col_loop`: hierarchy without forcing tiles into a graph.

## 5. The command language

radare2 can serve as inspiration for the vocabulary, not as a dependency: its commands are short and keyboard-driven (from memory, to be checked: `f` sets a flag, `CC` a comment, `pd` prints disassembly, `agf` shows a function's graph). Its analysis is static, ours rests on what ran. Later we could export our names and comments to it, as a viewer.

Candidate commands, to be grown by use rather than designed up front: `load`, `dis`, `name`, `comment`, `show`, `loops`, `container`.

## 6. Containers (stretches)

Tiles stay as recorded. A stretch is a container of tiles that presents tile-like features to the outside and knows its structure inside:

- **Entry and exits**, plus the address span, computed from the sequential tiles. The tiles of a container are not always contiguous in memory (a loop body can sit after the code that uses it), so the span is a convenience, not an assumption.
- **Loops and calls inside.** A `JSR` is recorded as a leap to the subroutine, and the return arrives as a separate leap from the `RTS` (in `LOAD_LEVEL`: `$6358` -> `$6267`, `$64bb` -> `$62b3`). The container adds the call fall-through edge from the `JSR` to its return point, as disassemblers do inside a function, and keeps the call itself as an edge between containers. The tile data is not touched.
- **Holes.** The container sees the gaps between its tiles and fills them through `disassembler.py` when asked for its listing, marked "not run", because a hole may be an inline table rather than code. The marks also show where the dynamic run's coverage is thin.

In structural analysis terms, a container is a region collapsed into one abstract node.

## 7. Structure detection, kept modest

The textbook path from basic blocks to structure:

1. **Dominators:** block A dominates B when every path from the entry to B passes through A. Cooper, Harvey and Kennedy, *A Simple, Fast Dominance Algorithm*, is short enough to write ourselves.
2. **Natural loops:** a back edge is one whose target dominates its source; each defines a loop, and loops nest.
3. **Region recovery:** if/else and loops into structured form. Search terms: *structural analysis Sharir*, *interval analysis Allen Cocke*, Yakdan et al. *No More Gotos*.

`LOAD_LEVEL` (`$6238`, Xekri's name, used here only to locate it) shows the structure in the recorded counts alone: two clearing loops (`$6252` 31 times, `$625a` 6 times), a row loop (`$6269`, 16 times) around a column loop (`$627e`, 448 = 16 x 28 times) with back edges `$62a8` -> `$6269` and `$629c` -> `$627e`, and an if/else at `$6286` splitting 448 into 224 + 224 that joins at `$6292`. Never run: `$629a` (no sprite >= 10 in that level), the error path, the reset. The oracle check: does our loop nesting match `.loop1`, `.loop2`, `.row_loop` and `.col_loop`?

## 8. Disassembly in `dasm` style

`disassembler.py` produces the listings, adapted to the `dasm` listing style, with our labels and comments. Next to it, Xekri's listing, parsed by `a2-lode-runner`'s `tools/dasm_listing_parser.py` (`make dasm-listing`), is the oracle to compare against.

## 9. Maps

The HTML execution map from `lr_count.py` is a pattern, not a single report. The same grid can show other counts: `LDx`/`STx` maps, read vs. written, writes to HGR.

## 10. Breakpoints that know what they look for

- Tag each container with "writes to HGR" (`$2000`-`$5FFF`), from an `after_write_data` hook. Then work upwards from such a container to the `JSR` in the routine above it; a breakpoint there shows which call puts a sprite on the screen while the level is drawn. (In `LOAD_LEVEL` the `STA (PTR1),Y` at `$629c` writes into the level's sprite table, not to the screen; the drawing happens in the routine it calls at `$63b3`.)
- Sprite tables on the 6502 are almost always split into lo and hi bytes, so containers that load with indirect addressing and store to HGR with indirect addressing should be easy to find.

## 11. Chunks

Managing the noweb source is a level of reverse engineering of its own. From `LOAD_LEVEL` on, think and annotate in chunks: living documentation from the start, browsable with `a2-lode-runner`'s tools. How workbench names and comments turn into chunks is open (section 12).

## 12. Open questions

- Terminology: tile, split tile, "stretch tile", stretch, container. Which names survive?
- Where the session file lives, and its format.
- How containers are stored: in the session file, or rebuilt from the recorded run each time?
- From workbench names and comments to noweb chunks: generated, or written by hand with the workbench's help?
- Questions that need the running machine: rerun, or emulator snapshots?

## 13. A first slice

Load the two CSVs; `dis(start, end)` through `disassembler.py`; the session file with `name()` and `comment()`. Then structure detection as one command, `loops(entry)`, tested on `LOAD_LEVEL` against the oracle.
