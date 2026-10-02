# briefing.md -- Task Specification for Claude

**Context:** `papple2` workbench -- loop detection on basic blocks, built on the tiling reports.  
**Goal:** Find the nested loops of `LOAD_LEVEL` (`$6238`) from the split tiling reports, with tiling and analysis as reusable parts of `src/papple2/workbench/`.  
**Primary references:** `docs/workbench-ideas.md` (sections 6, 7, 13), `DIRECTION.md` (sections 1, 5).

This briefing replaces the previous one. It sets the direction for a session; details may still be wrong. Work step by step, in the order of section 4.

---

## 1. Terms

| Term | Meaning |
| :--- | :--- |
| tile | A run of instructions from an entry point to the leap that leaves it. Recorded by the tiling instrumentation. |
| unbroken tile | A tile as recorded. Unbroken tiles may overlap. |
| split tile | A tile after breaking at every entry point. Split tiles do not overlap. |
| leap | A branch, `JMP`, `JSR`, `RTS` (or `RTI`, `BRK`): a transfer that leaves a tile. |
| glide | The CPU runs on into the next instruction, without a leap. Where breaking cuts a tile, the piece before the cut glides into the piece after it. |
| basic block | A node of the graph built for structure detection. Each basic block comes from one split tile. |
| edge | A connection between two basic blocks in the graph. |
| call fall-through edge | An edge added in the graph only: from the basic block holding a `JSR` to the basic block at `JSR + 3`. |
| stretch | Reserved for a future container that combines tiling reports and analysis reports. **Not used in this slice.** |

The tiling reports speak of tiles and transitions. The graph speaks of basic blocks and edges. The graph builder is the only place that translates between the two.

---

## 2. Design

### Pipeline: phases connected by files

Each phase reads reports from earlier phases, builds its own data structures, does its work, and writes reports to a folder given by the caller.

### Two kinds of packages in `src/papple2/workbench/`

- **Instrumentation package** -- hooks into a running `Emulator`. May include analysis and checks, and always writes reports. Three jobs:
  1. Set up its instrumentation on an `Emulator` passed in.
  2. Collect information while the `Emulator` runs.
  3. Write reports into a folder given by the caller.
- **Analysis package** -- no `Emulator`. Reads reports from a folder, works on them, writes reports into a folder. Because it only needs files, it can run directly on fixture files.

### `workbench/tiling.py` (instrumentation package)

- Holds what is in `scripts/lr_tiles.py` today: collecting tiles and transitions, the consistency checks, breaking the tiles (including the glide rows), and writing the four tiling reports.
- One object holds the tiling state for the three jobs. Names to be decided in the session.

### `workbench/basic_blocks_analysis.py` (analysis package)

- Reads `lr_split_tiles.csv` and `lr_split_transitions.csv`.
- Builds the graph, computes dominators, finds natural loops (section 3).
- Writes the two loop reports (section 3).

### Scripts

- `scripts/lr_tiles.py` stays a script and keeps its `make` target. It uses `workbench/tiling.py` instead of its own copy of the tiling code.
- `scripts/lr_basic_blocks_analysis.py` is new:
  1. Sets up the `Emulator` with the Lode Runner binary.
  2. Stops after 4,000,000 instructions.
  3. Adds its own instrumentation (the trap).
  4. Sets up the tiling instrumentation via `workbench/tiling.py`.
  5. Runs the `Emulator`.
  6. Has `workbench/tiling.py` write its reports.
  7. Runs `workbench/basic_blocks_analysis.py` on the same folder.
  8. Does consistency checks and further reporting.
- Reports go to `tmp/<script name without extension>/`, e.g. `tmp/lr_tiles/` and `tmp/lr_basic_blocks_analysis/`.
- The analysis has no `main()` of its own and no IPython front end in this slice.

---

## 3. Specifications

### A. Tiling reports: renames

| File | Old | New |
| :--- | :--- | :--- |
| `lr_tiles.csv` | (file name) | `lr_unbroken_tiles.csv` |
| `lr_transitions.csv` | (file name) | `lr_unbroken_transitions.csv` |
| `lr_split_tiles.csv` | `stretch_start_PC` | `tile_start_PC` |
| `lr_split_tiles.csv` | `stretch_end_PC` | `tile_end_PC` |
| `lr_split_transitions.csv` | `source_stretch_start` | `source_tile` |
| `lr_split_transitions.csv` | `target_stretch_start` | `target_tile` |

- The two transition files then have the same columns: `source_tile,leap_from_PC,opcode,outcome,target_tile,count`. This is intended: both register tiles.
- Names in the code that say "stretch" are renamed in the same step, e.g. `transform_to_stretches`, and the "Split stretches" line in `lr_measurements.txt`.
- Glide rows (added on 2026-10-02) have empty `leap_from_PC` and `opcode`, and the outcome `glide`.

### B. Graph building

- **Basic blocks:** one per row of `lr_split_tiles.csv`.
- **Edges from leap rows**, with these rows left out:
  - `JSR` (`$20`) -- the edge into the callee,
  - `RTS` (`$60`), `RTI` (`$40`), `BRK` (`$00`).
  - `JMP` (`$4C`) and branch rows stay.
- **Edges from glide rows:** all of them.
- **Call fall-through edges:** for each `JSR` row, an edge from its source basic block to the basic block starting at `leap_from_PC + 3`, if such a basic block exists. If none exists, the `JSR` never returned during the run: no edge.
- **Scope:** the basic blocks reachable from the `entry` passed in.
- **Known limit:** a `JMP` into another routine (a tail call) pulls that routine's basic blocks into the graph. `LOAD_LEVEL` has no `JMP`.

### C. Dominators (Cooper, Harvey, Kennedy 2001)

- Pure Python, no graph libraries.
- Reverse post-order from `entry`, then iterate `idom(b) = intersect(idom(b), p)` over the processed predecessors `p` of `b` until nothing changes.
- Helper: `dominates(a, b)` -- `a` is `b` or an ancestor of `b` in the `idom` tree.

### D. Natural loops

- A back edge is an edge `S -> T` with `dominates(T, S)`. `T` is the loop header.
- Loop body: `T`, plus every basic block that can reach `S` without passing through `T`.
- Back edges with the same header: one loop, bodies merged.
- Nesting: a loop is nested in another if its body is a strict subset of the other's body.

### E. Loop reports

`lr_loops.csv` -- one row per loop:

| Column | Description |
| :--- | :--- |
| `loop_id` | `L01`, `L02`, ... |
| `header_block` | Start of the header basic block (hex) |
| `back_edge_source_block` | Start of the basic block holding the branch back (hex) |
| `back_edge_count` | How often the back edge was taken |
| `nesting_depth` | `0` for an outermost loop, `1` for a loop inside it, ... |
| `outer_loop_id` | `loop_id` of the enclosing loop, or `-` |
| `member_blocks` | Starts of all member basic blocks, space-separated |

`lr_loop_members.csv` -- one row per basic block:

| Column | Description |
| :--- | :--- |
| `block_start_PC` | Start (hex) |
| `block_end_PC` | End, exclusive (hex) |
| `executions` | From `lr_split_tiles.csv` |
| `innermost_loop` | `loop_id` of the innermost enclosing loop, or `-` |
| `depth` | `0` = in no loop, `1` = in an outermost loop, ... (so `depth = nesting_depth + 1` of the innermost loop) |

---

## 4. Steps

1. **Renames** (section 3.A) in `scripts/lr_tiles.py`. You run `make lr-tiles`.
2. **`workbench/tiling.py`:** move the tiling code there. `lr_tiles.py` uses it and writes to `tmp/lr_tiles/`. You run `make lr-tiles`; the reports must be unchanged apart from the folder.
3. **`workbench/basic_blocks_analysis.py`:** graph, dominators, natural loops, loop reports. Tested on small hand-made graphs, and on the fixture split reports (section 6). **The first run on `LOAD_LEVEL` is the milestone: you run it.**
4. **`scripts/lr_basic_blocks_analysis.py`** and the integration test (section 6).

---

## 5. Ground truth: `LOAD_LEVEL` (`$6238`)

Checked against the split reports of the 4,000,000-instruction run (2026-10-02, before the renames). The member sets were worked out by hand from the listing and the edges; check them before relying on them.

| Oracle label | Header | Back edge | Branch at | Taken | Header executions | Nesting depth | Members |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `.loop1` | `6252` | `6252 -> 6252` | `$6256` | 30 | 31 | 0 | `6252` |
| `.loop2` | `625a` | `625a -> 625a` | `$625e` | 5 | 6 | 0 | `625a` |
| `.row_loop` | `6269` | `62a8 -> 6269` | `$62ae` | 15 | 16 | 0 | `6269 627e 6288 628c 6292 629c 62a8` |
| `.col_loop` | `627e` | `629c -> 627e` | `$62a6` | 432 | 448 | 1, in `.row_loop` | `627e 6288 628c 6292 629c` |

Edges in `LOAD_LEVEL` that need sections 3.A and 3.B:

- Glides: `6238 -> 6252` (1), `6258 -> 625a` (1), `6267 -> 6269` (1), `6269 -> 627e` (16), `628c -> 6292` (224).
- Call fall-through edges: `6260 -> 6267` (`JSR` at `$6264`), `62b0 -> 62b3` (`JSR` at `$62b0`).
- Without the glides, `$6252` is not reachable from `$6238`.

The oracle grades; it never feeds the tools.

---

## 6. Tests

- **Unit tests** for `workbench/basic_blocks_analysis.py`: the graph builder (glide edges, call fall-through edges, left-out rows), dominators on a small graph, natural loops and nesting on a small graph.
- **Analysis on fixtures:** run `workbench/basic_blocks_analysis.py` on the fixture split reports. Check the four loops of section 5. No `Emulator` needed.
- **Integration test:** runs the `Emulator` with tiling and analysis and writes all reports to `tmp/reports/test_<name>/`:
  - `lr_unbroken_tiles.csv`, `lr_unbroken_transitions.csv`, `lr_split_tiles.csv`, `lr_split_transitions.csv`,
  - `lr_loops.csv`, `lr_loop_members.csv`.
  - Each is compared with its golden in `tests/fixtures/<test name>/`.
  - Takes about 5 s. Needs `LODE_RUNNER.BIN`, which is not in git, so it skips when the file is missing. Could be marked manual.
- **Precondition for goldens:** two runs produce identical reports. Check before creating the goldens.
- The goldens are created after steps 1 and 2, so they have the new names and the glide rows.

---

## 7. Open questions

- Where `LOAD_LEVEL.lst` lives. It is a grading fixture, but it is Xekri's work from `a2-lode-runner`.
- Whether the `lr_` prefix stays in report file names once reports live in a folder per script.
- How the goldens are refreshed when a report changes on purpose.
- Later: how an analysis package states which instrumentation package it needs upstream.

## 8. Out of scope

- IPython and the workbench session.
- The stretch container.
- A folder structure for experiments.
