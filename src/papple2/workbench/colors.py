"""Persistent named color ranges in a program's dossier.

Ranges are half-open. Overlaps are allowed: matching definitions with
different shades give MIX_COLOR, while definitions with the same shade
keep that shade.

Every change reloads the file first to preserve another session's edits.
Opening the store or repeating an unchanged definition writes nothing.
Views choose how to display the colors; this module owns their lookup.
"""

import json
from dataclasses import dataclass
from pathlib import Path

SHADES = frozenset(
    {"red", "green", "yellow", "blue", "magenta", "cyan", "white"}
)
MIX_COLOR = "magenta"


@dataclass(frozen=True)
class ColorRange:
    """The bounds and shade of one named color range."""

    start: int
    end: int
    shade: str


class Colors:
    """Named color ranges saved in one dossier's colors.json."""

    def __init__(self, folder: Path) -> None:
        self.path = folder / "colors.json"
        self.ranges: dict[str, ColorRange] = {}
        self.reload()

    def reload(self) -> None:
        """Read the saved definitions.

        Without a file, definitions already in memory stay, following
        the dossier's existing annotation and hiding conventions.
        """
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.ranges = {
                name: ColorRange(
                    start=int(entry["start"], 16),
                    end=int(entry["end"], 16),
                    shade=entry["shade"],
                )
                for name, entry in data.items()
            }

    def color(self, name: str, start: int, end: int, shade: str) -> None:
        """Add or replace a named definition and save it immediately."""
        self.reload()
        if not name.strip():
            raise ValueError("a color range needs a name")
        if not 0 <= start < end <= 0x10000:
            raise ValueError(
                "a color range needs 0000 <= start < end <= 10000"
            )
        if shade not in SHADES:
            raise ValueError(
                f"unknown color {shade}; choose from {', '.join(sorted(SHADES))}"
            )

        definition = ColorRange(start, end, shade)
        if self.ranges.get(name) == definition:
            return
        self.ranges[name] = definition
        self._save()

    def uncolor(self, name: str) -> None:
        """Remove a named definition and save; refuse an unknown name."""
        self.reload()
        if name not in self.ranges:
            raise ValueError(f"no color range {name}")
        del self.ranges[name]
        self._save()

    def color_at(self, address: int) -> str | None:
        """The color assigned to address, or None if none is assigned.

        Reads the definitions currently in memory. The caller reloads
        once before drawing a view, not once per byte.
        """
        shades = {
            definition.shade
            for definition in self.ranges.values()
            if definition.start <= address < definition.end
        }
        return _combined(shades)

    def color_for_range(self, start: int, end: int) -> str | None:
        """The color of definitions containing the entire given span.

        For a routine's breadcrumb: partial coverage does not assign its
        title a color. This is containment lookup, not a summary of the
        colors of all bytes inside the span.
        """
        if not 0 <= start < end <= 0x10000:
            raise ValueError(
                "a color lookup needs 0000 <= start < end <= 10000"
            )
        shades = {
            definition.shade
            for definition in self.ranges.values()
            if definition.start <= start and end <= definition.end
        }
        return _combined(shades)

    def _save(self) -> None:
        # Address order keeps related definitions together in the file.
        data = {
            name: {
                "start": f"{definition.start:04x}",
                "end": f"{definition.end:04x}",
                "shade": definition.shade,
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


def _combined(shades: set[str]) -> str | None:
    """One shared shade, MIX_COLOR for disagreement, or None."""
    if not shades:
        return None
    if len(shades) == 1:
        return next(iter(shades))
    return MIX_COLOR
