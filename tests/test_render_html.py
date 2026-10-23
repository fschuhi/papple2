"""tools/render_html.py: a markdown file as an HTML page in docs/html/.

What the script adds to markdown-it-py: listings in the editor's colors,
other code fences kept exactly, links that still lead to their file from
docs/html/, and diagrams drawn by an LLM, found by their id.
"""

import sys
from pathlib import Path

# The repo root: this file lies in tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent

# tools/ is no package; its scripts are imported from their folder.
sys.path.insert(0, str(REPO_ROOT / "tools"))

from render_html import (  # noqa: E402
    code_fences,
    color_line,
    diagram_id,
    is_listing,
    load_drawings,
    prompt_text,
    relink,
    render_code,
)


def test_a_listing_line_gets_the_editors_colors() -> None:
    # As listing() prints it: gutter, address, bytes, instruction.
    assert color_line("| |   +-- 6286  b0 04                 BCS $628c") == (
        '| |   +-- 6286  <span class="bytes">b0 04</span>'
        '                 <span class="mn-bra">BCS</span> $628c'
    )
    # A mnemonic in the comment gets no span.
    assert color_line("6288  29 0f    AND #$0f   ; BPL always jumps") == (
        '6288  <span class="bytes">29 0f</span>    <span class="mn-logic">AND</span>'
        " #$0f   ; BPL always jumps"
    )
    # Written by hand: no bytes, several mnemonics, labels left alone.
    assert color_line("     .loop  DEY / BNE .loop / DEX / BNE SOUND_DELAY1") == (
        '     .loop  <span class="mn-inc">DEY</span> / <span class="mn-bra">BNE</span>'
        ' .loop / <span class="mn-inc">DEX</span> / <span class="mn-bra">BNE</span>'
        " SOUND_DELAY1"
    )
    # A row that never ran, after the gutter.
    assert color_line("| |   |   ... 629a-629c: 2 bytes never ran ...") == (
        '| |   |   <span class="gap">... 629a-629c: 2 bytes never ran ...</span>'
    )


def test_a_link_leads_to_its_file_from_docs_html() -> None:
    docs = REPO_ROOT / "docs"
    assert relink("glossary.md", docs) == "../glossary.md"
    assert relink("routine.md#span", docs) == "../routine.md#span"
    assert relink("../README.md", docs) == "../../README.md"
    # A web address and a place on the same page stay as they are.
    assert relink("https://6502.org", docs) == "https://6502.org"
    assert relink("#terms", docs) == "#terms"


def test_a_fence_that_is_no_listing_stays_exactly() -> None:
    diagram = "MOVE_GUARDS --JSR--> MOVE_GUARD\n   |  RTS & back <-- here\n"
    assert render_code(diagram) == (
        "<pre>MOVE_GUARDS --JSR--&gt; MOVE_GUARD\n   |  RTS &amp; back &lt;-- here</pre>\n"
    )


def test_the_same_text_gives_the_same_id() -> None:
    first = diagram_id("A --JSR--> B")
    assert first == diagram_id("A --JSR--> B\n")
    assert first != diagram_id("A --JMP--> B")
    assert first.startswith("diagram-") and len(first) == len("diagram-") + 8


def test_a_fence_with_a_drawing_becomes_the_svg(tmp_path: Path) -> None:
    diagram = "A --JSR--> B"
    command = "make html FILE=docs/routine.md"
    # The LLM's answer, with words and a code fence around the SVGs.
    answer = tmp_path / "answer.html"
    answer.write_text(
        "Here are the drawings:\n```html\n"
        f'<svg id="{diagram_id(diagram)}" width="100" height="40"><text>A</text></svg>\n'
        f'<svg id="{diagram_id(command)}" class="keep-text"/>\n```\n',
        encoding="utf-8",
    )
    drawings = load_drawings(answer)
    assert render_code(diagram, drawings) == (
        '<div class="diagram">\n'
        f'<svg id="{diagram_id(diagram)}" width="100" height="40"><text>A</text></svg>\n'
        "</div>\n"
    )
    # Kept as text on purpose, and not drawn yet: both stay <pre>.
    assert render_code(command, drawings) == f"<pre>{command}</pre>\n"
    assert render_code("A --JMP--> B", drawings) == "<pre>A --JMP--&gt; B</pre>\n"
    assert load_drawings(tmp_path / "no answer yet.html") == {}


def test_the_prompt_holds_every_fence_that_is_no_listing() -> None:
    markdown = (
        "# Page\n\n```\n6c9b  20 db 6c  JSR MOVE_GUARD\n```\n\n"
        "- item\n\n  ```\n  A --JSR--> B\n  ```\n\n```\nmake html\n```\n"
    )
    fences = [text for text in code_fences(markdown) if not is_listing(text)]
    # The fence inside the list item comes without its indentation.
    assert fences == ["A --JSR--> B", "make html"]
    prompt = prompt_text(fences)
    for text in fences:
        assert f"{diagram_id(text)}:\n\n```\n{text}\n```\n" in prompt
    assert "6c9b" not in prompt.split("The fences:")[1]
