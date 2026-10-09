"""Named ranges hidden in listings, kept in the program's dossier.

hidden.json belongs to the program, not to a run. Ranges are half-open:
start is included, end is not. Adjacent ranges are allowed; overlapping
ranges are refused.

Every change reloads the file first, preserving changes made in another
session. Opening the store or repeating an unchanged definition writes
nothing. This module owns persistence, not how a listing displays a range.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HiddenRange:
    """The bounds and note of one named hidden range."""

    start: int
    end: int
    note: str


class Hidden:
    """The named hidden ranges in one dossier's hidden.json."""

    def __init__(self, folder: Path) -> None:
        self.path = folder / "hidden.json"
        self.ranges: dict[str, HiddenRange] = {}
        self.reload()

    def reload(self) -> None:
        """Read the current definitions from disk.

        Without a file, definitions already in memory stay, as they do
        in Annotations: nothing has been saved to replace them.
        """
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.ranges = {
                name: HiddenRange(
                    start=int(entry["start"], 16),
                    end=int(entry["end"], 16),
                    note=entry["note"],
                )
                for name, entry in data.items()
            }

    def hide(self, name: str, start: int, end: int, note: str) -> None:
        """Add or replace name's definition, saving it immediately.

        A replacement is checked against every other named range, not
        against its own previous definition. Refused changes leave the
        saved definitions untouched.
        """
        self.reload()
        if not name.strip():
            raise ValueError("a hidden range needs a name")
        if not 0 <= start < end <= 0x10000:
            raise ValueError(
                "a hidden range needs 0000 <= start < end <= 10000"
            )

        for other_name, other in self.ranges.items():
            if other_name != name and start < other.end and other.start < end:
                raise ValueError(
                    f"{name} overlaps {other_name}"
                    f" ({other.start:04x}-{other.end:04x})"
                )

        definition = HiddenRange(start, end, note)
        if self.ranges.get(name) == definition:
            return
        self.ranges[name] = definition
        self._save()

    def unhide(self, name: str) -> None:
        """Remove a named definition and save; refuse an unknown name."""
        self.reload()
        if name not in self.ranges:
            raise ValueError(f"no hidden range {name}")
        del self.ranges[name]
        self._save()

    def _save(self) -> None:
        # Address order makes nearby ranges easy to find in the file.
        data = {
            name: {
                "start": f"{definition.start:04x}",
                "end": f"{definition.end:04x}",
                "note": definition.note,
            }
            for name, definition in sorted(
                self.ranges.items(),
                key=lambda item: (item[1].start, item[0]),
            )
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
