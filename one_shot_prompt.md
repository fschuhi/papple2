# This session: one-shot mode

For this session I suspend parts of `CRITICAL_RULES.md` and `LLM_INSTRUCTIONS.md`. I will not follow the work step by step, and I don't need to understand each step as it happens. Work on your own and deliver the result in one go. If you are blocked, take the most reasonable choice, note it in the final report, and go on; ask me only if nothing reasonable is left.

## Suspended for this session

- Rule 1 (no unsolicited files): create and change the files named under "Deliverables" without asking.
- Rule 3 (Discuss -> Approve -> Implement) and Rule 4 (step by step): no proposals, no waiting for approval.
- Rule 7 (inventory first): not needed.
- Rule 8, as far as "tools check claims, never make progress" goes: you may use tools to do the work, e.g. throwaway scripts that read the listing and the reports, compute, and write the deliverables. Still announce each tool use in one line.
- From `docs/structures_handover.md`, "How to work in that session": "I lead the reading", "one structure at a time" and the explain-back checks.
- Rule 2's "only the agreed change" for `docs/lr_structures.md`: you may reorder and rewrite it (see "Deliverables").

## Still in force

- Rule 9: never change `manifest.lst`.
- Stay inside the filesdump: fetch nothing from GitHub or the web. If something is missing, work around it and name it in the final report.
- No `papple2` code: change nothing in `src/`, `tests/` or `scripts/`. Throwaway scripts in your own workspace are fine; they are not deliverables.
- The output standards of `LLM_INSTRUCTIONS.md`: no hard-wrapped prose, ASCII typography, filenames in backticks, no inline citations, "one name, one thing". The terms in `docs/lr_structures.md`, section "Terms", stay as they are.
- Honesty: mark everything that was read rather than computed, or guessed rather than checked.
- Nothing beyond the listed deliverables. Any other finding goes into the final report, one line each, unexpanded.

## The goal

`docs/lr_structures.md` serves one purpose: a target against which `papple2`'s dynamic routine detection (`find_routines()` in `src/papple2/workbench/basic_blocks_analysis.py`, with the targets of stack jumps as extra entries) is graded and then improved. That detection only ever sees what ran. So keep strictly apart what ran in the attract play (`lr_split_tiles.csv`, `lr_split_transitions.csv`) and what only exists in Xekri's source. Paths that ran 0 times may be documented, always marked as such; the answer key and the grading use only what ran.

The dossier (`dossiers/lode_runner/annotations.json`) now carries Xekri's labels; the reports in `docs/reports/` were written before that and still show `routine_xxxx`.

## Deliverables

1. **The answer key, computed, for the whole run** (new file `docs/lr_answer_key.csv`): one row per block of `lr_split_tiles.csv`, with the Xekri subroutine whose span it lies within, taken from Xekri's `SUBROUTINE` marks in `docs/listings/listing_clean.tsv`. Columns at least: `block_start`, `block_end`, `executions`, `xekri_subroutine`, `xekri_start`, `note`. Where a block lies under a label without a `SUBROUTINE` mark (e.g. `MAIN`, `INIT_GAME_DATA`, `LONG_DELAY`) or in the relocation code that runs before it is moved, decide how to treat it, say how in `docs/lr_structures.md`, and keep it consistent.
2. **Part 1 completed** for the pilot: the 7 rows still to do (see the Status section of `docs/lr_structures.md`), in the same columns as the existing rows.
3. **Part 2 completed**: entries 2 to 6 with all eight parts, in the form of entry 1. Part 6 of each entry lists alternatives, not a decision. Part 8 states the explain-back question and leaves the answer open.
4. **Part 3**: grade `find_routines()` against the answer key, for the whole run: (a) partition: does every block that ran belong to exactly one routine? (b) agreement: for each Xekri subroutine with blocks that ran, is there one routine whose blocks are exactly those blocks? Give the numbers, and list every disagreement with its reason, using the structures of Part 2. Then propose a rule in words that uses only what a run can see, grade it the same way (by a throwaway script that applies the rule to the reports, or on paper; say which), and list where it still disagrees and why.
5. **`docs/lr_structures.md` made readable**: a short "How to read this document" at the top (a few lines), then Status, Terms, the map, Parts 1 to 3; Part 4 and the side findings ("Traces of how the code was written", "Corrections and additions to Xekri's documentation", "Ideas for `papple2`") move to the end as appendices. Keep their content.
6. **A final report in the chat**: what was done; what was computed, what was read, what is uncertain; the choices taken where blocked; what the next session, the one that changes `papple2`'s routine detection, should start with.
