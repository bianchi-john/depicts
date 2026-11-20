import os

import pytest
from helpers import symlinks_supported

from depicts.collectors import MAX_TREE_ENTRIES, scan_project
from depicts.config import DEFAULT_EXCLUDES


def scan(root, excludes=DEFAULT_EXCLUDES, depth=3):
    return scan_project(str(root), list(excludes), max_depth=depth)


# ------------------------------------------------------------------ excludes

def test_default_excludes(make_files):
    root = make_files({"src/main.py": "", "node_modules/x/index.js": "", "pkg.egg-info/PKG-INFO": ""})
    result = scan(root)
    assert result.files == ["src/main.py"]
    assert "node_modules" not in "\n".join(result.tree)


def test_exclude_trailing_slash_and_dot_prefix(make_files):
    # Regression: '--exclude logs/' used to exclude nothing.
    root = make_files({"logs/a.txt": "", "keep.txt": ""})
    for pattern in ("logs/", "./logs", "/logs/"):
        assert scan(root, [pattern]).files == ["keep.txt"]


def test_exclude_glob_and_path_patterns(make_files):
    root = make_files({"a.log": "", "sub/b.log": "", "src/tests/t.py": "", "tests/u.py": "", "src/app.py": ""})
    assert scan(root, ["*.log"]).files == ["src/app.py", "src/tests/t.py", "tests/u.py"]
    assert scan(root, ["src/tests"]).files == ["a.log", "src/app.py", "sub/b.log", "tests/u.py"]


# ------------------------------------------------------------------ gitignore

def test_gitignore_basic_and_dir_only(make_files):
    root = make_files({".gitignore": "*.log\nbuild_out/\n", "a.log": "", "build_out/x": "", "src/build_out": "",
                       "main.py": ""})
    files = scan(root).files
    assert "a.log" not in files and "build_out/x" not in files
    assert "src/build_out" in files  # a *file* named like a dir-only pattern is kept


def test_gitignore_negation(make_files):
    # Regression: '!keep.log' was ignored, so keep.log was wrongly excluded.
    root = make_files({".gitignore": "*.log\n!keep.log\n", "a.log": "", "keep.log": ""})
    assert scan(root).files == [".gitignore", "keep.log"]


def test_gitignore_double_star_matches_at_root(make_files):
    root = make_files({".gitignore": "**/gen\n", "gen/a.py": "", "src/gen/b.py": "", "src/c.py": ""})
    assert scan(root).files == [".gitignore", "src/c.py"]


def test_nested_gitignore_applies_to_its_directory_only(make_files):
    root = make_files({"sub/.gitignore": "*.tmp\n!special.tmp\n", "sub/a.tmp": "", "sub/special.tmp": "",
                       "top.tmp": ""})
    assert scan(root).files == ["sub/.gitignore", "sub/special.tmp", "top.tmp"]


def test_nested_gitignore_can_reinclude(make_files):
    root = make_files({".gitignore": "*.cfg\n", "a.cfg": "", "sub/.gitignore": "!b.cfg\n", "sub/b.cfg": ""})
    assert scan(root).files == [".gitignore", "sub/.gitignore", "sub/b.cfg"]


def test_git_info_exclude(make_files):
    root = make_files({".git/info/exclude": "secret_notes.txt\n", "secret_notes.txt": "", "main.py": ""})
    assert scan(root).files == ["main.py"]


# ------------------------------------------------------------------ tree

def test_tree_has_vertical_guides(make_files):
    root = make_files({"a/x.py": "", "a/y.py": "", "b.py": ""})
    assert scan(root).tree == [
        "├── a/",
        "│   ├── x.py",
        "│   └── y.py",
        "└── b.py",
    ]


def test_depth_limit_shows_counts_but_files_are_complete(make_files):
    # Regression: files below --depth were missing from the summary counts.
    files = {f"a/b/c/d/m{i}.py": "" for i in range(5)}
    files["a/top.py"] = ""
    root = make_files(files)
    result = scan(root, depth=3)
    assert len(result.files) == 6
    assert result.tree == [
        "└── a/",
        "    ├── b/",
        "    │   └── c/ (5 files)",
        "    └── top.py",
    ]


def test_tree_collapses_large_directories(make_files):
    root = make_files({f"many/f{i:03}.txt": "" for i in range(MAX_TREE_ENTRIES + 7)})
    result = scan(root)
    assert len(result.files) == MAX_TREE_ENTRIES + 7
    assert result.tree[-1] == "    └── … (+7 more entries)"
    assert len(result.tree) == 1 + MAX_TREE_ENTRIES + 1


def test_empty_root(tmp_path):
    assert scan(tmp_path).tree == []


@symlinks_supported
def test_symlink_loop_is_not_followed(make_files):
    # Regression: a 'loop -> .' symlink made setup.py appear 41 times.
    root = make_files({"setup.py": "x"})
    os.symlink(".", root / "loop")
    result = scan(root)
    assert result.files == ["setup.py"]
    assert "├── loop/ (symlink, not followed)" in result.tree


@symlinks_supported
def test_symlinked_external_directory_is_not_walked(make_files, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "big.txt").write_text("x")
    root = make_files({"main.py": ""})
    os.symlink(outside, root / "data")
    assert scan(root).files == ["main.py"]


@symlinks_supported
def test_unreadable_directory_is_marked(make_files):
    if os.geteuid() == 0:
        pytest.skip("root can read everything")
    root = make_files({"locked/x.py": "", "ok.py": ""})
    os.chmod(root / "locked", 0)
    try:
        result = scan(root)
    finally:
        os.chmod(root / "locked", 0o755)
    assert "├── locked/ (unreadable)" in result.tree
    assert result.files == ["ok.py"]
