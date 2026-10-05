"""Annotations: what we know about a program's addresses, kept in its dossier.

A dossier is a folder for one program (dossiers/lode_runner/,
dossiers/walkthrough/). Its annotations live in annotations.json there,
under git: labels now, comments next. They belong to the program, not to
a run or an IPython session, so a label given today shows tomorrow in a
run that covers far more code.

Every change is written at once, so the file is never behind the prompt.
Nothing is written without a change: opening a dossier only to look leaves
no trace.

Addresses are the ones the code runs at, i.e. memory after relocation,
which is what dis() reads.
"""

import json
import re
from pathlib import Path

# A global label: a letter or _, then letters, digits, _ and : (the colon
# groups labels, as in rw:HIRES). A local label is stored by its full name:
# a global label, one dot, then letters, digits and _, e.g.
# routine_001.loop2. Stored names stay full and unique, so they don't change
# when the rules for typing or showing .loop2 change. No spaces anywhere.
VALID_LABEL = re.compile(r"[A-Za-z_][A-Za-z0-9_:]*(\.[A-Za-z0-9_]+)?")


class Annotations:
    def __init__(self, folder: Path) -> None:
        self.path = folder / "annotations.json"
        # Plain dicts, so dis() takes them as they are.
        self.labels: dict[int, str] = {}
        self.comments: dict[int, str] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.labels = _from_file(data["labels"])
            self.comments = _from_file(data["comments"])

    def label(self, address: int, text: str) -> None:
        """Give address the label text, replacing any label it has. A text
        that breaks VALID_LABEL's rule is refused. A text used at another
        address is refused: dasm would refuse it too, and at the prompt it's
        almost always a typo."""
        if not VALID_LABEL.fullmatch(text):
            raise ValueError(
                f"{text} is no valid label: letters, digits, _ and :,"
                " and one . for a local label"
            )
        for other, other_text in self.labels.items():
            if other_text == text and other != address:
                raise ValueError(f"{text} is already the label of ${other:04x}")
        self.labels[address] = text
        self._save()

    def unlabel(self, address: int) -> None:
        """Remove address's label. An address without one is refused:
        at the prompt that's almost always a mistyped address."""
        if address not in self.labels:
            raise ValueError(f"${address:04x} has no label")
        del self.labels[address]
        self._save()

    def add_labels(self, labels: dict[int, str]) -> None:
        """Add many labels at once, e.g. STANDARD_LABELS in a script's setup.
        Addresses that already have a label keep it, and texts already in
        use are skipped, so adding the same labels again changes nothing --
        not even the file."""
        in_use = set(self.labels.values())
        added = False
        for address, text in labels.items():
            if address not in self.labels and text not in in_use:
                self.labels[address] = text
                in_use.add(text)
                added = True
        if added:
            self._save()

    def comment(self, address: int, text: str) -> None:
        """Give address the comment text, replacing any comment it has."""
        self.comments[address] = text
        self._save()

    def uncomment(self, address: int) -> None:
        """Remove address's comment. An address without one is refused,
        as in unlabel()."""
        if address not in self.comments:
            raise ValueError(f"${address:04x} has no comment")
        del self.comments[address]
        self._save()

    def _save(self) -> None:
        # Sorted by address and indented: one entry per line, so git diff
        # shows each change as one line.
        data = {
            "labels": _to_file(self.labels),
            "comments": _to_file(self.comments),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n")


def _to_file(entries: dict[int, str]) -> dict[str, str]:
    """JSON keys are strings: four-digit hex, sorted by address."""
    return {f"{address:04x}": text for address, text in sorted(entries.items())}


def _from_file(entries: dict[str, str]) -> dict[int, str]:
    return {int(key, 16): text for key, text in entries.items()}
