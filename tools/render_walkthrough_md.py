"""Render the walkthrough's chapters as markdown, for reading.

Reads tests/test_walkthrough.py as text and writes
tmp/walkthrough/walkthrough.md. The tests are the source; the markdown is
generated, so it says what the passing tests say, and is never edited by
hand.

How the test file becomes markdown:
- The module docstring becomes the introduction. Its indented blocks (the
  programs with their addresses) become code blocks.
- Each test named test_chapter_<n>_<program>_<topic> becomes a chapter,
  headed "<n>. <Topic>". A chapter whose program differs from the one
  before starts a new part, headed with the program's name.
- In a chapter, a block of comment lines at the function's own indent
  becomes prose; a "#" line alone separates paragraphs. Everything else
  becomes a Python code block, with its line-end and indented comments
  kept, since they explain the rows.

Run from the repo root:

    make walkthrough-md
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "test_walkthrough.py"
TARGET = ROOT / "tmp" / "walkthrough" / "walkthrough.md"

# test_chapter_3_nested_loops_split_tiles: number, then program and topic.
CHAPTER = re.compile(r"test_chapter_(\d+)_(.+)")

# The programs a chapter name may start with, longest first, so that a
# program whose name begins with another's is found whole.
PROGRAMS = sorted(
    (path.stem for path in (ROOT / "src" / "papple2" / "programs").glob("*.py")
     if path.stem != "__init__"),
    key=len,
    reverse=True,
)

# A chapter's body is indented by one level.
BODY_INDENT = "    "


def render_docstring(docstring: str) -> list[str]:
    """The module docstring as markdown: its first line as the title, its
    indented blocks fenced as code."""
    lines = docstring.strip("\n").splitlines()
    out = [f"# {lines[0].rstrip('.')}"]
    in_code = False
    for line in lines[1:]:
        if line.startswith("    "):
            if not in_code:
                out.append("```text")
                in_code = True
            out.append(line[4:])
        elif not line.strip():
            out.append("")
        else:
            if in_code:
                # The blank lines after the code belong to the prose.
                blanks = 0
                while out[-1] == "":
                    out.pop()
                    blanks += 1
                out.extend(["```"] + [""] * blanks)
                in_code = False
            out.append(line)
    if in_code:
        while out[-1] == "":
            out.pop()
        out.append("```")
    return out


def split_name(name: str) -> tuple[int, str, str]:
    """(number, program, topic) of a chapter's test name."""
    number, rest = CHAPTER.fullmatch(name).groups()
    for program in PROGRAMS:
        if rest.startswith(program + "_"):
            topic = rest[len(program) + 1:]
            return int(number), program, topic.replace("_", " ")
    raise ValueError(f"{name}: no program of papple2.programs in its name")


def body_lines(source_lines: list[str], node: ast.FunctionDef) -> list[str]:
    """The lines of a chapter's body, without its def line(s), dedented by
    one level."""
    lines = source_lines[node.lineno - 1:node.end_lineno]
    # The signature may span lines; it ends at the first line ending in ":".
    header = next(i for i, line in enumerate(lines) if line.rstrip().endswith(":"))
    return [line[len(BODY_INDENT):] if line.startswith(BODY_INDENT) else line.strip()
            for line in lines[header + 1:]]


def render_chapter(lines: list[str]) -> list[str]:
    """A chapter's body as markdown: comment blocks at the body's own
    indent as prose, everything else as code."""
    out: list[str] = []
    prose: list[str] = []
    code: list[str] = []

    def flush_prose() -> None:
        paragraph: list[str] = []
        for text in prose + [""]:
            if text:
                paragraph.append(text)
            elif paragraph:
                out.extend([" ".join(paragraph), ""])
                paragraph = []
        prose.clear()

    def flush_code() -> None:
        while code and not code[-1].strip():
            code.pop()
        while code and not code[0].strip():
            code.pop(0)
        if code:
            out.extend(["```python", *code, "```", ""])
        code.clear()

    for line in lines:
        if line.startswith("#"):
            flush_code()
            prose.append(line[1:].strip())
        else:
            flush_prose()
            code.append(line)
    flush_prose()
    flush_code()
    return out


def render(source: str) -> str:
    """The whole walkthrough as markdown."""
    tree = ast.parse(source)
    source_lines = source.splitlines()
    out = render_docstring(ast.get_docstring(tree, clean=False) or "")

    part = 0
    program_before = None
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and CHAPTER.fullmatch(node.name)):
            continue
        number, program, topic = split_name(node.name)
        if program != program_before:
            part += 1
            out.extend(["", f"## Part {part}: `{program}`", ""])
            program_before = program
        out.extend([f"### {number}. {topic[0].upper()}{topic[1:]}", ""])
        out.extend(render_chapter(body_lines(source_lines, node)))
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
