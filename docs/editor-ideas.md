# Listing editor -- ideas

Ideas for the listing editor (`papple2.workbench.listing_editor_prompt_toolkit`, opened by `edit()`). Once an idea is concrete enough to start, it gets an item in `TODO.md` that points here. Settled decisions are in `docs/decisions.md`; the editor's keys are in the module's docstring.

---

## 1. Window Management & Layout

*   **Dynamic Resizing:** Keyboard shortcuts to expand or shrink the number of visible rows on the fly.

## 2. Structural Navigation & Deep Traversal

*   **Semantic Jumping:** Keyboard shortcuts to move the active row forward or backward to the next/previous leap, block, loop header, or loop fallthrough.
*   **RTS Resolution:** When on an `RTS`, query the shadow stack (`StackTracking`, `lr_returns.csv`) for all recorded return destinations, and present them as leap targets in a floating window over the listing. Selecting one leaps there, like Enter on a `JSR`.
*   **Routine Navigation:** Shortcuts to jump to the top or bottom of the current routine.
*   **Jump Station:** A dedicated modal or panel to register, organize, and instantly leap to meaningful targets (routines, stretches, labels). Jumping pushes the current location to breadcrumbs and centers the active row cursor on the target.

## 3. Editing Mechanics & SourceGen Inspirations

*   **Data Operand Formatting (SourceGen-style):** Highlight a raw data block and format it as `.word` pointers, `.byte` tables, or ASCII strings. Auto-generate labels for pointer targets.
*   **Offset Math (`label+1`):** Support rendering 16-bit zero-page fetches as `LDA target` and `LDA target+1` rather than requiring distinct labels for the high byte. The dossier has such a pair today: `zp_hgr1_row_ptr` and `zp_hgr1_row_ptr_hi`.

## 4. Visuals & Rule Engines

*   **Live Highlighting Rules:** Shortcuts to toggle semantic highlights on the fly (e.g., highlight all zero-page accesses, all tabled reads). Once there are several such rules: a general way to define and apply them, without hardcoding them into the display logic.
*   **Color Ranges (Taint Analysis):** Assign colors to specific address ranges, in the hexdump, `listing()` and `edit()`. `color("sprites", start, end, "red")` sets a range by a string ID (again with the same ID: replaced), `colors()` lists them, `uncolor("sprites")` removes one. Start and end as addresses or labels, kept as addresses; colors by name (`red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`). A byte in two or more ranges gets the one overlap color, `overlap_color("magenta")`. Kept in `annotations.json`, a third section, so the colors persist across `hexdump()`, `listing()` and `edit()`. In the listing, the hex bytes are colored byte by byte; in the editor, widths must be counted without the color codes.
*   **Hotness Indicators:** Use font weighting (bold) or dimming (Bayesian focus) to visually indicate execution counts. Less-hot paths fade into the background.
*   **Folding:** Collapse and expand labelled loops to hide detail. A loop with a label (`.loop1`) folds to one row, e.g. `> .loop1`, `>>` for depth; folding an outer loop hides its inner ones, since natural loops are either nested or disjoint. Blocks are too small to be worth folding, and only entities with a label can be folded. Shortcuts to "expand all" and "collapse all". Before building: folding hides a contiguous stretch of rows, but a loop's blocks are a set, so check that each loop spans a contiguous range in the listing. Saving folds in the dossier: low priority, a new session may well want to see everything.

## 5. Structural & Vertical Search

*   **Vertical Regex:** Support regular expressions that span multiple rows (e.g., finding a `PHA` followed by another `PHA` within a 3-line window).
*   **Inbound/Outbound Querying:** Search for all routines that `JSR` into the current routine, or all routines the current routine calls. At the prompt, `show_callers()` already does the inbound half; in the editor, e.g. on a routine's entry row.
*   **Scope Toggles:** Run searches locally (within the currently viewed routine) or globally (across all known routines and stretches).

## 6. Stretches (Overlapping Regions)

The editor's side of "Routines as stretches" in `GOALS.md`.

*   **Definition:** A stretch is a persistent, address-bound volume in the dossier defined by a contiguous `[start_address, end_address]` range. Unlike dynamic routines, it explicitly claims a region of memory and survives across runs.
*   **Stretches as Layers:** Stretches are treated as contextual tags applied to addresses, not structural containers. They are visualized using the left margin (the gutter) via colored vertical lines (`│`, `║`).
*   **Contextual Panel:** When the cursor enters a stretch, a dedicated UI panel/status bar displays the documentation, parameters, and side-effects bound to that stretch.
*   **Persistent & Manual:** Once created, a stretch is a durable artifact. It is never altered as a side-effect of a new dynamic run. Divergences between a stretch and a new run offer semi-automatic "resize suggestions".
*   **Literate Programming Tie-in:** Stretches map to the "chunks" of code that will eventually be tangled or woven into narrative documentation (noweb).
