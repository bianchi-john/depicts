# Depicts

Summarize a software project for AI context.
Run without arguments to get an instant summary of the current directory.

## Installation

As a snap:

```bash
sudo snap install depicts
```

Or from source with pip / pipx (Python 3.10+):

```bash
pipx install git+https://github.com/bianchi-john/depicts
```

*(During local development you can build the snap with `snapcraft` and install it with `sudo snap install ./depicts_*.snap --dangerous`.)*

## Usage

Run `depicts` from the root of your project:

```bash
cd my-project
depicts                      # print the summary
depicts --clipboard          # copy it, ready to paste into an AI chat
depicts --format md --output context.md
```

The output contains:

- **Stack**: the detected technologies (Python, Node.js, Rust, Go, Docker, Kubernetes).
- **Summary**: entry points, config files, source-file counts and the size of the output in tokens.
- **Directory tree**: 3 levels by default. Directories cut by `--depth` show how many files they contain, and very large directories are collapsed.
- **Priority files**: the files that best describe the project, such as the README, manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`), entry points and the top-level modules of Python packages.

### What gets excluded

- Common noise: `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `*.egg-info`, `.idea`, `.vscode`.
- Everything matched by your `.gitignore` files (nested ones and `.git/info/exclude` included, with `!` negations).
- Anything you pass to `--exclude` or list in `exclude_dirs`.

### Truncation

- Files up to 200 lines are shown in full; longer files are cut to 150 lines, with a note saying how many lines the file has.
- Setting `--lines N` (or `max_lines`) makes `N` a hard limit for every file.
- README files get twice the budget.
- `--full` disables truncation.

### Safety

The output is meant to be pasted into AI tools, so depicts never includes:

- the content of files that usually hold secrets (`.env`, `*.pem`, `*.key`, `id_rsa`, `.npmrc`, …) unless you name them yourself with `--file`;
- files reached through a symlink that points outside the project;
- paths outside the project listed in `.depicts.yml` (a cloned repository cannot make depicts read your other files).

Binary files and files over 10 MB are listed as skipped. Symlinked directories are shown but not followed.

### Patterns

`--file`, `--exclude` and `.depicts.yml` take glob patterns:

| Pattern | Matches |
|---|---|
| `docs/setup.md` | that file |
| `scripts/*.sh` | `.sh` files directly in `scripts/` (`*` does not cross `/`) |
| `**/*.sql` | `.sql` files at any depth |
| `logs`, `*.log` (exclude only) | any file or directory with that name, at any depth |
| `src/tests` (exclude only) | that path from the project root |

### CLI arguments

```text
usage: depicts [-h] [--version] [--path PATH] [--file GLOB] [--output FILE]
               [--format {plain,md,json}] [--clipboard] [--short | --full] [--lines N]
               [--exclude PATTERN] [--depth N]

Summarize a software project for AI context.
Run without arguments to get an instant summary of the current directory.

options:
  -h, --help            Show this help message and exit
  --version             Show the version number and exit

targeting:
  --path PATH           Path to the project root (default: current directory)
  --file GLOB           Force include a file or glob pattern, relative to the project root
                        (can be repeated; use **/ to match at any depth, e.g. "**/*.sql")

output:
  --output FILE         Write output to a file instead of stdout
  --format {plain,md,json}
                        Output format: plain text with ASCII separators (default),
                        Markdown with fenced code blocks, or JSON
  --clipboard           Copy output to the clipboard instead of printing it to stdout
                        (can be combined with --output)

verbosity:
  --short, --no-content
                        Show only stack detection and directory tree, no file contents
  --full                Show full content of all priority files without truncation
  --lines N             Max lines to show per file (default: 150; files up to 200
                        lines are shown in full unless this is set). Overrides config

filtering:
  --exclude PATTERN     Exclude a directory, file or glob pattern (can be repeated, e.g.
                        --exclude logs --exclude src/tests --exclude "*.log")
  --depth N             Max directory tree depth (default: 3)
```

`--clipboard` uses the first available tool among `pbcopy`, `wl-copy` (on Wayland), `xclip`, `xsel` and `clip.exe`.

### JSON output

```json
{
  "stack": "Python",
  "summary": {
    "entry_points": ["mypkg/__main__.py"],
    "source_files": {".py": 12},
    "config_files": ["pyproject.toml"],
    "output_size": "~4,210 tokens (16.9 KB)"
  },
  "tree": ["├── mypkg/", "│   ├── __init__.py", "…"],
  "files": [
    {"path": "pyproject.toml", "content": "…", "truncated": false,
     "shown_lines": 30, "total_lines": 30, "skipped": null}
  ]
}
```

`summary` is `null` with `--short`. For skipped files, `content` is `null` and `skipped` gives the reason.

## Configuration

To change the defaults, put a `.depicts.yml` file in the root of your project. See [`.depicts.yml.example`](.depicts.yml.example) for the available settings. Invalid values are reported as warnings and ignored.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture, how to run the tests and how to add stack detectors or output formatters.
