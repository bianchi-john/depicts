"""
Configuration management for depicts.
Loads ``.depicts.yml``, validates it and merges it with the CLI arguments.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import yaml

DEFAULT_EXCLUDES = (
    '.git', '__pycache__', 'node_modules', '.venv', 'dist', 'build', '.idea', '.vscode', '*.egg-info',
)
DEFAULT_MAX_LINES = 150
# Unless the user sets a line limit, files up to this many lines are shown in
# full, so that a 160-line file is not cut at 150.
DEFAULT_FULL_FILE_THRESHOLD = 200

KNOWN_KEYS = {'exclude_dirs', 'max_lines', 'extra_files'}


@dataclass
class Config:
    excludes: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    max_lines: int = DEFAULT_MAX_LINES
    # True when the limit comes from --lines or .depicts.yml: it is then a hard limit.
    max_lines_explicit: bool = False
    extra_files: list[str] = field(default_factory=list)  # from .depicts.yml: untrusted
    cli_files: list[str] = field(default_factory=list)    # from --file: chosen by the user

    @property
    def truncate_threshold(self) -> int:
        """Files with more lines than this are truncated to ``max_lines``."""
        if self.max_lines_explicit:
            return self.max_lines
        return max(self.max_lines, DEFAULT_FULL_FILE_THRESHOLD)


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _string_list(value, key: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings = [v for v in value if isinstance(v, str)]
        if len(strings) != len(value):
            _warn(f"'{key}' in .depicts.yml contains non-string items; they were ignored.")
        return strings
    _warn(f"'{key}' in .depicts.yml must be a list of strings; it was ignored.")
    return []


def _read_yaml(config_path: str) -> dict:
    try:
        with open(config_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        _warn(f"could not parse .depicts.yml: {e}")
        return {}
    if data is None:
        return {}
    if not isinstance(data, dict):
        _warn(".depicts.yml must contain a mapping of settings (e.g. 'max_lines: 100'); it was ignored.")
        return {}
    for key in data:
        if key not in KNOWN_KEYS:
            _warn(f"unknown setting '{key}' in .depicts.yml (known: {', '.join(sorted(KNOWN_KEYS))}).")
    return data


def load_config(root_path, cli_excludes=None, cli_lines=None, cli_force_includes=None) -> Config:
    """Load ``.depicts.yml`` if present and merge it with the CLI arguments (CLI wins)."""
    config = Config()
    data = {}
    config_path = os.path.join(root_path, '.depicts.yml')
    if os.path.isfile(config_path):
        data = _read_yaml(config_path)

    config.excludes.extend(_string_list(data.get('exclude_dirs'), 'exclude_dirs'))
    config.excludes.extend(cli_excludes or [])

    max_lines = data.get('max_lines')
    if max_lines is not None:
        if isinstance(max_lines, int) and not isinstance(max_lines, bool) and max_lines >= 1:
            config.max_lines = max_lines
            config.max_lines_explicit = True
        else:
            _warn(f"'max_lines' in .depicts.yml must be a positive integer, got {max_lines!r}; "
                  f"using {DEFAULT_MAX_LINES}.")
    if cli_lines is not None:
        config.max_lines = cli_lines
        config.max_lines_explicit = True

    config.extra_files = _string_list(data.get('extra_files'), 'extra_files')
    config.cli_files = list(cli_force_includes or [])
    return config
