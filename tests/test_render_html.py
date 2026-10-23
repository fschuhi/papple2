"""tools/render_html.py: a markdown file as an HTML page in docs/html/.

What the script adds to markdown-it-py: listings in the editor's colors,
other code fences kept exactly, and links that still lead to their file
from docs/html/.
"""

import sys
from pathlib import Path

# The repo root: this file lies in tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent

# tools/ is no package; its scripts are imported from their folder.
sys.path.insert(0, str(REPO_ROOT / "tools"))

from render_html import color_line, relink, render_code  # noqa: E402


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
