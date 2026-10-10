"""Session: the state of one working session at the IPython prompt.

A Session owns what the commands of papple2.workbench.shell work on: the
reports folder, the current dossier with the annotations, hidden ranges
and colors read from it, and the current run with its routines. The
commands stay the contract; the
Session is where they keep their state, so that a reader sees which state
a command needs, and a test can start from a fresh one.

A Session does not print and does not return Text: the commands in
shell.py shape what it gives them for IPython.

Everything starts empty, as the module variables of shell.py did. The
attributes are plain, so a test may assign a stand-in to any of them.
"""

import time
from pathlib import Path
from types import ModuleType
from typing import Any

from papple2.core.emulator import Emulator
from papple2.debug.disassembler import STANDARD_LABELS
from papple2.debug.stop_conditions import instruction_count_reaches
from papple2.workbench.annotations import Annotations
from papple2.workbench.basic_blocks_analysis import (
    BlockGraph,
    Routines,
    SplitTransition,
    build_run_graph,
    find_routines,
    read_returns,
    read_split_tiles,
    read_split_transitions,
    stack_jumps,
)
from papple2.workbench.colors import Colors
from papple2.workbench.hidden import Hidden
from papple2.workbench.stack_tracking import RETURNS_FILE, StackTracking
from papple2.workbench.tiling import (
    SPLIT_TILES_FILE,
    SPLIT_TRANSITIONS_FILE,
    Tiling,
    address,
)


class Session:
    """The reports folder, the current dossier and the current run."""

    def __init__(self) -> None:
        # Where write_report() writes; None until use_reports_folder().
        self.reports_folder: Path | None = None
        # The current dossier's folder and the stores read from it; None
        # until use_dossier(). Hidden ranges and colors are kept apart from
        # the labels and comments.
        self.dossier_folder: Path | None = None
        self.annotations: Annotations | None = None
        self.hidden: Hidden | None = None
        self.color_store: Colors | None = None

        # The current run: the program setup it ran, the machine as the run
        # left it (listing() reads its memory), its disk stand-in (with a
        # log of the reads it served), and the instrumentations that were
        # attached, in the order given to run(). Empty until run().
        self.run_program: ModuleType | None = None
        self.run_emulator: Emulator | None = None
        self.run_rwts: Any = None
        self.run_instrumentations: list[object] = []
        # The run's routines and the graph of every block it ran
        # (listing()'s arrows), built from the tiling's split reports. None
        # until tiling_reports() or set_current_run().
        self.routines: Routines | None = None
        self.run_graph: BlockGraph | None = None
        # The run's split transitions, as read from its report: who leapt
        # where, and how often. None until tiling_reports() or
        # set_current_run().
        self.run_transitions: list[SplitTransition] | None = None
        # The run's stack jumps, (address of the RTS, target) -> how often,
        # as stack_jumps() finds them in the stack tracking's report. None
        # until set_current_run() is given that report.
        self.run_stack_jumps: dict[tuple[int, int], int] | None = None
        # The listing editor's memory: for every routine edit() showed, the
        # first row in its window and the bar's row when it was left,
        # (top, cursor), so that it opens again as it was. Forgotten with
        # the run's routines. Cleared in place, never replaced: the editor
        # holds this very dict.
        self.editor_views: dict[int, tuple[int, int]] = {}

    def use_reports_folder(self, folder: Path) -> None:
        """Make folder the reports folder; it need not exist yet."""
        self.reports_folder = Path(folder)

    def write_report(self, file_name: str, text: str) -> Path:
        """Write text into the reports folder as file_name; return its path."""
        if self.reports_folder is None:
            raise RuntimeError(
                "no reports folder set; call use_reports_folder() first"
            )
        path = self.reports_folder / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def use_dossier(self, folder: Path) -> None:
        """Open the dossier in folder: annotations, hidden ranges, colors."""
        self.dossier_folder = Path(folder)
        self.annotations = Annotations(self.dossier_folder)
        self.hidden = Hidden(self.dossier_folder)
        self.color_store = Colors(self.dossier_folder)
        # Only a dossier without annotations yet gets the standard labels,
        # so a standard label removed by hand stays removed.
        if not self.annotations.path.exists():
            self.annotations.add_labels(STANDARD_LABELS)

    def current_annotations(self) -> Annotations:
        """The open dossier's annotations; stops if no dossier is open."""
        if self.annotations is None:
            raise RuntimeError("no dossier open; call use_dossier() first")
        return self.annotations

    def refresh_annotations(self) -> None:
        """Read the annotations from the file again, if a dossier is open."""
        if self.annotations is not None:
            self.annotations.reload()

    def address_of(self, place: int | str) -> int:
        """place if it is an address, else the address its label names."""
        if isinstance(place, int):
            return place
        for labelled, text in self.current_annotations().labels.items():
            if text == place:
                return labelled
        raise ValueError(f"no label {place} in the dossier")

    def current_hidden(self) -> Hidden:
        """The open dossier's hidden ranges; stops if no dossier is open."""
        if self.dossier_folder is None or self.hidden is None:
            raise RuntimeError("no dossier open; call use_dossier() first")
        return self.hidden

    def current_colors(self) -> Colors:
        """The open dossier's colors; stops if no dossier is open."""
        if self.dossier_folder is None or self.color_store is None:
            raise RuntimeError("no dossier open; call use_dossier() first")
        return self.color_store

    def run(
        self,
        program: ModuleType,
        instructions: int,
        *instrumentations: type,
        binary: str | None = None,
    ) -> tuple[int, float]:
        """Run program headless with the instrumentations attached; return
        the instructions run and the seconds they took."""
        emulator, rwts = program.boot(
            binary or program.DEFAULT_BINARY, headless=True
        )
        attached = [
            instrumentation(emulator.cpu) for instrumentation in instrumentations
        ]
        for instrumentation in attached:
            emulator.attach(instrumentation)

        start = time.perf_counter()
        try:
            emulator.run(until=instruction_count_reaches(instructions))
        finally:
            seconds = time.perf_counter() - start
            for instrumentation in attached:
                emulator.detach(instrumentation)

        self.run_program = program
        self.run_emulator = emulator
        self.run_rwts = rwts
        self.run_instrumentations = attached
        self.routines = None
        self.run_graph = None
        self.run_transitions = None
        self.run_stack_jumps = None
        self.editor_views.clear()
        return emulator.instructions, seconds

    def tiling_reports(self) -> int:
        """Write the tiling reports into the reports folder, build the run's
        routines from them; return how many routines it has."""
        if self.run_emulator is None or self.run_program is None:
            raise RuntimeError("no run; call run() first")
        tilings = [
            each for each in self.run_instrumentations if isinstance(each, Tiling)
        ]
        if not tilings:
            raise RuntimeError(
                "the current run had no Tiling attached; run(program, n, Tiling)"
            )
        if self.reports_folder is None:
            raise RuntimeError(
                "no reports folder set; call use_reports_folder() first"
            )
        # The emulator counts from 0, so emulator.instructions is what ran
        # while the tiling was attached.
        tilings[0].write_reports(
            self.reports_folder,
            self.run_emulator.instructions,
            len(self.run_rwts.log),
        )
        return self.set_current_run(
            self.run_emulator,
            self.run_program.LOAD_ADDRESS,
            self.reports_folder / SPLIT_TILES_FILE,
            self.reports_folder / SPLIT_TRANSITIONS_FILE,
        )

    def stack_tracking_reports(self) -> int | None:
        """Write the stack tracking report into the reports folder; if the
        routines are built, build them again with it, and return how many
        there are, else None."""
        if self.run_emulator is None:
            raise RuntimeError("no run; call run() first")
        trackings = [
            each
            for each in self.run_instrumentations
            if isinstance(each, StackTracking)
        ]
        if not trackings:
            raise RuntimeError(
                "the current run had no StackTracking attached; "
                "run(program, n, StackTracking)"
            )
        if self.reports_folder is None:
            raise RuntimeError(
                "no reports folder set; call use_reports_folder() first"
            )
        trackings[0].write_reports(self.reports_folder)
        if self.routines is None:
            return None
        return self.set_current_run(
            self.run_emulator,
            self.run_program.LOAD_ADDRESS,
            self.reports_folder / SPLIT_TILES_FILE,
            self.reports_folder / SPLIT_TRANSITIONS_FILE,
            returns=self.reports_folder / RETURNS_FILE,
        )

    def set_current_run(
        self,
        emulator: Emulator,
        start: int,
        split_tiles: Path,
        split_transitions: Path,
        returns: Path | None = None,
    ) -> int:
        """Make the run emulator has made the current one, built from its
        reports; return how many routines it has."""
        tiles = read_split_tiles(split_tiles)
        transitions = read_split_transitions(split_transitions)
        self.run_stack_jumps = (
            stack_jumps(read_returns(returns), transitions) if returns else None
        )
        # How often each target was entered by a stack jump.
        entered: dict[int, int] = {}
        for (_, target), count in (self.run_stack_jumps or {}).items():
            entered[target] = entered.get(target, 0) + count
        self.run_emulator = emulator
        self.routines = find_routines(tiles, transitions, start, entered)
        self.editor_views.clear()
        self.run_graph = build_run_graph(tiles, transitions, start)
        self.run_transitions = transitions
        self.label_routines()
        return len(self.routines.graphs)

    def label_routines(self) -> None:
        """Give each routine entry without a label the name routine_<address>,
        if a dossier is open."""
        # A global label at every entry keeps local labels from belonging
        # to the routine above. Entries with a label keep it, so names
        # given by hand stay.
        if self.annotations is None or self.routines is None:
            return
        self.annotations.add_labels(
            {entry: f"routine_{entry:04x}" for entry in self.routines.graphs}
        )

    def current_routines(self) -> Routines:
        """The current run's routines; stops if there is no current run."""
        if self.routines is None:
            raise RuntimeError(
                "no routines; call tiling_reports() after run(),"
                " or set_current_run()"
            )
        return self.routines

    def routine_at(self, entry: int | str) -> int:
        """The address of entry, if a routine of the current run starts there."""
        entry = self.address_of(entry)
        if entry not in self.current_routines().graphs:
            raise ValueError(
                f"{address(entry)} is not a routine; show_routines() lists them"
            )
        return entry
