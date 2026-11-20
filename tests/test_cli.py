import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from helpers import file_headers, lines

from depicts import __version__
from depicts.cli import copy_to_clipboard
from depicts.formatters import FORMATTERS

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT = {
    "pyproject.toml": "[project]\nname = 'demo'\n",
    "README.md": "# Demo\n",
    "demo/__init__.py": "",
    "demo/cli.py": lines(300),
    "data/blob.bin": b"\x00\x01",
}


def test_end_to_end_plain(make_files, run_cli):
    root = make_files(PROJECT)
    code, out, err = run_cli("--path", root)
    assert code == 0, err
    assert " STACK: Python" in out
    assert file_headers(out) == ["README.md", "demo/__init__.py", "demo/cli.py", "pyproject.toml"]
    assert "... (truncated: showing 150 of 300 lines) ..." in out
    assert "Output size  : ~" in out


def test_lines_option_is_a_hard_limit(make_files, run_cli):
    root = make_files({"pyproject.toml": lines(50)})
    _, out, _ = run_cli("--path", root, "--lines", 3)
    assert "showing 3 of 50 lines" in out


def test_short_mode(make_files, run_cli):
    _, out, _ = run_cli("--path", make_files(PROJECT), "--no-content")
    assert "[DIRECTORY TREE]" in out
    assert "[SUMMARY]" not in out
    assert file_headers(out) == []


def test_full_mode(make_files, run_cli):
    _, out, _ = run_cli("--path", make_files(PROJECT), "--full")
    assert "line 299" in out
    assert "truncated" not in out


def test_json_output_is_valid_and_has_size(make_files, run_cli):
    _, out, _ = run_cli("--path", make_files(PROJECT), "--format", "json")
    data = json.loads(out)
    assert data["summary"]["output_size"].startswith("~")
    assert [f["path"] for f in data["files"]] == ["README.md", "demo/__init__.py", "demo/cli.py", "pyproject.toml"]


@pytest.mark.parametrize("argv", [
    ["--depth", "0"], ["--depth", "-1"], ["--lines", "0"], ["--lines", "abc"],
    ["--short", "--full"], ["--format", "xml"],
])
def test_invalid_arguments_are_rejected(argv, run_cli):
    code, _, err = run_cli(*argv)
    assert code == 2
    assert "error:" in err


def test_format_choices_come_from_registry(run_cli):
    _, out, _ = run_cli("--help")
    assert "{" + ",".join(FORMATTERS) + "}" in out


def test_readme_usage_matches_help(run_cli, monkeypatch):
    # The usage block in README.md is copied from --help; this keeps the two in sync.
    monkeypatch.setenv("COLUMNS", "100")
    _, out, _ = run_cli("--help")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split("### CLI arguments\n\n```text\n", 1)[1].split("\n```", 1)[0]
    assert block == out.rstrip("\n"), "README usage is stale: paste the output of `COLUMNS=100 depicts --help`"


def test_missing_path(tmp_path, run_cli):
    code, _, err = run_cli("--path", tmp_path / "nope")
    assert code == 1
    assert "is not a directory" in err


def test_empty_directory(tmp_path, run_cli):
    _, out, _ = run_cli("--path", tmp_path)
    assert "(empty directory)" in out


def test_output_and_clipboard_can_be_combined(make_files, run_cli, tmp_path_factory):
    target = tmp_path_factory.mktemp("out") / "summary.txt"
    with patch("depicts.cli.copy_to_clipboard", return_value=(True, None)) as copy:
        code, out, err = run_cli("--path", make_files(PROJECT), "--output", target, "--clipboard")
    assert code == 0
    assert out == ""  # status messages go to stderr, stdout stays clean
    assert "Output written to" in err and "copied to clipboard" in err
    assert copy.call_args.args[0] == target.read_text(encoding="utf-8")


def test_clipboard_failure_is_reported(make_files, run_cli):
    with patch("depicts.cli.copy_to_clipboard", return_value=(False, "no clipboard tool found")):
        code, _, err = run_cli("--path", make_files(PROJECT), "--clipboard")
    assert code == 1
    assert "no clipboard tool found" in err


def test_permission_error_mentions_snap(make_files, run_cli):
    with patch("depicts.cli.scan_project", side_effect=PermissionError("denied")):
        code, _, err = run_cli("--path", make_files(PROJECT))
    assert code == 1
    assert "Snap" in err


def test_other_os_errors_do_not_crash(make_files, run_cli):
    with patch("depicts.cli.scan_project", side_effect=OSError(40, "Too many levels of symbolic links")):
        code, _, err = run_cli("--path", make_files(PROJECT))
    assert code == 1
    assert "Too many levels" in err


# ------------------------------------------------------------------ clipboard

class FakePopen:
    """Records clipboard invocations; tools listed in `missing` are 'not installed'."""

    def __init__(self, missing=(), failing=()):
        self.missing, self.failing, self.calls = set(missing), set(failing), []

    def __call__(self, cmd, **kwargs):
        if cmd[0] in self.missing:
            raise FileNotFoundError(cmd[0])
        fake = self

        class Proc:
            returncode = 1 if cmd[0] in fake.failing else 0

            def communicate(self, input=None, timeout=None):
                fake.calls.append((cmd[0], input))
                return None, None

        return Proc()


def test_clipboard_prefers_wl_copy_on_wayland(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    fake = FakePopen(missing={"pbcopy"})
    with patch("subprocess.Popen", fake):
        assert copy_to_clipboard("hi") == (True, None)
    assert fake.calls == [("wl-copy", b"hi")]


def test_clipboard_skips_wl_copy_without_wayland(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    fake = FakePopen(missing={"pbcopy"})
    with patch("subprocess.Popen", fake):
        copy_to_clipboard("hi")
    assert fake.calls[0][0] == "xclip"


def test_clipboard_uses_utf16_for_clip_exe(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    fake = FakePopen(missing={"pbcopy", "xclip", "xsel"})
    with patch("subprocess.Popen", fake):
        assert copy_to_clipboard("├──")[0]
    assert fake.calls == [("clip.exe", "├──".encode("utf-16"))]


def test_clipboard_reports_found_but_failing_tools(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    fake = FakePopen(missing={"pbcopy", "xsel", "clip.exe"}, failing={"xclip"})
    with patch("subprocess.Popen", fake):
        ok, error = copy_to_clipboard("hi")
    assert not ok
    assert error == "clipboard tool failed: xclip (exit code 1)"


def test_clipboard_reports_missing_tools(monkeypatch):
    fake = FakePopen(missing={"pbcopy", "wl-copy", "xclip", "xsel", "clip.exe"})
    with patch("subprocess.Popen", fake):
        ok, error = copy_to_clipboard("hi")
    assert not ok and error.startswith("no clipboard tool found")


# ------------------------------------------------------------------ real process

def run_module(*args, **kwargs):
    return subprocess.run([sys.executable, "-m", "depicts", *map(str, args)], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60, **kwargs)


def test_python_dash_m_works():
    result = run_module("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"depicts {__version__}"


def test_broken_pipe_is_silent(make_files):
    # Regression: `depicts | head -1` printed a BrokenPipeError traceback.
    root = make_files({"README.md": lines(20000)})  # well above the 64 KB pipe buffer
    proc = subprocess.Popen([sys.executable, "-m", "depicts", "--path", str(root), "--full"], cwd=REPO_ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.stdout.readline()
    proc.stdout.close()
    _, err = proc.communicate(timeout=60)
    assert b"BrokenPipeError" not in err
    assert b"Traceback" not in err


def test_depicts_on_itself_includes_its_own_sources():
    # Regression: run on its own repository, depicts used to show no source file at all.
    result = run_module()
    assert result.returncode == 0, result.stderr
    headers = file_headers(result.stdout)
    assert "depicts/cli.py" in headers
    assert "depicts/collectors.py" in headers
    assert "pyproject.toml" in headers
