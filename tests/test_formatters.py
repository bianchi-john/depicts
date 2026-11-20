import json
import re

import pytest

from depicts.formatters import FORMATTERS
from depicts.formatters.markdown import fence_for
from depicts.models import FileEntry, Report, Summary

README = "Intro\n```bash\nls\n```\nMore text\n"


def make_report(files=None, summary=True):
    return Report(
        stack="Python",
        tree=["├── main.py", "└── README.md"],
        summary=Summary(["main.py"], {".py": 1}, ["pyproject.toml"], "~10 tokens (0.1 KB)") if summary else None,
        files=files if files is not None else [FileEntry("main.py", content='print("hello")\n', total_lines=1,
                                                          shown_lines=1)],
    )


def test_plain():
    out = FORMATTERS["plain"](make_report())
    assert " STACK: Python" in out
    assert "Entry points : main.py" in out
    assert "Output size  : ~10 tokens (0.1 KB)" in out
    assert "[DIRECTORY TREE]" in out
    assert '[FILE: main.py]\n════════════════════════════════\nprint("hello")\n' in out


def test_plain_without_summary():
    out = FORMATTERS["plain"](make_report(summary=False))
    assert "[SUMMARY]" not in out


def test_skipped_and_truncated_files_are_labelled():
    files = [
        FileEntry("logo.png", skipped="binary file"),
        FileEntry("big.py", content="a\nb\n", truncated=True, shown_lines=2, total_lines=900),
    ]
    out = FORMATTERS["plain"](make_report(files))
    assert "<skipped: binary file>" in out
    assert "a\nb\n... (truncated: showing 2 of 900 lines) ..." in out


@pytest.mark.parametrize("text, fence", [
    ("plain", "```"),
    ("has ``` inside", "````"),
    ("has ````` inside", "``````"),
])
def test_fence_for(text, fence):
    assert fence_for(text) == fence


def headings_outside_code(markdown):
    """Headings a CommonMark renderer would see (i.e. not inside a fenced block)."""
    headings, fence = [], None
    for line in markdown.splitlines():
        if fence is None:
            opening = re.match(r"^(`{3,})", line)
            if opening:
                fence = opening.group(1)
            elif line.startswith("#"):
                headings.append(line)
        elif re.fullmatch(rf"`{{{len(fence)},}}\s*", line):
            fence = None
    assert fence is None, "unclosed code block"
    return headings


def test_markdown_code_blocks_survive_backticks_in_content():
    # Regression: the README's own ``` closed the surrounding block.
    files = [FileEntry("README.md", content=README), FileEntry("main.py", content="x = 1\n")]
    out = FORMATTERS["md"](make_report(files))
    assert "## File: `README.md`\n````md\nIntro\n```bash\nls\n```\nMore text\n````" in out
    assert headings_outside_code(out) == [
        "# Project Summary", "## Summary", "## Directory Tree", "## File: `README.md`", "## File: `main.py`",
    ]


def test_markdown_language_hints():
    files = [FileEntry("Dockerfile.dev", content="FROM x\n"), FileEntry("app/main.py", content="x = 1\n")]
    out = FORMATTERS["md"](make_report(files))
    assert "```dockerfile\nFROM x\n```" in out
    assert "```py\nx = 1\n```" in out


def test_markdown_summary():
    out = FORMATTERS["md"](make_report())
    assert out.startswith("# Project Summary\n**STACK:** Python\n")
    assert "- **Source files:** 1 .py file" in out


def test_json_is_structured():
    files = [
        FileEntry("main.py", content='print("hello")\n', shown_lines=1, total_lines=1),
        FileEntry("logo.png", skipped="binary file"),
    ]
    data = json.loads(FORMATTERS["json"](make_report(files)))
    assert data["stack"] == "Python"
    assert data["summary"]["source_files"] == {".py": 1}
    assert data["tree"] == ["├── main.py", "└── README.md"]
    assert data["files"][0] == {"path": "main.py", "content": 'print("hello")\n', "truncated": False,
                                "shown_lines": 1, "total_lines": 1, "skipped": None}
    assert data["files"][1]["content"] is None
    assert data["files"][1]["skipped"] == "binary file"


def test_json_without_summary():
    assert json.loads(FORMATTERS["json"](make_report(summary=False)))["summary"] is None
