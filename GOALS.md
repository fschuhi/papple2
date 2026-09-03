# papple2 -- Goals and Roadmap

(Note: "I" in the following paragraphs refer to the user, "you" to you as the AI model.)

**Charter:** This file answers: where is the project going, in what order, and what happens next. It holds the strategic vision, the phased roadmap, and goals that need a strategy discussion before they are actionable. The _Current Session Pointer_ below is the single canonical "where we are / what's next" -- keep it to a few lines, update it, don't grow it; `FIRST_PROMPT.md` sends the reader here first. Concrete, startable work lives in `TODO.md`; the resolved-work record lives in `HISTORY.md` or `CHANGELOG.md`(on the heap, out of the per-session dump); architecture, contract, and settled decisions live in `README.md`.

---

## 📍 Current Session Pointer

**Where we are:** 
- Revisited the hibernated Robotron 2084 disassembly project which uses a Python emulator as important part of its Excel-based workbench.
- There are tests using `unittest`. As far as I remember, these are the tests from ApplePy
- The emulator is not only for low level 6502 stuff but also for the Apple II. The screen and keyboard are emulated by `pygame`. I don't remember, but I think it's not possible to mock the `pygame` "Apple II".
- I don't understand anymore how everything hangs together; it has been years since I've worked with Papple2 and the Robotron 2084 disassembly project.

**What's next:**
We devise an action plan (as markdown document) which outlines the steps necessary to arrive at the target state of the project. This target state looks like this:
- `papple2` can be used in other Python project like `load-runner`(see "Strategic Vision" below).
- The Robotron 2084 disassembly project is the showcase how to use the emulator. It doesn't have to be included in the project, but it could, to exemplify how `papple2` can be used.
- The emulator can be run both with showing the `pygame` and taking keyboard input but also completely silently, including working with programmatic keypresses.
- The `papple2` library (is this even the correct terminology?) has a good pytest test coverage, including (1) 6502 specifics, (2) Apple II specifics, (3) running disk images with and without the `pygame` screen, (4) breakpoints and other debugging facilities.
- The Excel bridge is implemented with PyXll instead of xlwings.
- Full set of the artefacts `README.md`, `GOALS.md`, `TODO.md`.

The above list is preliminary. I expect more constraints and target states to be added when working through the inventory of what's already there. 

---

## 🎯 Strategic vision

(very rough draft)

- `papple2` is a lightweight Apple II emulator. The main use for the emulator is as debugging facility.
- Papple2 is based on ApplePy. The latter is not actively maintained anymore, so I migrated the code to Python 3, removed some stuff like the socket machinery (see `README.md`) and added modules specifically for debugging, memory inspection, and tracing. 
- The code is currently in `src/papple2`, because eventually I'd like to use `papple2` in an other project, `load-runner`. That private educational project aims to port the much-beloved Apple II game to Godot. Depending on how high I set the bar regarding fidelity, it could very well be helpful to do cycle counting. I'm also currently working on a level extractor which directly reads from the disk. This could be completed by using the code, via the emulator, i.e. letting it load the level and then inspect the filled buffers afterwards.
- The project contains experimental structures like "tiles" which can be used to monitor and understand what's happening. Since the introduction of this concept I've learned about noweb weaving, so I think that the tiling idea was not a complete miss. Having said that, the state of tiles as concept is unclear. It might be a good to keep, probably in a kind of hibernated form so that it doesn't harm anything else. It could then be revitalized with a targeted refactoring.
- The code we have right now was set up to do a disassembly of Robotron 2084, another Apple II game. For the workbench UI I used Excel, via xlwings. I'm not using that library anymore, though, so we need to refactor the bridge so that I can use the now-preferred PyXll. This is low prio for now, because the Robotron disassembly project is in hibernation.
