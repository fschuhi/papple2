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
# routine_6238.loop2. Stored names stay full and unique, so they don't change
# when the rules for typing or showing .loop2 change. A local label is typed
# by its short part alone, .loop2, which is why the rule takes that too.
# No spaces anywhere.
VALID_LABEL = re.compile(
    r"[A-Za-z_][A-Za-z0-9_:]*(\.[A-Za-z0-9_]+)?|\.[A-Za-z0-9_]+"
)


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
        almost always a typo.

        A local label is typed as .loop1 and gets the global label above it
        (see with_owners()). Typed by its full name, it must have the owner
        it would get anyway; otherwise it's refused. Any label change can
        move local labels to another owner: refused if that gives two labels
        the same name."""
        if not VALID_LABEL.fullmatch(text):
            raise ValueError(
                f"{text} is no valid label: letters, digits, _ and :,"
                " and one . for a local label"
            )
        for other, other_text in self.labels.items():
            if other_text == text and other != address:
                raise ValueError(f"{text} is already the label of ${other:04x}")
        changed = dict(self.labels)
        changed[address] = text
        rebuilt = with_owners(changed)
        if "." in text and not text.startswith(".") and rebuilt[address] != text:
            short = text[text.index(".") :]
            raise ValueError(
                f"{text} doesn't fit here, it would be {rebuilt[address]};"
                f" type {short}"
            )
        self._take(rebuilt)

    def unlabel(self, address: int) -> None:
        """Remove address's label. An address without one is refused:
        at the prompt that's almost always a mistyped address."""
        if address not in self.labels:
            raise ValueError(f"${address:04x} has no label")
        changed = dict(self.labels)
        del changed[address]
        # Removing a global label merges its scope into the one above:
        # with_owners() refuses if that gives two local labels one name.
        self._take(with_owners(changed))

    def add_labels(self, labels: dict[int, str]) -> None:
        """Add many labels at once, e.g. STANDARD_LABELS in a script's setup.
        Addresses that already have a label keep it, and texts already in
        use are skipped, so adding the same labels again changes nothing --
        not even the file."""
        in_use = set(self.labels.values())
        changed = dict(self.labels)
        added = False
        for address, text in labels.items():
            if address not in changed and text not in in_use:
                changed[address] = text
                in_use.add(text)
                added = True
        if added:
            self._take(with_owners(changed))

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

    def _take(self, labels: dict[int, str]) -> None:
        """Make labels the dossier's labels and write the file, unless
        nothing changed: e.g. .loop1 typed again where it already is."""
        if labels == self.labels:
            return
        self.labels = labels
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


def with_owners(labels: dict[int, str]) -> dict[int, str]:
    """labels, with every local label named after the global label above it
    now: its short part (.loop1) kept, the owner in front given anew. Done
    for all of them on every change, not just the ones a change touches:
    simpler, and fast enough for a program's few thousand lines.

    Raises ValueError, naming the problem, if a local label has no global
    label above it, or if two labels would get the same name. labels itself
    is left alone, so a refused change changes nothing."""
    result: dict[int, str] = {}
    owner = None
    for address in sorted(labels):
        text = labels[address]
        if "." not in text:
            owner = text
            result[address] = text
            continue
        short = text[text.index(".") :]
        if owner is None:
            raise ValueError(
                f"{short}: no global label above ${address:04x} to belong to"
            )
        result[address] = owner + short
    first_at: dict[str, int] = {}
    for address, text in sorted(result.items()):
        if text in first_at:
            raise ValueError(
                f"{text} would be the label of both ${first_at[text]:04x}"
                f" and ${address:04x}"
            )
        first_at[text] = address
    return result


def _to_file(entries: dict[int, str]) -> dict[str, str]:
    """JSON keys are strings: four-digit hex, sorted by address."""
    return {f"{address:04x}": text for address, text in sorted(entries.items())}


def _from_file(entries: dict[str, str]) -> dict[int, str]:
    return {int(key, 16): text for key, text in entries.items()}
