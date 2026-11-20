"""
Exclusion rules: user/config excludes and Git ignore files.
"""
from __future__ import annotations

import os
import sys
from fnmatch import fnmatchcase

import pathspec

from .patterns import normalize


class ExcludeMatcher:
    """Matches the ``--exclude`` / ``exclude_dirs`` patterns.

    * A pattern without ``/`` (``node_modules``, ``*.log``) matches an entry
      with that name at any depth; glob wildcards are supported.
    * A pattern with ``/`` (``src/tests``, ``docs/*/build``) matches that path
      relative to the project root.

    Trailing and leading slashes and a leading ``./`` are ignored, so
    ``logs``, ``logs/`` and ``./logs/`` are equivalent.
    """

    def __init__(self, patterns):
        self.name_patterns: list[str] = []
        self.path_patterns: list[str] = []
        for raw in patterns:
            pattern = normalize(raw).strip("/")
            if not pattern:
                continue
            if "/" in pattern:
                self.path_patterns.append(pattern)
            else:
                self.name_patterns.append(pattern)

    def matches(self, rel_path: str) -> bool:
        """``rel_path`` is relative to the root. Parents are assumed already checked."""
        name = rel_path.rsplit("/", 1)[-1]
        if any(fnmatchcase(name, p) for p in self.name_patterns):
            return True
        return any(fnmatchcase(rel_path, p) for p in self.path_patterns)


def _read_spec(path: str) -> pathspec.GitIgnoreSpec | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return pathspec.GitIgnoreSpec.from_lines(f)
    except OSError as e:
        print(f"Warning: could not read {path}: {e.strerror}", file=sys.stderr)
        return None


class GitIgnore:
    """The ``.gitignore`` files that apply to one directory.

    Rules are evaluated the way Git does: every ``.gitignore`` from the root
    down to the entry's directory is consulted, and the last pattern that
    matches wins, so ``!pattern`` in a deeper file can re-include a file.
    ``.git/info/exclude`` applies to the whole repository.
    """

    def __init__(self, specs: tuple[tuple[str, pathspec.GitIgnoreSpec], ...] = ()):
        self._specs = specs

    @classmethod
    def for_root(cls, root: str) -> GitIgnore:
        exclude_file = os.path.join(root, ".git", "info", "exclude")
        if os.path.isfile(exclude_file):
            spec = _read_spec(exclude_file)
            if spec is not None:
                return cls((("", spec),))
        return cls()

    def descend(self, abs_dir: str, rel_dir: str) -> GitIgnore:
        """Return the rules for ``abs_dir``, adding its own ``.gitignore`` if present."""
        gitignore = os.path.join(abs_dir, ".gitignore")
        if not os.path.isfile(gitignore):
            return self
        spec = _read_spec(gitignore)
        if spec is None:
            return self
        return GitIgnore((*self._specs, (rel_dir, spec)))

    def is_ignored(self, rel_path: str, is_dir: bool) -> bool:
        decision = None
        for base, spec in self._specs:
            sub = rel_path[len(base) + 1:] if base else rel_path
            if is_dir:
                sub += "/"
            result = spec.check_file(sub)
            if result.include is not None:
                decision = result.include
        return bool(decision)
