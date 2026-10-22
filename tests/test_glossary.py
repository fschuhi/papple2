"""The glossary in the code: words docs/glossary.md rules out stay out.

Section 2 of the glossary names positions in code by address: before and
after, lower and higher. The word it forbids is spelled in two halves
here, so this file does not find itself.
"""

import re
from pathlib import Path

# The repo root: this file lies in tests/.
REPO_ROOT = Path(__file__).resolve().parent.parent

# The folders that hold the code, its tests and its tools.
CODE_FOLDERS = ("src", "scripts", "tests", "tools")

FORBIDDEN = "be" + "hind"


def test_the_code_never_says_the_forbidden_word() -> None:
    # In any case and anywhere in a line: at the start of a sentence, and
    # inside a name such as left_be + hind, too.
    word = re.compile(FORBIDDEN, re.IGNORECASE)
    found = [
        f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"
        for folder in CODE_FOLDERS
        for path in sorted((REPO_ROOT / folder).rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if word.search(line)
    ]

    assert not found, (
        f'"{FORBIDDEN}" names a position in code; docs/glossary.md, section 2, '
        "says after (or end, for a range):\n" + "\n".join(found)
    )
