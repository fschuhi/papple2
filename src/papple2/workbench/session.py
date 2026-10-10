"""Session: the state of one working session at the IPython prompt.

A Session owns what the commands of papple2.workbench.shell work on: the
reports folder and the current dossier, with the annotations, hidden
ranges and colors read from it. The commands stay the contract; the
Session is where they keep their state, so that a reader sees which state
a command needs, and a test can start from a fresh one.

A Session does not print and does not return Text: the commands in
shell.py shape what it gives them for IPython.

Everything starts empty, as the module variables of shell.py did. The
attributes are plain, so a test may assign a stand-in to any of them.
"""

from pathlib import Path

from papple2.debug.disassembler import STANDARD_LABELS
from papple2.workbench.annotations import Annotations
from papple2.workbench.colors import Colors
from papple2.workbench.hidden import Hidden


class Session:
    """The reports folder and the current dossier of one working session."""

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
