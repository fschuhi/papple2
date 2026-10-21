# UI ideas

Ideas for reading code with `papple2`: the listing editor (`papple2.workbench.listing_editor`, opened by `edit()`), the views at the prompt, and the windows that may come next to them. Once an idea is concrete enough to start, it gets an item in `TODO.md` that points here. What is built is described in `docs/workbench.md`, not here.

---

## 1. Windows

The IPython prompt stays the command center. Next to it, floating windows look into the same run, several at once, each a view of its own:

*   **Viewer:** a windowed `edit()`. The same rows, the same keys, read-only first; labels and comments come later. Several viewers open at once, each on its own routine, so two routines can be read side by side.
*   **Thumbnail:** a picture of an address range, the whole run or one table, one cell per N bytes, zoomed smoothly with the mouse wheel down to single bytes. A click opens the address in a viewer. Several thumbnails at once.
*   **Hex viewer:** `hexdump()` in a window, following the viewer's bar or standing on its own.
*   **Routine graph, live:** today's `show_routine_graph()` as a drawing of its own instead of a Graphviz picture: Graphviz still lays it out (`dot -Tjson` gives the positions), the window draws the boxes and arrows itself, so a box can be clicked, filled by a brush, or dimmed, and the neighbourhood of one routine can be shown alone.
*   **Color maps:** `memory_map()` in a window, zoomable like the thumbnail; later heatmaps, with the lessons from Robotron ([`DIRECTION.md`](DIRECTION.md), "Lessons from Robotron"): binary marks first, counts only on a log or rank scale.
*   **Toolkit:** Tkinter first, because it is in the standard library and IPython's `%gui tk` keeps the windows alive while the prompt stays usable, without threads. The windows know only the `Session`; if Tkinter is not good enough, another toolkit replaces one module.
*   **Every window draws from the `Session`**, from the reports and the memory the run left, never from the running machine. The pygame window keeps its own loop.
*   **Keyboard first:** the gestures of the editor (Enter, Backspace, `g`, `u`) work the same in every window, and small input forms take a range, a label or a question.

## 2. Brushing

A brush is a question answered by the run and painted in every window at once: "which routines touch HGR?" paints `draw_at_hx`, `erase_at_hx`, the page copy and the clear in red, in the thumbnail, in the gutter of every viewer, in the routine graph.

*   **Shape:** a question in, a set of addresses out. The first brushes come from the cross reference (`lr_xrefs.csv`): `touches(range)`, for reads, writes or both, is the HGR question; `calls_into(routine)` and `called_by(routine)` come from the routine graph. A brush is a gesture: one key, one form, one color.
*   **Two kinds of color, two looks.** A color range from the dossier is a decision of mine ("sprites are blue"); a brush is what the run found. They must not look alike: the dossier's colors stay where they are today (operands, breadcrumbs, map cells); a brush is a thick colored line in the gutter of the viewer and a filled cell in the thumbnail.
*   **Participation, not purpose.** A red routine touched HGR; why, the reading has to tell. Marks, not counts.
*   **One run at a time.** A brush knows only what ran. More runs, with the player moving in all four directions, uncover more code; the dossier is the layer that persists across runs.
*   **Brushes to keep:** every brush should give a picture worth a page in the Book. If it does not, it is not needed.

## 3. Navigation

*   **Semantic Jumping:** Keyboard shortcuts to move the active row forward or backward to the next/previous leap, block, loop header, or loop fallthrough.
*   **RTS Resolution:** When on an `RTS`, query the shadow stack (`StackTracking`, `lr_returns.csv`) for all recorded return destinations, and present them as leap targets in a floating window over the listing. Selecting one leaps there, like Enter on a `JSR`.
*   **Routine Navigation:** Shortcuts to jump to the top or bottom of the current routine.
*   **Jump Station:** A dedicated modal or panel to register, organize, and instantly leap to meaningful targets (routines, stretches, labels). Jumping pushes the current location to breadcrumbs and centers the active row cursor on the target. Today: `g`, a picker with every routine of the run, and `u` with every way into the routine shown. The picker is meant for every list of places: the targets of an `RTS`, the paths into a watched range.
*   **Dynamic Resizing:** Keyboard shortcuts to expand or shrink the number of visible rows on the fly.

## 4. Editing

*   **Data Operand Formatting (SourceGen-style):** Highlight a raw data block and format it as `.word` pointers, `.byte` tables, or ASCII strings. Auto-generate labels for pointer targets.

## 5. Visuals and rules

*   **Live Highlighting Rules:** Shortcuts to toggle semantic highlights on the fly (e.g., highlight all zero-page accesses, all tabled reads). Once there are several such rules: a general way to define and apply them, without hardcoding them into the display logic. A brush (section 2) is such a rule, answered by the run instead of by the code's text.
*   **Operand colors in `listing()`:** `edit()` colors the name in an operand by the address it names; `listing()` does not yet. Settle first whether the target color or the location color wins on the operand.
*   **One color manager:** `LISTING_COLORS`, `MAP_BACKGROUNDS`, `MAP_LETTERS` and the editor's `f"ansi{shade}"` through one function in `colors.py`, taking a name or `#rrggbb`. Needed before windows: a window draws any color, and seven shades are too few (HGR1, HGR2 and the ROM alone would take three).
*   **Hotness Indicators:** Use font weighting (bold) or dimming (Bayesian focus) to visually indicate execution counts. Less-hot paths fade into the background.
*   **Folding:** Collapse and expand labelled loops to hide detail. A loop with a label (`.loop1`) folds to one row, e.g. `> .loop1`, `>>` for depth; folding an outer loop hides its inner ones, since natural loops are either nested or disjoint. Blocks are too small to be worth folding, and only entities with a label can be folded. Shortcuts to "expand all" and "collapse all". Before building: folding hides a contiguous stretch of rows, but a loop's blocks are a set, so check that each loop spans a contiguous range in the listing. Saving folds in the dossier: low priority, a new session may well want to see everything.

## 6. Search

*   **Vertical Regex:** Support regular expressions that span multiple rows (e.g., finding a `PHA` followed by another `PHA` within a 3-line window).
*   **Inbound/Outbound Querying:** Search for all routines that `JSR` into the current routine, or all routines the current routine calls. At the prompt, `show_callers()` does the inbound half; in the editor, `u`. Open: the outbound half.
*   **Scope Toggles:** Run searches locally (within the currently viewed routine) or globally (across all known routines and stretches).

## 7. Stretches

The editor's side of "Routines as stretches" in `GOALS.md`.

*   **Definition:** A stretch is a persistent, address-bound volume in the dossier defined by a contiguous `[start_address, end_address]` range. Unlike dynamic routines, it explicitly claims a region of memory and survives across runs.
*   **Stretches as Layers:** Stretches are treated as contextual tags applied to addresses, not structural containers. They are visualized using the left margin (the gutter) via colored vertical lines (`│`, `║`), like a brush that persists.
*   **Contextual Panel:** When the cursor enters a stretch, a dedicated UI panel/status bar displays the documentation, parameters, and side-effects bound to that stretch.
*   **Persistent & Manual:** Once created, a stretch is a durable artifact. It is never altered as a side-effect of a new dynamic run. Divergences between a stretch and a new run offer semi-automatic "resize suggestions".
*   **Literate Programming Tie-in:** Stretches map to the "chunks" of code that will eventually be tangled or woven into narrative documentation (noweb).

## 8. Later

*   **Time machine slices:** once an instrumentation records the run in slices, every window shows the slice chosen on a timeline, and the pygame window too: the display is a function of memory and the soft switches, so a slice's memory can be drawn on demand, without the emulator's loop running.
