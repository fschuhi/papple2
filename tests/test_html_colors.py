"""The HTML pages show listings in the listing editor's colors.

docs/html/style.css holds one rule per editor class the pages use: the
mnemonic classes (mn-load, ...), bytes and gap. This test keeps those
rules equal to STYLE in listing_editor.py, so that edit() and the pages
cannot drift apart: a color changed in the editor turns the suite red
until the stylesheet follows.
"""

import re
from pathlib import Path

from papple2.workbench.listing_editor import STYLE

# The repo root: this file lies in tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent

STYLESHEET = REPO_ROOT / "docs" / "html" / "style.css"

# The editor's classes that are not mnemonic classes but show on the pages.
OTHER_CLASSES = ("bytes", "gap")

# A rule as the stylesheet writes the editor's colors: on one line,
# .mn-load { color: #ff8a80; }
COLOR_RULE = re.compile(r"^\.([a-z-]+) \{ color: (#[0-9a-fA-F]{6}); \}$", re.MULTILINE)


def on_the_pages(name: str) -> bool:
    """Whether the pages use the editor's class name."""
    return name.startswith("mn-") or name in OTHER_CLASSES


def stylesheet_colors() -> dict[str, str]:
    """Class -> color, for the editor's classes in the stylesheet."""
    text = STYLESHEET.read_text(encoding="utf-8")
    return {
        name: color.lower()
        for name, color in COLOR_RULE.findall(text)
        if on_the_pages(name)
    }


def editor_colors() -> dict[str, str]:
    """Class -> color, for the classes of STYLE the pages use."""
    return {
        name: style.lower() for name, style in STYLE.style_rules if on_the_pages(name)
    }


def test_the_stylesheet_has_the_editors_colors() -> None:
    assert stylesheet_colors() == editor_colors(), (
        "docs/html/style.css and STYLE in listing_editor.py differ; "
        "change the stylesheet to the editor's colors"
    )
