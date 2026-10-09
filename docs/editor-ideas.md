# Listing editor -- ideas

Ideas for the listing editor (`papple2.workbench.listing_editor`, opened by `edit()`). Once an idea is concrete enough to start, it gets an item in `TODO.md` that points here. Settled decisions are in `docs/decisions.md`; the editor's keys are in the module's docstring.

---

## 1. Window Management & Layout

*   **Dynamic Resizing:** Keyboard shortcuts to expand or shrink the number of visible rows on the fly.

## 2. Structural Navigation & Deep Traversal

*   **Semantic Jumping:** Keyboard shortcuts to move the active row forward or backward to the next/previous leap, block, loop header, or loop fallthrough.
*   **RTS Resolution:** When on an `RTS`, query the shadow stack (`StackTracking`, `lr_returns.csv`) for all recorded return destinations, and present them as leap targets in a floating window over the listing. Selecting one leaps there, like Enter on a `JSR`.
*   **Routine Navigation:** Shortcuts to jump to the top or bottom of the current routine.
*   **Jump Station:** A dedicated modal or panel to register, organize, and instantly leap to meaningful targets (routines, stretches, labels). Jumping pushes the current location to breadcrumbs and centers the active row cursor on the target. *(First step done 2026-10-08: Go To, `g`, a picker with every routine of the run. The picker is meant for every list of places: callers, the targets of an `RTS`, the paths into a watched range. Callers with `u` since 2026-10-09.)*

## 3. Editing Mechanics & SourceGen Inspirations

*   **Data Operand Formatting (SourceGen-style):** Highlight a raw data block and format it as `.word` pointers, `.byte` tables, or ASCII strings. Auto-generate labels for pointer targets.

## 4. Visuals & Rule Engines

*   **Live Highlighting Rules:** Shortcuts to toggle semantic highlights on the fly (e.g., highlight all zero-page accesses, all tabled reads). Once there are several such rules: a general way to define and apply them, without hardcoding them into the display logic.
*   **Persistent Color Ranges:** Built 2026-10-09. Named, half-open ranges live in the dossier's `colors.json`, separate from labels/comments and hidden ranges. `color(name, start, end, shade)` adds or replaces a definition, `colors()` lists them, and `uncolor(name)` removes one. `color("sprites", *to_range("r_11x2_1"), "blue")` saves a routine's existing listing bounds. Supported shades are red, green, yellow, blue, magenta, cyan and white. Overlaps with equal shades retain their color; different shades return the fixed mix color magenta. One shared store supplies lookup; each view decides how to render it. These are presentation classifications, not taint analysis.
*   **Breadcrumb Colors:** Built 2026-10-09. Past, current and future names use their assigned colors, only the current one bold; uncolored names, separators and abbreviations are gray. A title gets the color of definitions containing its whole displayed range, not partial coverage. The editor receives a callback and knows nothing about dossier persistence. No per-line location coloring or new gutter marker: breadcrumbs provide the grouping while instruction text stays available for later operand and syntax colors.
*   **Listing Location Colors:** Built 2026-10-09. Long `listing()` output colors each addressed row by its starting address: address, bytes, label and instruction, including operands and `.byte` contents. Comments, arrows and collapsed rows retain their normal appearance. IPython receives a colored display version; the returned string and clipboard text remain plain. The listing and editor deliberately use different presentations.
*   **Referenced-Operand Colors:** Next: color an operand by the address it names, independently of where the instruction lives. Preserve brackets, indexes, shortened local labels and offsets; immediates are values, not addresses. In the editor, color the operand without coloring the whole line. In the listing, settle precedence over the existing location color before implementation. Actual runtime read/write destinations are separate instrumentation work.
*   **Other Color Views:** Graphviz node colors and the static memory map are next consumers of the same store; see `TODO.md`, "Coloring and memory map". Hexdump byte colors remain later work. Map-cell aggregation must be designed separately from breadcrumb containment lookup.
*   **Hotness Indicators:** Use font weighting (bold) or dimming (Bayesian focus) to visually indicate execution counts. Less-hot paths fade into the background.
*   **Folding:** Collapse and expand labelled loops to hide detail. A loop with a label (`.loop1`) folds to one row, e.g. `> .loop1`, `>>` for depth; folding an outer loop hides its inner ones, since natural loops are either nested or disjoint. Blocks are too small to be worth folding, and only entities with a label can be folded. Shortcuts to "expand all" and "collapse all". Before building: folding hides a contiguous stretch of rows, but a loop's blocks are a set, so check that each loop spans a contiguous range in the listing. Saving folds in the dossier: low priority, a new session may well want to see everything.

## 5. Structural & Vertical Search

*   **Vertical Regex:** Support regular expressions that span multiple rows (e.g., finding a `PHA` followed by another `PHA` within a 3-line window).
*   **Inbound/Outbound Querying:** Search for all routines that `JSR` into the current routine, or all routines the current routine calls. At the prompt, `show_callers()` does the inbound half; in the editor, `u` (2026-10-09). Open: the outbound half.
*   **Scope Toggles:** Run searches locally (within the currently viewed routine) or globally (across all known routines and stretches).

## 6. Stretches (Overlapping Regions)

The editor's side of "Routines as stretches" in `GOALS.md`.

*   **Definition:** A stretch is a persistent, address-bound volume in the dossier defined by a contiguous `[start_address, end_address]` range. Unlike dynamic routines, it explicitly claims a region of memory and survives across runs.
*   **Stretches as Layers:** Stretches are treated as contextual tags applied to addresses, not structural containers. They are visualized using the left margin (the gutter) via colored vertical lines (`│`, `║`).
*   **Contextual Panel:** When the cursor enters a stretch, a dedicated UI panel/status bar displays the documentation, parameters, and side-effects bound to that stretch.
*   **Persistent & Manual:** Once created, a stretch is a durable artifact. It is never altered as a side-effect of a new dynamic run. Divergences between a stretch and a new run offer semi-automatic "resize suggestions".
*   **Literate Programming Tie-in:** Stretches map to the "chunks" of code that will eventually be tangled or woven into narrative documentation (noweb).
