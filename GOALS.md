# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` or `CHANGELOG.md`(on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** M7.5 (the Robotron + Excel carve-out) is done. `probotron` exists as its own repo, pushed to GitHub -- the workbench, the PyXLL/Excel bridge, and their supporting data/docs now live there, depending on `papple2` as an editable local package; the Excel bridge is verified working from Excel via PyXLL. `papple2`'s own side of the split -- deleting the now-migrated files from this repo, dropping `pyxll`/the Windows branch from `requirements.txt`/`Makefile`/`manifest.lst` -- is in progress. `MIGRATE_ROBOTRON.md` has been deleted now that the migration it planned is complete; see `HISTORY.md` if its reasoning is needed again.

**What's next:** M8 (documentation), now unblocked. First items: remove/reword the references to the in-repo Robotron showcase across `README.md` (the "Package split" diagram, the "Testing strategy" section), this file's own strategic vision (items 2 and 4 below), and `ACTION_PLAN.md`'s M7 description -- concrete list in `TODO.md`.
