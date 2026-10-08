# Editor & UI Feature Backlog

This document captures the brainstorming for the next generation of the `papple2` workbench UI, specifically evolving `edit()` into a structural, navigable, terminal-based interface using `prompt_toolkit`.

## 1. Window Management & Layout
*   **Modal Terminal UI:** The editor opens its own full-screen terminal buffer and restores the original shell cleanly upon exit (like `fzf` or `less`), eliminating screen clutter.
*   **Window Elements:** Clear visual distinction between the area above the code (breadcrumbs) and below it (status bar/command input).
*   **Dynamic Resizing:** Keyboard shortcuts to expand or shrink the number of visible rows on the fly.
*   **Crop and Capture:** A shortcut to exit `edit()` and return the currently viewed lines as an `Out` object, allowing you to crop to a specific area and pipe it to `clip()`.

## 2. Structural Navigation & Deep Traversal
*   **High-Visibility Cursor:** Use an inverted text style (classic DOS style) or a distinct background color for the entire active row to provide an immediate, unambiguous sense of location.
*   **Semantic Jumping:** Keyboard shortcuts to move the active row forward or backward to the next/previous leap, block, loop header, or loop fallthrough.
*   **Static Leap Following:** Press a key (e.g., `Enter`) on a `JSR`/`JMP` or branch to open the target routine in place. The previous routine pushes onto a breadcrumb stack.
*   **Return to Caller:** Jump back from a routine (e.g., `Backspace`), popping the breadcrumb stack and restoring the exact window state and cursor position (ensuring the `>` active row remains visible).
*   **RTS Resolution:** When on an `RTS`, query the shadow stack/structure graph for known jump sources and present them as leap targets.
*   **Routine Navigation:** Shortcuts to jump to the top or bottom of the current routine.
*   **Jump Station:** A dedicated modal or panel to register, organize, and instantly leap to meaningful targets (routines, stretches, labels). Jumping pushes the current location to breadcrumbs and centers the active row cursor on the target.

## 3. Editing Mechanics & SourceGen Inspirations
*   **Vim-Style Input:** Pressing `c` (comment) or `l` (label) focuses a bottom command bar for input, preserving the listing's horizontal layout. Supports multi-line comments.
*   **Data Operand Formatting (SourceGen-style):** Highlight a raw data block and format it as `.word` pointers, `.byte` tables, or ASCII strings. Auto-generate labels for pointer targets.
*   **Offset Math (`label+1`):** Support rendering 16-bit zero-page fetches as `LDA target` and `LDA target+1` rather than requiring distinct labels for the high byte.
*   **Local Labels:** Support routine-bounded local labels (e.g., `.loop1`) to keep the global namespace clean.
*   **Breadcrumb Integrity:** Prevent deleting or renaming a label if it is currently active in the breadcrumb path.

## 4. Visuals & Rule Engines
*   **Live Highlighting Rules:** Shortcuts to toggle semantic highlights on the fly (e.g., highlight all zero-page accesses, all tabled reads).
*   **Color Ranges (Taint Analysis):** Assign colors to specific address ranges. Requires cross-command state management so colors persist across `hexdump` and `listing`.
*   **Hotness Indicators:** Use font weighting (bold) or dimming (Bayesian focus) to visually indicate execution counts. Less-hot paths fade into the background.
*   **Extensible Rule Engine:** A generalized way to define and apply coloring/highlighting rules without hardcoding them into the display logic.
*   **Folding:** Collapse and expand named blocks or loops to hide detail. Shortcuts to "expand all" and "collapse all". Only entities with a label can be folded.

## 5. Structural & Vertical Search
*   **Vertical Regex:** Support regular expressions that span multiple rows (e.g., finding a `PHA` followed by another `PHA` within a 3-line window).
*   **Inbound/Outbound Querying:** Search for all routines that `JSR` into the current routine, or all routines the current routine calls.
*   **Scope Toggles:** Run searches locally (within the currently viewed routine) or globally (across all known routines and stretches).

## 6. Stretches (Overlapping Regions)
*   **Definition:** A stretch is a persistent, address-bound volume in the dossier defined by a contiguous `[start_address, end_address]` range. Unlike dynamic routines, it explicitly claims a region of memory and survives across runs.
*   **Stretches as Layers:** Stretches are treated as contextual tags applied to addresses, not structural containers. They are visualized using the left margin (the gutter) via colored vertical lines (`│`, `║`).
*   **Contextual Panel:** When the cursor enters a stretch, a dedicated UI panel/status bar displays the documentation, parameters, and side-effects bound to that stretch.
*   **Persistent & Manual:** Once created, a stretch is a durable artifact. It is never altered as a side-effect of a new dynamic run. Divergences between a stretch and a new run offer semi-automatic "resize suggestions".
*   **Literate Programming Tie-in:** Stretches map to the "chunks" of code that will eventually be tangled or woven into narrative documentation (noweb).
