# Contributing to depicts

Thank you for your interest in contributing! `depicts` is designed to be highly modular and easily extensible.

## Architecture Overview

The tool is split into four main subsystems:
1. **Config (`depicts/config.py`)**: Loads the `.depicts.yml` configurations.
2. **Detectors (`depicts/detectors/`)**: Identify the software stack and define which files are high-priority.
3. **Collectors (`depicts/collectors.py`)**: Traverse the directory tree, respecting excludes, and safely read file contents.
4. **Formatters (`depicts/formatters/`)**: Take the raw structured data and output it nicely.

The main orchestrator (`depicts/cli.py`) wires these subsystems together.

## How to add a new Stack Detector

1. Create a new file in `depicts/detectors/`, e.g., `ruby.py`.
2. Define a function that takes `root` (the absolute path of the directory) and returns a tuple `(Stack Name, [Priority Files])`. Return `None` if the stack isn't detected.
   ```python
   # depicts/detectors/ruby.py
   import os

   def detect_ruby(root):
       if os.path.exists(os.path.join(root, 'Gemfile')):
           return "Ruby", ['README.md', 'Gemfile', 'config/routes.rb']
       return None
   ```
3. Register your new detector in `depicts/detectors/__init__.py` by importing it and adding it to the `DETECTORS` list.

## How to add a new Output Formatter

1. Create a new file in `depicts/formatters/`, e.g., `json_out.py`.
2. Define a function with the following signature:
   ```python
   def format_json(stack, summary, tree, files_content):
       import json
       return json.dumps({
           'stack': stack,
           'summary': summary,
           'tree': tree,
           'files': dict(files_content)
       }, indent=2)
   ```
3. Register it in `depicts/formatters/__init__.py` inside the `FORMATTERS` dictionary.
4. Update the `--format` CLI choices in `depicts/cli.py`.
