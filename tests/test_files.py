"""File selection (resolve_files) and file reading (read_file)."""
import os

import pytest
from helpers import lines, symlinks_supported

from depicts.collectors import MAX_FILE_SIZE, is_sensitive, read_file, resolve_files
from depicts.models import FileRef


def paths(refs):
    return [r.path for r in refs]


# ------------------------------------------------------------------ resolve_files

def test_root_patterns_do_not_match_nested_files(tmp_path):
    # Regression: 'index.js' used to match every */index.js in the project.
    scanned = ["index.js", "src/components/A/index.js", "docs/README.md", "README.md"]
    assert paths(resolve_files(tmp_path, scanned, ["index.js", "README.md"])) == ["README.md", "index.js"]


def test_double_star_pattern_matches_at_any_depth(tmp_path):
    scanned = ["README.md", "docs/README.md", "a/b/README.md"]
    assert paths(resolve_files(tmp_path, scanned, ["**/README.md"])) == sorted(scanned)


def test_results_are_sorted_and_deduplicated(tmp_path):
    scanned = ["b.py", "a.py"]
    assert paths(resolve_files(tmp_path, scanned, ["*.py", "a.py"], ["b.py"])) == ["a.py", "b.py"]


def test_extra_files_outside_root_are_rejected(make_files, tmp_path_factory, capsys):
    # Regression (security): .depicts.yml could pull any file on the machine into the output.
    secret = tmp_path_factory.mktemp("elsewhere") / "secret.txt"
    secret.write_text("TOP-SECRET")
    root = make_files({"README.md": "hi"})
    relative = os.path.relpath(secret, root)
    refs = resolve_files(root, ["README.md"], [], extra_files=[str(secret), relative, "~/.ssh/id_rsa"])
    assert paths(refs) == []
    assert capsys.readouterr().err.count("points outside the project") == 3


def test_extra_files_literal_inside_root_bypasses_excludes(make_files):
    root = make_files({"dist/bundle.js": "x"})
    refs = resolve_files(root, [], [], extra_files=["dist/bundle.js"])
    assert refs == [FileRef("dist/bundle.js", explicit=False)]


def test_cli_file_may_point_outside_root(make_files, tmp_path_factory):
    shared = tmp_path_factory.mktemp("shared") / "types.ts"
    shared.write_text("export type A = 1\n")
    root = make_files({"main.py": ""})
    refs = resolve_files(root, ["main.py"], [], cli_files=[str(shared)])
    assert refs == [FileRef(os.path.relpath(shared, root), explicit=True)]


def test_cli_absolute_path_is_not_used_as_a_glob(make_files):
    root = make_files({"etc/hosts": "project file"})
    refs = resolve_files(root, ["etc/hosts"], [], cli_files=["/nonexistent/etc/hosts"])
    assert refs == []


def test_cli_glob_marks_files_explicit(tmp_path):
    refs = resolve_files(tmp_path, ["a.sql", "db/b.sql"], ["a.sql"], cli_files=["**/*.sql"])
    assert refs == [FileRef("a.sql", True), FileRef("db/b.sql", True)]


# ------------------------------------------------------------------ read_file

def read(root, path, max_lines=150, threshold=200, full=False, explicit=False):
    return read_file(str(root), FileRef(path, explicit), max_lines, threshold, full)


def test_short_file_is_shown_in_full(make_files):
    entry = read(make_files({"a.txt": lines(180)}), "a.txt")
    assert not entry.truncated
    assert entry.total_lines == entry.shown_lines == 180


def test_long_file_is_truncated_with_total(make_files):
    entry = read(make_files({"a.txt": lines(300)}), "a.txt")
    assert entry.truncated
    assert (entry.shown_lines, entry.total_lines) == (150, 300)
    assert "line 149" in entry.content and "line 150" not in entry.content
    assert entry.body().endswith("... (truncated: showing 150 of 300 lines) ...")


def test_explicit_limit_applies_to_small_files(make_files):
    # Regression: --lines 5 was ignored for files under 201 lines.
    entry = read(make_files({"a.txt": lines(100)}), "a.txt", max_lines=5, threshold=5)
    assert entry.truncated
    assert entry.content == lines(5)


def test_readme_gets_a_larger_but_finite_budget(make_files):
    # Regression: README files were never truncated.
    entry = read(make_files({"README.md": lines(5000)}), "README.md", max_lines=5, threshold=5)
    assert entry.truncated
    assert entry.shown_lines == 10


def test_full_mode_disables_truncation(make_files):
    entry = read(make_files({"a.txt": lines(500)}), "a.txt", full=True)
    assert not entry.truncated and entry.total_lines == 500


def test_binary_files_are_skipped(make_files):
    root = make_files({"image.png": b"\x89PNG", "data.dat": b"abc\x00def"})
    assert read(root, "image.png").skipped == "binary file"
    assert read(root, "data.dat").skipped == "binary file"


def test_large_files_are_skipped(tmp_path):
    with open(tmp_path / "big.txt", "wb") as f:
        f.truncate(MAX_FILE_SIZE + 1)
    assert read(tmp_path, "big.txt").skipped.startswith("file too large")


def test_unreadable_file_reports_reason(tmp_path):
    entry = read(tmp_path, "missing.txt")
    assert entry.content is None
    assert entry.skipped.startswith("could not read file")


@pytest.mark.parametrize("name, expected", [
    (".env", True), (".env.production", True), ("config/server.key", True), ("id_rsa", True),
    ("id_ed25519", True), ("certs/ca.pem", True), (".npmrc", True),
    (".env.example", False), ("id_rsa.pub", False), ("environment.py", False), ("keys.py", False),
])
def test_is_sensitive(name, expected):
    assert is_sensitive(name) is expected


def test_sensitive_files_are_skipped_unless_explicit(make_files):
    root = make_files({".env": "API_KEY=123\n"})
    assert "secrets" in read(root, ".env").skipped
    assert read(root, ".env", explicit=True).content == "API_KEY=123\n"


@symlinks_supported
def test_symlink_to_outside_file_is_not_read(make_files, tmp_path_factory):
    # Regression (security): a repository could ship README.md -> /some/secret.
    secret = tmp_path_factory.mktemp("elsewhere") / "secret.txt"
    secret.write_text("TOP-SECRET")
    root = make_files({})
    os.symlink(secret, root / "README.md")
    entry = read(root, "README.md")
    assert entry.content is None
    assert entry.skipped == "symlink pointing outside the project"


@symlinks_supported
def test_symlink_inside_project_is_read(make_files):
    root = make_files({"docs/real.md": "hello\n"})
    os.symlink("docs/real.md", root / "README.md")
    assert read(root, "README.md").content == "hello\n"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs mkfifo")
def test_fifo_is_skipped_instead_of_blocking(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    assert read(tmp_path, "pipe").skipped == "not a regular file"
