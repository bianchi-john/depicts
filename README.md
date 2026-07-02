# Depicts

Summarize a software project for AI context.
Run without arguments to get an instant summary of the current directory.

## Installation

The tool is packaged as a snap. To install:

```bash
sudo snap install depicts
```

*(Note: During local development, you can build and install it using `snapcraft` and `sudo snap install ./depicts_*.snap --dangerous`)*

## Usage

Simply run `depicts` from the root of your project:

```bash
cd my-project
depicts
```

By default, it outputs a plain-text project summary to `stdout` containing:
- The detected software stack (e.g., Python, Node.js).
- A 3-level directory tree (excluding common noise like `.git` or `node_modules`).
- The contents of priority files for the stack (up to 150 lines per file).

### CLI Arguments

```text
usage: depicts [OPTIONS]

Summarize a software project for AI context.
Run without arguments to get an instant summary of the current directory.

options:
  -h, --help            Show this help message and exit
  --version             show program's version number and exit

targeting:
  --path PATH           Path to the project root (default: current directory)
  --file GLOB           Force include a specific file or glob pattern in the output

output:
  --output FILE         Write output to a file instead of stdout
  --format {plain,md,json}
                        Output format: plain text with ASCII separators (default)
                        or Markdown with fenced code blocks or JSON
  --clipboard           Copy output to clipboard instead of printing to stdout

verbosity:
  --short               Show only stack detection and directory tree, no file contents
  --full                Show full content of all priority files without truncation
  --lines N             Max lines to show per file (default: 150, overrides config)
  --no-content          Alias for --short

filtering:
  --exclude DIR         Exclude an additional directory or path (can be repeated, e.g.
                        --exclude logs --exclude src/tests)
  --depth N             Max directory tree depth (default: 3)
```

## Configuration

You can override defaults by placing a `.depicts.yml` file in the root of your project. See `.depicts.yml.example` for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for architecture details and how to extend `depicts` with new stack detectors or output formatters.

