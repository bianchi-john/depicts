#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

from .config import load_config
from .detectors import detect_stack
from .collectors import (
    build_tree_and_files, 
    resolve_priority_files, 
    read_file_content, 
    generate_summary
)
from .formatters import FORMATTERS

def copy_to_clipboard(text):
    """Attempt to copy text to clipboard using system utilities."""
    # macOS
    try:
        p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p.communicate(input=text.encode('utf-8'))
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    # Windows / WSL
    try:
        p = subprocess.Popen(['clip.exe'], stdin=subprocess.PIPE)
        # Windows clip.exe often prefers utf-16le or local codepage, but utf-8 mostly works in modern WSL
        p.communicate(input=text.encode('utf-8'))
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    # Linux - xclip
    try:
        p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
        p.communicate(input=text.encode('utf-8'))
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass
        
    # Linux - xsel
    try:
        p = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE)
        p.communicate(input=text.encode('utf-8'))
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass
        
    return False

def main():
    from . import __version__
    parser = argparse.ArgumentParser(
        description="Summarize a software project for AI context.\nRun without arguments to get an instant summary of the current directory.",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False
    )
    
    options = parser.add_argument_group('options')
    options.add_argument('-h', '--help', action='help', help='Show this help message and exit')
    options.add_argument('--version', action='version', version=f'depicts {__version__}')
    
    targeting = parser.add_argument_group('targeting')
    targeting.add_argument('--path', metavar='PATH', default='.', help='Path to the project root (default: current directory)')
    targeting.add_argument('--file', metavar='GLOB', action='append', default=[], help='Force include a specific file or glob pattern in the output')
    
    output = parser.add_argument_group('output')
    output.add_argument('--output', metavar='FILE', help='Write output to a file instead of stdout')
    output.add_argument('--format', choices=['plain', 'md', 'json'], default='plain', help='Output format: plain text with ASCII separators (default)\nor Markdown with fenced code blocks or JSON')
    output.add_argument('--clipboard', action='store_true', help='Copy output to clipboard instead of printing to stdout')
    
    verbosity = parser.add_argument_group('verbosity')
    verbosity.add_argument('--short', action='store_true', help='Show only stack detection and directory tree, no file contents')
    verbosity.add_argument('--full', action='store_true', help='Show full content of all priority files without truncation')
    verbosity.add_argument('--lines', metavar='N', type=int, help='Max lines to show per file (default: 150, overrides config)')
    verbosity.add_argument('--no-content', action='store_true', help='Alias for --short')
    
    filtering = parser.add_argument_group('filtering')
    filtering.add_argument('--exclude', metavar='DIR', action='append', default=[], help='Exclude an additional directory or path (can be repeated, e.g.\n--exclude logs --exclude src/tests)')
    filtering.add_argument('--depth', metavar='N', type=int, default=3, help='Max directory tree depth (default: 3)')

    
    parsed_args = parser.parse_args()
    
    root_path = os.path.abspath(parsed_args.path)
    if not os.path.isdir(root_path):
        print(f"Error: Path '{root_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
        
    try:
        # 1. Config Loading
        config = load_config(
            root_path=root_path,
            cli_excludes=parsed_args.exclude,
            cli_lines=parsed_args.lines,
            cli_force_includes=parsed_args.file
        )
        
        short_mode = parsed_args.short or parsed_args.no_content
        full_mode = parsed_args.full
        
        # 2. Detect Stack
        stack_name, priority_patterns = detect_stack(root_path)
        
        # 3. Collect Directory Tree
        tree_lines, all_files = build_tree_and_files(root_path, config['excludes'], max_depth=parsed_args.depth)
        if not tree_lines:
            tree_lines = ["  (empty or inaccessible directory)"]
            
        # 4. Resolve Priority Files
        resolved_files = resolve_priority_files(root_path, priority_patterns, config['force_includes'])
        
        # 5. Generate Summary
        summary = generate_summary(all_files, resolved_files)
            
        # 6. Collect File Contents
        files_content = []
        if not short_mode:
            for filepath in resolved_files:
                content = read_file_content(root_path, filepath, config['max_lines'], full_mode)
                files_content.append((filepath, content))
                
        # 7. Format Output
        formatter = FORMATTERS.get(parsed_args.format) or FORMATTERS['plain']
        output_summary = None if short_mode else summary
        output_text = formatter(stack_name, output_summary, tree_lines, files_content)
        
        if output_summary and not short_mode:
            size_bytes = len(output_text.encode('utf-8'))
            tokens = size_bytes // 4
            kb = size_bytes / 1024
            # We add it to the summary struct for formatters to use
            summary['output_size'] = f"~{tokens:,} tokens ({kb:.1f} KB)"
            # Re-format since we just added size
            output_text = formatter(stack_name, output_summary, tree_lines, files_content)
        
        # 8. Route Output
        if parsed_args.clipboard:
            success = copy_to_clipboard(output_text)
            if success:
                print("Output copied to clipboard.")
            else:
                print("Error: Could not copy to clipboard. Neither xclip nor xsel was found.", file=sys.stderr)
                sys.exit(1)
        elif parsed_args.output:
            try:
                with open(parsed_args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"Output written to {parsed_args.output}")
            except Exception as e:
                print(f"Error writing to file: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_text)

    except PermissionError as e:
        print(f"\n[Permission Error] Could not access files: {e}", file=sys.stderr)
        print("Note: If you are running this from a Snap package, it cannot access hidden folders (like ~/.gemini or ~/.ssh) due to strict security confinement.", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
