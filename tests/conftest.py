import pytest

from depicts.cli import main


@pytest.fixture
def make_files(tmp_path):
    """Create files from a {relative_path: content} mapping and return the root."""
    def _make(files, root=None):
        root = root or tmp_path
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        return root
    return _make


@pytest.fixture
def run_cli(capsys):
    """Run the CLI in-process; returns (exit_code, stdout, stderr)."""
    def _run(*argv):
        with pytest.raises(SystemExit) as exc:
            main([str(a) for a in argv])
        out, err = capsys.readouterr()
        return exc.value.code, out, err
    return _run

