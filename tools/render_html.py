"""Render one markdown file of papple2 as an HTML page in docs/html/.

The page is a reading version: the markdown stays the source. It uses
docs/html/style.css, which gives listings the colors of edit(). Run from
the repo root:

    python tools/render_html.py docs/lr_structures.md

writes docs/html/lr_structures.html. make html FILE=... runs it.

markdown-it-py does the markdown, as CommonMark with tables: the rules
PyCharm and Obsidian show the file by. Code fences are this script's own:
each becomes <pre> with its text exactly, and a listing gets spans for
its bytes, mnemonics and gap rows. Diagrams stay as text.
"""

import html
import os
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from papple2.workbench.listing_editor import MNEMONIC_CLASS

# The repo root: this file lies in tools/.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Where the pages go, next to style.css.
HTML_FOLDER = REPO_ROOT / "docs" / "html"

# The start of a listing line: the gutter's arrows, if any, then the
# address, as listing() prints it ("+-> 6252  9d e0 0c ...") or as a hand
# in a markdown file writes it ("6e89  JSR ...").
ADDRESS = re.compile(r"^[ |+\->]*[0-9a-fA-F]{4}\s")

# The bytes, directly after the address and two spaces, as listing()
# prints them: one to three pairs of lower-case hex digits.
BYTES = re.compile(r"^([ |+\->]*[0-9a-fA-F]{4}  )([0-9a-f]{2}(?: [0-9a-f]{2}){0,2})(?= |$)")

# A word of three capitals, not part of a longer name (ROL_TABLE), a
# label (.loop) or a number ($ADC, #$ADC). Whether it is a mnemonic,
# MNEMONIC_CLASS says.
WORD = re.compile(r"(?<![\w.$#])([A-Z]{3})(?!\w)")

# A row of bytes that never ran, as listing() prints it.
GAP = re.compile(r"\.\.\. \S+: [\d,]+ bytes? never ran \.\.\.")

# A link that leaves the repo, or stays on the page: kept as it is.
OUTSIDE = re.compile(r"^([a-z][a-z0-9+.-]*:|#)", re.IGNORECASE)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
{body}</main>
</body>
</html>
"""


def escape(text: str) -> str:
    """text for HTML: <, > and & as entities, quotes as they are."""
    return html.escape(text, quote=False)


def span(css_class: str, text: str) -> str:
    """text in a span of css_class."""
    return f'<span class="{css_class}">{escape(text)}</span>'


def is_listing(text: str) -> bool:
    """Whether a code fence is a listing: its first line that is not
    empty starts with an address, after the gutter's arrows if any."""
    for line in text.splitlines():
        if line.strip():
            return bool(ADDRESS.match(line))
    return False


def color_line(line: str) -> str:
    """One line of a listing, escaped, with spans for the editor's colors:
    the bytes, every mnemonic in the code, a row that never ran. The
    comment, from ";" on, gets none."""
    code, semicolon, comment = line.partition(";")
    rest = escape(semicolon + comment)
    gap = GAP.search(code)
    if gap:
        return (
            escape(code[: gap.start()])
            + span("gap", gap.group(0))
            + escape(code[gap.end() :])
            + rest
        )
    parts = []
    position = 0
    found = BYTES.match(code)
    if found:
        parts.append(escape(found.group(1)))
        parts.append(span("bytes", found.group(2)))
        position = found.end()
    for word in WORD.finditer(code, position):
        group = MNEMONIC_CLASS.get(word.group(1))
        if group is None:
            continue
        parts.append(escape(code[position : word.start()]))
        parts.append(span(f"mn-{group}", word.group(1)))
        position = word.end()
    parts.append(escape(code[position:]))
    return "".join(parts) + rest


def color_listing(text: str) -> str:
    """A listing's text, escaped, every line with color_line()."""
    return "\n".join(color_line(line) for line in text.split("\n"))


def render_code(text: str) -> str:
    """A code fence as <pre>: the text exactly, a listing colored."""
    text = text.removesuffix("\n")
    inner = color_listing(text) if is_listing(text) else escape(text)
    return f"<pre>{inner}</pre>\n"


def relink(target: str, source_folder: Path) -> str:
    """A link's target in a markdown file in source_folder, changed so
    that it leads to the same file from docs/html/. A web address, or a
    place on the same page (#...), stays as it is."""
    if not target or OUTSIDE.match(target):
        return target
    path, hash_sign, place = target.partition("#")
    if not path:
        return target
    moved = os.path.relpath(source_folder / path, HTML_FOLDER)
    return Path(moved).as_posix() + hash_sign + place


def relink_tokens(tokens: list[Token], source_folder: Path) -> None:
    """relink() every link and image in tokens, in place."""
    for token in tokens:
        if token.type == "link_open":
            token.attrSet("href", relink(str(token.attrGet("href")), source_folder))
        elif token.type == "image":
            token.attrSet("src", relink(str(token.attrGet("src")), source_folder))
        if token.children:
            relink_tokens(token.children, source_folder)


def title_of(text: str, fallback: str) -> str:
    """The text of the first heading of the first level."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def code_rule(renderer: object, tokens: list[Token], index: int, *_: object) -> str:
    """markdown-it-py's render rule for a code fence or an indented code
    block: render_code(). The renderer comes first, as the rule is bound
    to it."""
    return render_code(tokens[index].content)


def render_page(source: Path) -> str:
    """The HTML page for one markdown file."""
    text = source.read_text(encoding="utf-8")
    parser = MarkdownIt("commonmark").enable("table")
    parser.add_render_rule("fence", code_rule)
    parser.add_render_rule("code_block", code_rule)
    tokens = parser.parse(text)
    relink_tokens(tokens, source.resolve().parent)
    body = parser.renderer.render(tokens, parser.options, {})
    return PAGE.format(title=escape(title_of(text, source.stem)), body=body)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/render_html.py docs/<file>.md")
    source = Path(sys.argv[1])
    page = HTML_FOLDER / f"{source.stem}.html"
    page.write_text(render_page(source), encoding="utf-8")
    print(f"{source} -> {page.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
