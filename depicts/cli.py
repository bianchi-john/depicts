#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

from .collectors import build_summary, read_file, resolve_files, scan_project
from .config import DEFAULT_MAX_LINES, load_config
from .detectors import detect_stack
from .formatters import FORMATTERS
from .models import Report

_SIZE_PLACEHOLDER = "@@DEPICTS_OUTPUT_SIZE@@"
CLIPBOARD_TIMEOUT = 10


def _clipboard_commands():
    """Candidate clipboard tools, in order, with the encoding each expects."""
    commands = [(['pbcopy'], 'utf-8')]
    if os.environ.get('WAYLAND_DISPLAY'):
        commands.append((['wl-copy'], 'utf-8'))
    commands += [
        (['xclip', '-selection', 'clipboard'], 'utf-8'),
        (['xsel', '--clipboard', '--input'], 'utf-8'),
        # clip.exe (Windows / WSL) reads UTF-16 when the input starts with a BOM;
        # given UTF-8 it would mangle every non-ASCII character, tree lines included.
        (['clip.exe'], 'utf-16'),
    ]
    return commands


def copy_to_clipboard(text):
    """Copy text to the clipboard with the first system tool that works.

    Returns ``(True, None)`` on success, otherwise ``(False, error_message)``.
    """
    failures = []
    for cmd, encoding in _clipboard_commands():
        try:
            # The tools fork a background process that keeps serving the selection:
            # it must not inherit our stdout/stderr, or a pipe reading our output would hang.
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            continue  # not installed or not executable
        try:
            p.communicate(input=text.encode(encoding), timeout=CLIPBOARD_TIMEOUT)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            failures.append(f"{cmd[0]} (timed out)")
            continue
        if p.returncode == 0:
            return True, None
        failures.append(f"{cmd[0]} (exit code {p.returncode})")

    if failures:
        return False, "clipboard tool failed: " + ", ".join(failures)
    return False, "no clipboard tool found (install wl-clipboard, xclip or xsel; pbcopy/clip.exe on macOS/Windows)"


def _positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {number}")
    return number


def build_argument_parser(version):
    """Builds and returns the ArgumentParser for depicts CLI."""
    parser = argparse.ArgumentParser(
        prog='depicts',
        description="Summarize a software project for AI context.\n"
                    "Run without arguments to get an instant summary of the current directory.",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False
    )

    options = parser.add_argument_group('options')
    options.add_argument('-h', '--help', action='help', help='Show this help message and exit')
    options.add_argument('--version', action='version', version=f'depicts {version}',
                         help='Show the version number and exit')

    targeting = parser.add_argument_group('targeting')
    targeting.add_argument('--path', metavar='PATH', default='.',
                           help='Path to the project root (default: current directory)')
    targeting.add_argument('--file', metavar='GLOB', action='append', default=[],
                           help='Force include a file or glob pattern, relative to the project root\n'
                                '(can be repeated; use **/ to match at any depth, e.g. "**/*.sql")')

    output = parser.add_argument_group('output')
    output.add_argument('--output', metavar='FILE', help='Write output to a file instead of stdout')
    output.add_argument('--format', choices=list(FORMATTERS), default='plain',
                        help='Output format: plain text with ASCII separators (default),\n'
                             'Markdown with fenced code blocks, or JSON')
    output.add_argument('--clipboard', action='store_true',
                        help='Copy output to the clipboard instead of printing it to stdout\n'
                             '(can be combined with --output)')

    verbosity = parser.add_argument_group('verbosity')
    amount = verbosity.add_mutually_exclusive_group()
    amount.add_argument('--short', '--no-content', dest='short', action='store_true',
                        help='Show only stack detection and directory tree, no file contents')
    amount.add_argument('--full', action='store_true',
                        help='Show full content of all priority files without truncation')
    verbosity.add_argument('--lines', metavar='N', type=_positive_int,
                           help=f'Max lines to show per file (default: {DEFAULT_MAX_LINES}; files up to 200\n'
                                'lines are shown in full unless this is set). Overrides config')

    filtering = parser.add_argument_group('filtering')
    filtering.add_argument('--exclude', metavar='PATTERN', action='append', default=[],
                           help='Exclude a directory, file or glob pattern (can be repeated, e.g.\n'
                                '--exclude logs --exclude src/tests --exclude "*.log")')
    filtering.add_argument('--depth', metavar='N', type=_positive_int, default=3,
                           help='Max directory tree depth (default: 3)')

    return parser


def render(report, fmt):
    """Format the report, including the size of the output itself in the summary."""
    formatter = FORMATTERS[fmt]
    if report.summary is None:
        return formatter(report)
    report.summary.output_size = _SIZE_PLACEHOLDER
    text = formatter(report)
    without_size = text.replace(_SIZE_PLACEHOLDER, "", 1)
    # ~4 characters per token is the usual rough estimate for English text and code.
    size = f"~{len(without_size) // 4:,} tokens ({len(without_size.encode('utf-8')) / 1024:.1f} KB)"
    report.summary.output_size = size
    return text.replace(_SIZE_PLACEHOLDER, size, 1)


def run_pipeline(parsed_args):
    """Orchestrates the whole process: config -> detect -> scan -> select -> read -> format -> output."""
    root_path = os.path.abspath(parsed_args.path)
    if not os.path.isdir(root_path):
        print(f"Error: Path '{root_path}' is not a directory.", file=sys.stderr)
        return 1

    try:
        config = load_config(
            root_path=root_path,
            cli_excludes=parsed_args.exclude,
            cli_lines=parsed_args.lines,
            cli_force_includes=parsed_args.file
        )
        stack_name, priority_patterns = detect_stack(root_path)
        scan = scan_project(root_path, config.excludes, max_depth=parsed_args.depth)
        tree = scan.tree or ["  (empty directory)"]

        summary = None
        files = []
        if not parsed_args.short:
            summary = build_summary(scan.files)
            refs = resolve_files(root_path, scan.files, priority_patterns, config.extra_files, config.cli_files)
            files = [
                read_file(root_path, ref, config.max_lines, config.truncate_threshold, parsed_args.full)
                for ref in refs
            ]

        output_text = render(Report(stack_name, tree, summary, files), parsed_args.format)
    except PermissionError as e:
        print(f"\n[Permission Error] Could not access files: {e}", file=sys.stderr)
        print("Note: If you are running this from a Snap package, it cannot access hidden folders "
              "(like ~/.gemini or ~/.ssh) due to strict security confinement.", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    status = 0
    if parsed_args.output:
        try:
            with open(parsed_args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"Output written to {parsed_args.output}", file=sys.stderr)
        except OSError as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            status = 1
    if parsed_args.clipboard:
        copied, error = copy_to_clipboard(output_text)
        if copied:
            print("Output copied to clipboard.", file=sys.stderr)
        else:
            print(f"Error: could not copy to clipboard: {error}", file=sys.stderr)
            status = 1
    if not parsed_args.output and not parsed_args.clipboard:
        print(output_text)
    return status


def main(argv=None):
    from . import __version__
    parser = build_argument_parser(__version__)
    parsed_args = parser.parse_args(argv)
    try:
        status = run_pipeline(parsed_args)
        sys.stdout.flush()
    except BrokenPipeError:
        # The reader went away (e.g. `depicts | head`). Point stdout at devnull so
        # the interpreter's final flush does not raise again, and exit quietly.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        status = 1
    except KeyboardInterrupt:
        status = 130
    sys.exit(status)


if __name__ == '__main__':
    main()
