"""
Data structures shared by the collectors, the CLI and the formatters.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# How many items of a list the text formatters print before collapsing the rest.
SUMMARY_LIST_LIMIT = 10


@dataclass(frozen=True)
class FileRef:
    """A file selected for output.

    ``explicit`` is True only for files the user asked for on the command line
    (``--file``): those may live outside the project root and bypass the
    sensitive-file filter, because the user chose them deliberately.
    """
    path: str
    explicit: bool = False


@dataclass
class FileEntry:
    """A selected file and what will be shown of it."""
    path: str
    content: str | None = None
    truncated: bool = False
    shown_lines: int | None = None
    total_lines: int | None = None
    skipped: str | None = None  # reason the content was left out, if it was

    def body(self) -> str:
        """Text representation used by the plain and Markdown formatters."""
        if self.skipped is not None:
            return f"<skipped: {self.skipped}>"
        text = (self.content or "").rstrip("\n")
        if self.truncated:
            text += f"\n... (truncated: showing {self.shown_lines} of {self.total_lines} lines) ..."
        return text


@dataclass
class Summary:
    entry_points: list[str] = field(default_factory=list)
    source_files: dict[str, int] = field(default_factory=dict)  # extension -> count
    config_files: list[str] = field(default_factory=list)
    output_size: str | None = None

    def rows(self) -> list[tuple[str, str]]:
        """Human-readable (label, value) pairs for the text formatters."""
        rows = [
            ("Entry points", _join_limited(self.entry_points)),
            ("Source files", _describe_sources(self.source_files)),
            ("Config files", _join_limited(self.config_files)),
        ]
        if self.output_size is not None:
            rows.append(("Output size", self.output_size))
        return rows


@dataclass
class Report:
    stack: str
    tree: list[str]
    summary: Summary | None
    files: list[FileEntry]


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _join_limited(items: list[str]) -> str:
    if not items:
        return "None detected"
    shown = ", ".join(items[:SUMMARY_LIST_LIMIT])
    hidden = len(items) - SUMMARY_LIST_LIMIT
    return f"{shown} (+{hidden} more)" if hidden > 0 else shown


def _describe_sources(counts: dict[str, int]) -> str:
    if not counts:
        return "None detected"
    return ", ".join(plural(n, f"{ext} file") for ext, n in counts.items())
