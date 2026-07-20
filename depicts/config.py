"""
Configuration management for depicts.
Handles loading and merging .depicts.yml with default settings and parsing .gitignore.
"""
import os
import sys
import yaml
import fnmatch

DEFAULT_EXCLUDES = {'.git', '__pycache__', 'node_modules', '.venv', 'dist', 'build', '.idea', '.vscode', '.egg-info'}

def parse_gitignore(root_path):
    """
    Parses .gitignore file in the root path.
    Returns a list of tuples: (pattern, is_dir_only, is_anchored)
    """
    rules = []
    gitignore_path = os.path.join(root_path, '.gitignore')
    if not os.path.isfile(gitignore_path):
        return rules
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Determine properties of the rule
                is_dir_only = line.endswith('/')
                normalized = line.rstrip('/')
                is_anchored = normalized.startswith('/')
                if is_anchored:
                    normalized = normalized[1:]
                rules.append((normalized, is_dir_only, is_anchored))
    except Exception as e:
        print(f"Warning: Could not parse .gitignore: {e}", file=sys.stderr)
    return rules

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
            print(f"Warning: Could not parse .depicts.yml: {e}", file=sys.stderr)

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

    # Parse gitignore
    gitignore_rules = parse_gitignore(root_path)

    return {
        'excludes': excludes,
        'max_lines': max_lines,
        'force_includes': force_includes,
        'gitignore_rules': gitignore_rules
    }

