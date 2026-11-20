"""
Directory scanning, file selection, file reading and summary generation.
"""
from __future__ import annotations

import os
import stat
import sys
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatchcase

from . import patterns
from .ignore import ExcludeMatcher, GitIgnore
from .models import FileEntry, FileRef, Summary, plural

# Directory entries listed per directory in the tree before collapsing the rest.
MAX_TREE_ENTRIES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024
# README files are the best single source of context, so they get a larger budget.
README_LINE_FACTOR = 2

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp', '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
    '.7z', '.pyc', '.so', '.dll', '.dylib', '.exe', '.bin', '.snap', '.class', '.jar', '.whl',
    '.woff', '.woff2', '.ttf', '.otf', '.mp3', '.mp4', '.mov', '.sqlite', '.db',
}

# Files whose content is never included unless the user names them with --file.
SENSITIVE_PATTERNS = (
    '.env', '.env.*', '*.pem', '*.key', '*.p12', '*.pfx', '*.keystore', '*.jks',
    'id_rsa*', 'id_dsa*', 'id_ecdsa*', 'id_ed25519*', '.npmrc', '.pypirc', '.netrc',
    'credentials', 'credentials.json', '.htpasswd',
)
SENSITIVE_ALLOWED = ('.env.example', '.env.sample', '.env.template', '*.pub')

ENTRY_POINT_NAMES = {
    'main.py', '__main__.py', 'app.py', 'wsgi.py', 'asgi.py', 'manage.py',
    'index.js', 'index.ts', 'index.mjs', 'main.js', 'main.ts', 'server.js', 'server.ts',
    'main.rs', 'main.go',
}
CONFIG_NAMES = {
    'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 'Pipfile',
    'package.json', 'tsconfig.json', 'Cargo.toml', 'go.mod', 'Makefile',
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml', 'Chart.yaml',
}
# Entry points and config files deeper than this many directories are not listed
# (otherwise every components/*/index.js would count as an entry point).
SUMMARY_MAX_DEPTH = 2
SOURCE_EXTENSIONS = {
    '.py', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.rs', '.go', '.java', '.kt', '.scala', '.swift',
    '.c', '.h', '.cc', '.cpp', '.hpp', '.cs', '.rb', '.php', '.sh',
}


# --------------------------------------------------------------------------- scan

@dataclass
class ScanResult:
    tree: list[str]
    files: list[str]  # every non-excluded file, at any depth, relative to the root


def _entry_kind(entry: os.DirEntry) -> str:
    """'dir', 'dir_link' (symlink to a directory) or 'file'."""
    try:
        if entry.is_symlink():
            return 'dir_link' if entry.is_dir() else 'file'
        return 'dir' if entry.is_dir(follow_symlinks=False) else 'file'
    except OSError:
        return 'file'


def scan_project(root: str, excludes, max_depth: int = 3) -> ScanResult:
    """Walk the project once.

    Builds the directory tree (``max_depth`` levels) and the list of all
    non-excluded files (no depth limit). Symbolic links to directories are
    shown but never followed, so link cycles and links to large external
    directories cannot blow up the scan. Raises ``OSError`` if the root itself
    cannot be listed.
    """
    matcher = ExcludeMatcher(excludes)
    files: list[str] = []

    def walk(abs_dir: str, rel_dir: str, depth: int, prefix: str, render: bool, ignore: GitIgnore):
        ignore = ignore.descend(abs_dir, rel_dir)
        with os.scandir(abs_dir) as it:
            entries = sorted(it, key=lambda e: e.name)

        visible = []
        for entry in entries:
            rel = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
            kind = _entry_kind(entry)
            if matcher.matches(rel) or ignore.is_ignored(rel, kind == 'dir'):
                continue
            visible.append((entry, rel, kind))

        render = render and depth <= max_depth
        shown = min(len(visible), MAX_TREE_ENTRIES)
        hidden = len(visible) - shown
        lines: list[str] = []
        count = 0
        for i, (entry, rel, kind) in enumerate(visible):
            in_view = render and i < shown
            is_last = i == shown - 1 and hidden == 0
            connector = "└── " if is_last else "├── "
            if kind == 'dir':
                note = ""
                try:
                    sub_lines, sub_count = walk(
                        entry.path, rel, depth + 1, prefix + ("    " if is_last else "│   "), in_view, ignore
                    )
                except OSError:
                    sub_lines, sub_count, note = [], 0, " (unreadable)"
                count += sub_count
                if in_view:
                    if depth == max_depth and sub_count:
                        note = f" ({plural(sub_count, 'file')})"
                    lines.append(f"{prefix}{connector}{entry.name}/{note}")
                    lines.extend(sub_lines)
            elif kind == 'dir_link':
                if in_view:
                    lines.append(f"{prefix}{connector}{entry.name}/ (symlink, not followed)")
            else:
                files.append(rel)
                count += 1
                if in_view:
                    lines.append(f"{prefix}{connector}{entry.name}")
        if render and hidden:
            lines.append(f"{prefix}└── … (+{hidden} more {'entry' if hidden == 1 else 'entries'})")
        return lines, count

    root = os.path.abspath(root)
    tree, _ = walk(root, "", 1, "", True, GitIgnore.for_root(root))
    return ScanResult(tree=tree, files=files)


# ------------------------------------------------------------------ file selection

def resolve_files(root, scanned_files, priority_patterns, extra_files=(), cli_files=()) -> list[FileRef]:
    """Select the files whose content goes into the output.

    * ``priority_patterns`` (from the detectors) and ``extra_files`` (from
      ``.depicts.yml``) only match files inside the project. ``extra_files``
      entries that point outside it (absolute paths, ``..``, ``~``) are
      rejected: a cloned repository must not be able to make depicts read
      files elsewhere on the machine.
    * ``cli_files`` (``--file``) are trusted: a literal path may point anywhere.

    A literal path that names an existing file is included even if it is
    excluded from the tree. Patterns follow ``depicts.patterns`` semantics.
    """
    root = os.path.abspath(root)
    selected: dict[str, bool] = {}

    def add(rel_path: str, explicit: bool) -> None:
        selected[rel_path] = selected.get(rel_path, False) or explicit

    def add_matches(pattern: str, explicit: bool) -> None:
        for rel_path in scanned_files:
            if patterns.match(pattern, rel_path):
                add(rel_path, explicit)

    for pattern in priority_patterns:
        add_matches(pattern, explicit=False)

    for pattern in extra_files:
        if patterns.escapes_root(pattern):
            print(f"Warning: ignoring extra_files entry {pattern!r} in .depicts.yml: "
                  "it points outside the project.", file=sys.stderr)
            continue
        add_matches(pattern, explicit=False)
        literal = patterns.normalize(pattern)
        if os.path.isfile(os.path.join(root, literal)):
            add(literal, explicit=False)

    for pattern in cli_files:
        candidate = os.path.expanduser(pattern)
        if os.path.isabs(candidate):
            candidate = os.path.normpath(candidate)
        else:
            add_matches(pattern, explicit=True)
            candidate = os.path.normpath(os.path.join(root, candidate))
        if os.path.isfile(candidate):
            add(os.path.relpath(candidate, root).replace('\\', '/'), explicit=True)

    return [FileRef(path, explicit) for path, explicit in sorted(selected.items())]


# ------------------------------------------------------------------- file reading

def _is_inside(root_real: str, path: str) -> bool:
    real = os.path.realpath(path)
    try:
        return os.path.commonpath([root_real, real]) == root_real
    except ValueError:  # different drives on Windows
        return False


def is_sensitive(rel_path: str) -> bool:
    name = rel_path.rsplit('/', 1)[-1]
    if any(fnmatchcase(name, p) for p in SENSITIVE_ALLOWED):
        return False
    return any(fnmatchcase(name, p) for p in SENSITIVE_PATTERNS)


def read_file(root: str, ref: FileRef, max_lines: int, threshold: int, full_mode: bool = False) -> FileEntry:
    """Read a selected file.

    Files longer than ``threshold`` lines are cut to ``max_lines`` (README
    files get ``README_LINE_FACTOR`` times both values); ``full_mode``
    disables truncation. Binary, oversized, sensitive and out-of-project files
    are reported as skipped instead of being read.
    """
    entry = FileEntry(path=ref.path)
    full_path = os.path.normpath(os.path.join(root, ref.path))

    if not ref.explicit:
        if not _is_inside(os.path.realpath(root), full_path):
            entry.skipped = "symlink pointing outside the project"
            return entry
        if is_sensitive(ref.path):
            entry.skipped = "may contain secrets (name it with --file to include it)"
            return entry
    if os.path.splitext(ref.path)[1].lower() in BINARY_EXTENSIONS:
        entry.skipped = "binary file"
        return entry

    try:
        st = os.stat(full_path)
        if not stat.S_ISREG(st.st_mode):
            entry.skipped = "not a regular file"
            return entry
        if st.st_size > MAX_FILE_SIZE:
            entry.skipped = f"file too large (>{MAX_FILE_SIZE // (1024 * 1024)} MB)"
            return entry
        with open(full_path, 'rb') as f:
            if b'\0' in f.read(8192):
                entry.skipped = "binary file"
                return entry

        if os.path.basename(ref.path).lower().startswith('readme'):
            max_lines *= README_LINE_FACTOR
            threshold *= README_LINE_FACTOR

        kept: list[str] = []
        total = 0
        with open(full_path, encoding='utf-8', errors='replace') as f:
            for line in f:
                total += 1
                if full_mode or total <= threshold:
                    kept.append(line)
    except OSError as e:
        entry.skipped = f"could not read file: {e.strerror or e}"
        return entry

    if not full_mode and total > threshold:
        entry.content = "".join(kept[:max_lines])
        entry.truncated = True
        entry.shown_lines = min(max_lines, total)
        entry.total_lines = total
    else:
        entry.content = "".join(kept)
        entry.shown_lines = entry.total_lines = total
    return entry


# ------------------------------------------------------------------------ summary

def _shallow_matches(files, names) -> list[str]:
    return sorted(
        f for f in files
        if f.rsplit('/', 1)[-1] in names and f.count('/') <= SUMMARY_MAX_DEPTH
    )


def build_summary(files) -> Summary:
    """Entry points, config files and source-file counts for the whole project."""
    counts = Counter(
        ext for ext in (os.path.splitext(f)[1] for f in files) if ext in SOURCE_EXTENSIONS
    )
    return Summary(
        entry_points=_shallow_matches(files, ENTRY_POINT_NAMES),
        source_files=dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        config_files=_shallow_matches(files, CONFIG_NAMES),
    )
