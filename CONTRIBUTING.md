# Contributing to depicts

Thank you for your interest in contributing! `depicts` is designed to be modular and easy to extend.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest          # run the test suite
ruff check .    # lint
```

CI runs the same commands on Python 3.10 (the version in the snap's `core22` base), 3.12 and 3.13, and builds the snap.

When you fix a bug, add a test that fails without the fix.

## Architecture overview

The main orchestrator, `depicts/cli.py`, wires these modules together:

| Module | Role |
|---|---|
| `config.py` | Loads and validates `.depicts.yml` and merges it with the CLI arguments into a `Config`. |
| `detectors/` | Identify the stack and return the patterns of its priority files. |
| `collectors.py` | `scan_project` walks the tree once, applying excludes and `.gitignore` rules. `resolve_files` picks the files to show, `read_file` reads them safely (truncation, binary, secret and symlink checks) and `build_summary` computes the summary. |
| `ignore.py` | Exclude patterns (`--exclude`, `exclude_dirs`) and Git ignore rules (via `pathspec`). |
| `patterns.py` | Glob matching relative to the project root (`*` does not cross `/`, `**/` matches any depth). |
| `models.py` | The data passed between modules: `FileRef`, `FileEntry`, `Summary` and `Report`. |
| `formatters/` | Turn a `Report` into text. |

## How to add a new stack detector

1. Create a new file in `depicts/detectors/`, e.g. `ruby.py`.
2. Define a function that takes `root` (the absolute path of the project) and returns `(stack_name, [patterns])`, or `None` if the stack isn't detected. Patterns are relative to the root: `Gemfile` matches only the root file, and `**/*.rb` would match at any depth (use that sparingly).
   ```python
   # depicts/detectors/ruby.py
   import os

   def detect_ruby(root):
       if os.path.exists(os.path.join(root, 'Gemfile')):
           return "Ruby", ['Gemfile', 'config/routes.rb', 'app/models/*.rb']
       return None
   ```
   README files and GitHub workflows are added for every project, so you don't need to list them. Avoid lock files: they are large and add little context.
3. Register the detector in `depicts/detectors/__init__.py` by adding it to the `DETECTORS` list.
4. Add tests to `tests/test_detectors.py`.

## How to add a new output formatter

1. Create a new file in `depicts/formatters/`, e.g. `xml_out.py`.
2. Define a function that takes a `depicts.models.Report` and returns a string:
   ```python
   def format_xml(report):
       ...  # report.stack, report.summary (None with --short), report.tree, report.files
   ```
   `FileEntry.body()` gives the text to show for a file, with truncation and skip notes. Use the individual fields (`content`, `truncated`, `skipped`, …) for structured formats.
3. Register it in the `FORMATTERS` dictionary in `depicts/formatters/__init__.py`. The `--format` choices are taken from that dictionary.
4. Add tests to `tests/test_formatters.py`.

## Releasing

Bump `__version__` in `depicts/__init__.py`: the Python package and the snap both read the version from there.
