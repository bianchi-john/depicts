"""
Configuration management for depicts.
Handles loading and merging .depicts.yml with default settings.
"""
import os
import yaml

DEFAULT_EXCLUDES = {'.git', '__pycache__', 'node_modules', '.venv', 'dist', 'build', '.idea', '.vscode', '.egg-info'}

def load_config(root_path, cli_excludes=None, cli_lines=None, cli_force_includes=None):
    """
    Loads config from .depicts.yml if it exists, and merges it with CLI arguments.
    """
    config = {}
    config_path = os.path.join(root_path, '.depicts.yml')
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            # We'll just silently ignore or return the error.
            # Printing directly might disrupt the output formatting, but we'll allow it as a warning for now.
            print(f"Warning: Could not parse .depicts.yml: {e}")

    # Resolve excludes
    excludes = set(DEFAULT_EXCLUDES)
    if 'exclude_dirs' in config and config['exclude_dirs']:
        excludes.update(config['exclude_dirs'])
    if cli_excludes:
        excludes.update(cli_excludes)

    # Resolve max lines
    max_lines = 150
    if 'max_lines' in config and config['max_lines'] is not None:
        max_lines = config['max_lines']
    if cli_lines is not None:
        max_lines = cli_lines

    # Resolve extra files
    force_includes = list(cli_force_includes) if cli_force_includes else []
    if 'extra_files' in config and config['extra_files']:
        force_includes.extend(config['extra_files'])

    return {
        'excludes': excludes,
        'max_lines': max_lines,
        'force_includes': force_includes
    }
