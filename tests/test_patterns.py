import pytest

from depicts.patterns import escapes_root, match


@pytest.mark.parametrize("pattern, path, expected", [
    ("README.md", "README.md", True),
    ("README.md", "docs/README.md", False),          # no implicit match at any depth
    ("**/README.md", "README.md", True),
    ("**/README.md", "a/b/README.md", True),
    ("src/*.py", "src/a.py", True),
    ("src/*.py", "src/sub/a.py", False),             # * does not cross /
    ("cmd/*/main.go", "cmd/server/main.go", True),
    ("a/**/b.txt", "a/b.txt", True),
    ("a/**/b.txt", "a/x/y/b.txt", True),
    ("docs/**", "docs/x/y.md", True),
    ("file?.txt", "file1.txt", True),
    ("file?.txt", "file/.txt", False),
    ("[ab].py", "a.py", True),
    ("[!ab].py", "c.py", True),
    ("[!ab].py", "a.py", False),
    ("./setup.py", "setup.py", True),
    ("weird[.txt", "weird[.txt", True),              # unclosed bracket is a literal
    ("a+b(c).txt", "a+b(c).txt", True),              # regex metacharacters are literal
])
def test_match(pattern, path, expected):
    assert match(pattern, path) is expected


@pytest.mark.parametrize("pattern, expected", [
    ("docs/a.md", False),
    ("scripts/*.sh", False),
    ("../secret.txt", True),
    ("docs/../../x", True),
    ("/etc/passwd", True),
    ("~/.ssh/id_rsa", True),
    ("C:/Windows/win.ini", True),
])
def test_escapes_root(pattern, expected):
    assert escapes_root(pattern) is expected
