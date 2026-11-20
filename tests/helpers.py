"""Helpers shared by the test modules."""
import os

import pytest


def lines(n, prefix="line"):
    return "".join(f"{prefix} {i}\n" for i in range(n))


def file_headers(output):
    return [line[len("[FILE: "):-1] for line in output.splitlines() if line.startswith("[FILE: ")]


symlinks_supported = pytest.mark.skipif(not hasattr(os, "symlink") or os.name == "nt",
                                        reason="symlinks need POSIX")
