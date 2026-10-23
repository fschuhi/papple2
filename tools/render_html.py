"""Render one markdown file of papple2 as an HTML page in docs/html/.

The page is a reading version: the markdown stays the source. It uses
docs/html/style.css, which gives listings the colors of edit(). Run from
the repo root:

    python tools/render_html.py docs/lr_structures.md

writes docs/html/lr_structures.html. make html FILE=... runs it.

markdown-it-py does the markdown, as CommonMark with tables: the rules
PyCharm and Obsidian show the file by. Code fences are this script's own:
each becomes <pre> with its text exactly, and a listing gets spans for
its bytes, mnemonics and gap rows.

An LLM draws the diagrams, all of a file in one answer. A code fence that
is not a listing and has no drawing yet makes the script write a prompt,
tmp/html/<name>-prompt.txt: give it to an LLM and save the answer as
docs/html/<name>-diagrams.html. Then each fence with a drawing becomes
that SVG. A drawing belongs to a fence by diagram_id(), a hash of the
fence's text: a diagram changed in the markdown shows as text again, and
the next prompt asks for it.
"""

import hashlib
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

# Where the prompts go: make html writes them again whenever needed.
PROMPT_FOLDER = REPO_ROOT / "tmp" / "html"

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

# One drawing in the LLM's answer: an <svg> with a diagram's id, and the
# answer for a fence that is no diagram, <svg id="..." class="keep-text"/>.
# Anything around them in the answer, words or a code fence, is ignored.
DRAWING = re.compile(r'<svg\b[^>]*\bid="(diagram-[0-9a-f]{8})"[^>]*?(?:/>|>.*?</svg>)', re.DOTALL)

PROMPT = """You draw ASCII diagrams as SVG, for the HTML pages of papple2.

Below are the code fences of one markdown file, each with an id. Most
are diagrams: names joined by arrows drawn with characters (-->, <--,
|, v, +--). Draw each diagram as one SVG. A fence that is no diagram
(a command, data, text laid out by hand) stays text: answer it with
<svg id="ID" class="keep-text"/>, ID being the fence's id.

Answer with the SVGs only, one after the other, in the order of the
fences, and nothing else.

The rules for each SVG:
- The root element is <svg id="ID" width="W" height="H" viewBox="0 0 W H">,
  ID being the fence's id, exactly as given.
- Keep the layout of the characters: what stands to the left stays left,
  what stands below stays below.
- Each name becomes a box with its text: <rect class="box" ... rx="3"/>
  and <text class="name" ...>. A box is 28 high and 8 per character
  wide, plus 24. The text sits in the middle of its box, with
  text-anchor="middle" and dominant-baseline="central".
- Each arrow becomes <line class="arrow" .../>, or <path class="arrow" .../>
  where it bends, with marker-end="url(#ID-head)".
- The text on an arrow, and any loose text, becomes <text class="label" ...>.
- Define the arrow head once, in <defs>, as in the example, with the id
  ID-head.
- Keep every word of the diagram, exactly as it is written.
- No colors, fonts or styles: the page's stylesheet sets them through the
  classes box, name, label, arrow and head.
- Make width, height and viewBox large enough for everything, with a
  margin of 10.

An example. This diagram, with the id diagram-example:

```
MOVE_GUARDS --JSR (6c9b)--> MOVE_GUARD --dispatch (6e96)--> TRY_GUARD_MOVE_LEFT
                                                               |
                                                               JMP STORE_GUARD_DATA (7044)
                                                               v
MOVE_GUARDS <-------------- RTS (75cd) -------------------- STORE_GUARD_DATA
            lands at 6c9e, after the JSR at 6c9b
```

is drawn like this:

<svg id="diagram-example" width="800" height="230" viewBox="0 0 800 230">
<defs>
<marker id="diagram-example-head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
<path class="head" d="M0,0 L8,4 L0,8 z"/>
</marker>
</defs>
<rect class="box" x="10" y="20" width="110" height="28" rx="3"/>
<text class="name" x="65" y="34" text-anchor="middle" dominant-baseline="central">MOVE_GUARDS</text>
<line class="arrow" x1="120" y1="34" x2="299" y2="34" marker-end="url(#diagram-example-head)"/>
<text class="label" x="210" y="22" text-anchor="middle" dominant-baseline="central">JSR (6c9b)</text>
<rect class="box" x="300" y="20" width="104" height="28" rx="3"/>
<text class="name" x="352" y="34" text-anchor="middle" dominant-baseline="central">MOVE_GUARD</text>
<line class="arrow" x1="404" y1="34" x2="619" y2="34" marker-end="url(#diagram-example-head)"/>
<text class="label" x="512" y="22" text-anchor="middle" dominant-baseline="central">dispatch (6e96)</text>
<rect class="box" x="620" y="20" width="172" height="28" rx="3"/>
<text class="name" x="706" y="34" text-anchor="middle" dominant-baseline="central">TRY_GUARD_MOVE_LEFT</text>
<line class="arrow" x1="706" y1="48" x2="706" y2="169" marker-end="url(#diagram-example-head)"/>
<text class="label" x="696" y="109" text-anchor="end" dominant-baseline="central">JMP STORE_GUARD_DATA (7044)</text>
<rect class="box" x="632" y="170" width="148" height="28" rx="3"/>
<text class="name" x="706" y="184" text-anchor="middle" dominant-baseline="central">STORE_GUARD_DATA</text>
<line class="arrow" x1="632" y1="184" x2="121" y2="184" marker-end="url(#diagram-example-head)"/>
<text class="label" x="376" y="172" text-anchor="middle" dominant-baseline="central">RTS (75cd)</text>
<rect class="box" x="10" y="170" width="110" height="28" rx="3"/>
<text class="name" x="65" y="184" text-anchor="middle" dominant-baseline="central">MOVE_GUARDS</text>
<text class="label" x="10" y="216" dominant-baseline="central">lands at 6c9e, after the JSR at 6c9b</text>
</svg>

The fences:
"""

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


def diagram_id(text: str) -> str:
    """The id of a code fence, from its text: the same text, the same id."""
    digest = hashlib.sha1(text.removesuffix("\n").encode("utf-8")).hexdigest()
    return f"diagram-{digest[:8]}"


def render_code(text: str, drawings: dict[str, str] | None = None) -> str:
    """A code fence as <pre>: the text exactly, a listing colored. A fence
    with a drawing in drawings (by diagram_id()) becomes that SVG."""
    text = text.removesuffix("\n")
    drawing = (drawings or {}).get(diagram_id(text))
    if drawing:
        return f'<div class="diagram">\n{drawing}\n</div>\n'
    inner = color_listing(text) if is_listing(text) else escape(text)
    return f"<pre>{inner}</pre>\n"


def load_drawings(path: Path) -> dict[str, str]:
    """The drawings in an LLM's answer, by diagram id; none if there is no
    answer yet. A fence answered with keep-text maps to "": it stays text,
    and asks for no drawing."""
    if not path.exists():
        return {}
    drawings = {}
    for found in DRAWING.finditer(path.read_text(encoding="utf-8")):
        keep_text = 'class="keep-text"' in found.group(0).split(">", 1)[0]
        drawings[found.group(1)] = "" if keep_text else found.group(0)
    return drawings


def prompt_text(fences: list[str]) -> str:
    """The prompt for an LLM: the rules, the example, and every fence with
    its id."""
    parts = [PROMPT]
    for text in fences:
        parts.append(f"\n{diagram_id(text)}:\n\n```\n{text}\n```\n")
    return "".join(parts)


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


def code_rule(
    renderer: object, tokens: list[Token], index: int, options: object, env: dict
) -> str:
    """markdown-it-py's render rule for a code fence or an indented code
    block: render_code(), with the drawings render_page() puts into env.
    The renderer comes first, as the rule is bound to it."""
    return render_code(tokens[index].content, env.get("drawings"))


def new_parser() -> MarkdownIt:
    """markdown-it-py for CommonMark with tables, its code fences ours."""
    parser = MarkdownIt("commonmark").enable("table")
    parser.add_render_rule("fence", code_rule)
    parser.add_render_rule("code_block", code_rule)
    return parser


def code_fences(text: str) -> list[str]:
    """The text of every code fence and indented code block in a markdown
    text, in order, as render_code() gets it."""
    return [
        token.content.removesuffix("\n")
        for token in new_parser().parse(text)
        if token.type in ("fence", "code_block")
    ]


def render_page(source: Path, drawings: dict[str, str] | None = None) -> str:
    """The HTML page for one markdown file, with the drawings for its
    diagrams, by diagram id."""
    text = source.read_text(encoding="utf-8")
    parser = new_parser()
    tokens = parser.parse(text)
    relink_tokens(tokens, source.resolve().parent)
    body = parser.renderer.render(tokens, parser.options, {"drawings": drawings or {}})
    return PAGE.format(title=escape(title_of(text, source.stem)), body=body)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/render_html.py docs/<file>.md")
    source = Path(sys.argv[1])
    answer = HTML_FOLDER / f"{source.stem}-diagrams.html"
    drawings = load_drawings(answer)
    page = HTML_FOLDER / f"{source.stem}.html"
    page.write_text(render_page(source, drawings), encoding="utf-8")
    print(f"{source} -> {page.relative_to(REPO_ROOT)}")
    # Every fence that is no listing goes into the prompt, drawn or not, so
    # that one answer holds all drawings of the file, drawn alike.
    fences = [text for text in code_fences(source.read_text(encoding="utf-8")) if not is_listing(text)]
    missing = [text for text in fences if diagram_id(text) not in drawings]
    if missing:
        prompt = PROMPT_FOLDER / f"{source.stem}-prompt.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(prompt_text(fences), encoding="utf-8")
        print(
            f"{len(missing)} of {len(fences)} code fences have no drawing yet. "
            f"Give an LLM {prompt.relative_to(REPO_ROOT)}, "
            f"and save its answer as {answer.relative_to(REPO_ROOT)}."
        )


if __name__ == "__main__":
    main()
