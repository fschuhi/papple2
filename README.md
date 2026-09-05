**IMPORTANT: This is the old readme, from the Robotron2084 repo. It contains `Papple2`, to be replaced with the `papple2` standalone project.**

## Package layout (current, as of the macOS port)

`papple2` is a real, installable Python package: the code lives in `src/papple2/`, declared in `pyproject.toml`, and installed in editable mode (`pip install -e .`, wired into `make setup`). The `Makefile` also builds an OS-specific venv (`.venv` on macOS, `.venv-win` on Windows). Every internal import is prefixed accordingly, e.g. `from papple2.Memory import Memory`.

Two things this does *not* yet mean:
- Imports are still star-imports (`from papple2.X import *`) in most files. Converting to explicit names is planned for M4, not done yet.
- The package is not yet split into core / debugging tools / Robotron showcase. Today, `papple2` contains all of it -- CPU, memory, and Apple II hardware alongside the Robotron- and Excel-specific code. That split is also M4 work (see `ACTION_PLAN.md`).

The rest of this file is the original Robotron2084-repo readme, and predates the package. It will be rewritten once M4 settles the core/debug/showcase structure.

# Papple2

I did the first run on disassembling Robotron using Python. The Papple2 workbench is derived from [ApplePy](https://github.com/jtauber/applepy), an Apple II emulator in Python, written by James Tauber. The emulator uses Pygame for screen output. You might want to check out [James' intro on YouTube](https://www.youtube.com/watch?v=EhK5JNx0irA).

Using Python as an emulator is of course an odd choice, because (I believe) all emulators in Python, including ApplePy, are slower than the original Apple II. At least in the beginning of the reengineering project that was not a problem at all. Compared to the more complete C# emulator Virtu (see below), ApplePy is very compact, easy to adapt and generally also easy to understand (which was important in the beginning, because I didn't know anything about Python in the beginning.)

I ported ApplePy to Python 3, removed some code (like all the interfacing with the emulator from the outside via sockets) and added a number of features:
* an assembler
* breakpoints, hooks
* execution tracer
* memory inspection tools
* statemachines
* call trees (using Graphviz)
* interface with Excel as a workbench (via xlwings)

There are tests (in tests.py), both the set from ApplePy as well as new ones using the assembler, as part of the effort of learning 6502.

I'm currently not developing on Papple2, but I can very well see myself coming back to it at a later point in time.

My  current disassembly is **Robotron (Apple).asm**, in the _Disassemblies_ folder.
