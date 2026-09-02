**IMPORTANT: This is the old readme, from the Robotron2084 repo. It contains `Papple2`, to be replaced with the `papple2` standalone project.**

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
