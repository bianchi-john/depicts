"""
Glob patterns for selecting files, always relative to the project root.

Semantics (deliberately close to shell globbing, not to .gitignore):

* ``README.md``        matches only ``README.md`` in the project root
* ``src/*.py``         ``*`` and ``?`` never cross a ``/``: matches ``src/a.py``, not ``src/x/a.py``
* ``**/README.md``     ``**/`` matches zero or more directories: any ``README.md`` in the project
* ``docs/**``          a trailing ``**`` matches everything below ``docs/``
* ``[ab].py``          character classes work as in fnmatch (``[!ab]`` negates)
"""
from __future__ import annotations

import os
import re
from functools import lru_cache


def normalize(pattern: str) -> str:
    """Use forward slashes and drop a leading ``./``."""
    pattern = pattern.strip().replace("\\", "/")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return pattern


def escapes_root(pattern: str) -> bool:
    """True if the pattern could point outside the project root."""
    pattern = normalize(pattern)
    return (
        os.path.isabs(pattern)
        or pattern.startswith(("/", "~"))
        or re.match(r"^[A-Za-z]:", pattern) is not None
        or ".." in pattern.split("/")
    )


@lru_cache(maxsize=512)
def compile_glob(pattern: str) -> re.Pattern[str]:
    pattern = normalize(pattern).lstrip("/")
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            start = i + 1
            negate = pattern.startswith("!", start)
            if negate:
                start += 1
            # A "]" right after "[" or "[!" is a literal member of the class.
            end = pattern.find("]", start + 1 if pattern.startswith("]", start) else start)
            if end == -1:
                out.append(re.escape(c))
            else:
                body = pattern[start:end]
                for special in ("\\", "]", "[", "^"):
                    body = body.replace(special, "\\" + special)
                out.append(f"[{'^/' if negate else ''}{body}]")
                i = end + 1
                continue
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out) + r"\Z")


def match(pattern: str, rel_path: str) -> bool:
    return compile_glob(pattern).match(rel_path) is not None
