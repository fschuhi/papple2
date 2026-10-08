# Implementation Roadmap: Inline Listing Editor

**Goal:** Replace the `readline`-based `edit()` loop with an inline, interactive `prompt_toolkit` application. It must render below the IPython prompt without stealing the alternate screen buffer, preserve scrollback context, and vanish upon exit, leaving only a cropped `Out` log.

## Phase 1: The Inline Shell & Erase-on-Exit
1. **Application Scaffolding:** Create a `prompt_toolkit.Application` with `full_screen=False`. 
2. **Layout Definition:** Define an `HSplit` containing:
   * A breadcrumb `Window` (1 row).
   * A listing `Window` (dynamically sized, e.g., max 30 rows).
   * A status `Window` (1 row).
3. **Erase on Exit:** Use `erase_when_done=True` (or manual terminal ANSI clears) so that when the `Application.run()` loop finishes, the interactive UI completely disappears from the terminal.
4. **Crop & Capture:** Make `edit()` return the currently visible disassembled rows as a string so IPython captures it as `Out[n]`.

## Phase 2: Navigation & High-Visibility Cursor
1. **Editor State:** Create a state object tracking `current_address` and `view_top_address`. 
2. **Key Bindings (Vertical):** Bind `Up`, `Down`, `PageUp`, and `PageDown`. These update `current_address` and adjust `view_top_address` to keep the cursor on screen.
3. **Row Highlighting:** In the `FormattedText` generator that feeds the listing `Window`, apply the `reverse` style tag to the entire row that matches `current_address` to create a high-visibility cursor.

## Phase 3: Leap Following & Breadcrumbs
1. **Breadcrumb State:** Add a `breadcrumb_stack` list to the state. Each entry stores `(routine_entry_address, cursor_address, view_top_address)`.
2. **The Leap (Enter):** Bind the `Enter` key. 
   * When pressed on a valid jump target (`JSR`, `JMP`, branch), push the current state to the `breadcrumb_stack`.
   * Update the UI state to load the new routine and set the cursor to its entry point.
3. **The Return (Backspace):** Bind `Backspace` or `<`.
   * Pop the top entry from the `breadcrumb_stack`.
   * Restore the routine, the `cursor_address`, and the `view_top_address` exactly as they were.
4. **Breadcrumb UI:** Update the top `Window` to render the stack (e.g., ` LOAD_LEVEL > routine_8438 > r_11x2_1 `).

## Phase 4: In-Place Editing Mechanics (Tab-Jumping)
1. **In-Place Overlays:** Instead of a bottom command bar, use `prompt_toolkit.layout.FloatContainer` to float editable `TextArea` widgets directly over the label and comment columns of the active row.
2. **Tab Navigation:** Bind `Tab` to shift focus between the label float, the comment float, and the main listing window.
3. **Committing:** Bind `Enter` within the floats to save the text to the `Annotations` dossier, hide the floats, and redraw the listing. 

## Phase 5: RTS Jump Station
1. **Target Querying:** When the cursor is on an `RTS`, query the `StackTracking` graph for all recorded return destinations.
2. **Modal Overlay:** Display these targets in a floating `Window`. Allow the user to select one to execute a leap.

---

# Editor & UI Feature Backlog

## 1. Window Management & Layout
*   **Inline Terminal UI:** The editor renders below the prompt and erases itself cleanly upon exit, eliminating screen clutter while preserving scrollback.
*   **Window Elements:** Clear visual distinction between the area above the code (breadcrumbs) and below it (status bar)[cite: 6].
*   **Dynamic Resizing:** Keyboard shortcuts to expand or shrink the number of visible rows on the fly[cite: 6].
*   **Crop and Capture:** A shortcut to exit `edit()` and return the currently viewed lines as an `Out` object, allowing you to crop to a specific area and pipe it to `clip()`[cite: 6].

## 2. Structural Navigation & Deep Traversal
*   **High-Visibility Cursor:** Use an inverted text style (classic DOS style) or a distinct background color for the entire active row to provide an immediate, unambiguous sense of location[cite: 6].
*   **Semantic Jumping:** Keyboard shortcuts to move the active row forward or backward to the next/previous leap, block, loop header, or loop fallthrough[cite: 6].
*   **Static Leap Following:** Press a key (e.g., `Enter`) on a `JSR`/`JMP` or branch to open the target routine in place. The previous routine pushes onto a breadcrumb stack[cite: 6].
*   **Return to Caller:** Jump back from a routine (e.g., `Backspace`), popping the breadcrumb stack and restoring the exact window state and cursor position (ensuring the `>` active row remains visible)[cite: 6].
*   **RTS Resolution:** When on an `RTS`, query the shadow stack/structure graph for known jump sources and present them as leap targets[cite: 6].
*   **Routine Navigation:** Shortcuts to jump to the top or bottom of the current routine[cite: 6].
*   **Jump Station:** A dedicated modal or panel to register, organize, and instantly leap to meaningful targets (routines, stretches, labels). Jumping pushes the current location to breadcrumbs and centers the active row cursor on the target[cite: 6].

## 3. Editing Mechanics & SourceGen Inspirations
*   **In-Place Editing:** Tab between label and comment fields directly on the active row using floating input buffers. Supports multi-line comments[cite: 6].
*   **Data Operand Formatting (SourceGen-style):** Highlight a raw data block and format it as `.word` pointers, `.byte` tables, or ASCII strings. Auto-generate labels for pointer targets[cite: 6].
*   **Offset Math (`label+1`):** Support rendering 16-bit zero-page fetches as `LDA target` and `LDA target+1` rather than requiring distinct labels for the high byte[cite: 6].
*   **Local Labels:** Support routine-bounded local labels (e.g., `.loop1`) to keep the global namespace clean[cite: 6].
*   **Breadcrumb Integrity:** Prevent deleting or renaming a label if it is currently active in the breadcrumb path[cite: 6].

## 4. Visuals & Rule Engines
*   **Live Highlighting Rules:** Shortcuts to toggle semantic highlights on the fly (e.g., highlight all zero-page accesses, all tabled reads)[cite: 6].
*   **Color Ranges (Taint Analysis):** Assign colors to specific address ranges. Requires cross-command state management so colors persist across `hexdump` and `listing`[cite: 6].
*   **Hotness Indicators:** Use font weighting (bold) or dimming (Bayesian focus) to visually indicate execution counts. Less-hot paths fade into the background[cite: 6].
*   **Extensible Rule Engine:** A generalized way to define and apply coloring/highlighting rules without hardcoding them into the display logic[cite: 6].
*   **Folding:** Collapse and expand named blocks or loops to hide detail. Shortcuts to "expand all" and "collapse all". Only entities with a label can be folded[cite: 6].

## 5. Structural & Vertical Search
*   **Vertical Regex:** Support regular expressions that span multiple rows (e.g., finding a `PHA` followed by another `PHA` within a 3-line window)[cite: 6].
*   **Inbound/Outbound Querying:** Search for all routines that `JSR` into the current routine, or all routines the current routine calls[cite: 6].
*   **Scope Toggles:** Run searches locally (within the currently viewed routine) or globally (across all known routines and stretches)[cite: 6].

## 6. Stretches (Overlapping Regions)
*   **Definition:** A stretch is a persistent, address-bound volume in the dossier defined by a contiguous `[start_address, end_address]` range. Unlike dynamic routines, it explicitly claims a region of memory and survives across runs[cite: 6].
*   **Stretches as Layers:** Stretches are treated as contextual tags applied to addresses, not structural containers. They are visualized using the left margin (the gutter) via colored vertical lines (`│`, `║`)[cite: 6].
*   **Contextual Panel:** When the cursor enters a stretch, a dedicated UI panel/status bar displays the documentation, parameters, and side-effects bound to that stretch[cite: 6].
*   **Persistent & Manual:** Once created, a stretch is a durable artifact. It is never altered as a side-effect of a new dynamic run. Divergences between a stretch and a new run offer semi-automatic "resize suggestions"[cite: 6].
*   **Literate Programming Tie-in:** Stretches map to the "chunks" of code that will eventually be tangled or woven into narrative documentation (noweb)[cite: 6].
