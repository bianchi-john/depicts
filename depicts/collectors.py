"""
File collection and summary generation.
"""
import os
import glob
from collections import defaultdict

def is_excluded(name, excludes):
    """Check if a file or directory should be excluded."""
    if name in excludes:
        return True
    if name.endswith('.egg-info'):
        return True
    return False

def build_tree_and_files(root, excludes, max_depth=3, current_depth=1, current_relpath=""):
    """
    Traverse the directory tree up to max_depth.
    Returns (tree_lines, list_of_all_relative_file_paths_found).
    """
    if current_depth > max_depth:
        return [], []
    
    tree_lines = []
    all_files = []
    try:
        entries = sorted(os.listdir(root))
    except PermissionError:
        return [], []
        
    for entry in entries:
        if is_excluded(entry, excludes):
            continue
            
        full_path = os.path.join(root, entry)
        rel_path = os.path.join(current_relpath, entry).replace('\\', '/')
        prefix = "  " * (current_depth - 1) + "├── "
        
        if os.path.isdir(full_path):
            tree_lines.append(f"{prefix}{entry}/")
            sub_lines, sub_files = build_tree_and_files(full_path, excludes, max_depth, current_depth + 1, rel_path)
            tree_lines.extend(sub_lines)
            all_files.extend(sub_files)
        else:
            tree_lines.append(f"{prefix}{entry}")
            all_files.append(rel_path)
            
    return tree_lines, all_files

def resolve_priority_files(root, priority_patterns, force_includes):
    """
    Expand glob patterns and check file existence for priority lists.
    Returns a sorted list of relative file paths.
    """
    resolved_files = set()
    patterns_to_check = priority_patterns + force_includes
    
    for pattern in patterns_to_check:
        full_pattern = os.path.join(root, pattern)
        for match in glob.glob(full_pattern, recursive=True):
            if os.path.isfile(match):
                resolved_files.add(os.path.relpath(match, root).replace('\\', '/'))
                
    return sorted(list(resolved_files))

def read_file_content(root, filepath, max_lines, full_mode):
    """
    Read the content of a file, respecting truncation rules.
    """
    full_path = os.path.join(root, filepath)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        is_truncated = False
        is_readme = os.path.basename(filepath).lower().startswith('readme')
        
        if not full_mode and not is_readme:
            # Show full if under 200 lines, otherwise truncate to max_lines
            if len(lines) > 200 and len(lines) > max_lines:
                lines = lines[:max_lines]
                is_truncated = True
                
        content = "".join(lines)
        if is_truncated:
            content += f"\n... (truncated to {max_lines} lines) ...\n"
        return content
    except Exception as e:
        return f"<Error reading file: {e}>"

def generate_summary(all_files, resolved_files):
    """
    Generates summary statistics: Entry points, Source files, Config files.
    """
    entry_patterns = {'main.py', 'app.py', 'wsgi.py', 'manage.py', 'index.js', 'index.ts', 'main.rs', 'main.go'}
    config_patterns = {'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json', 'Cargo.toml', 'go.mod', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'}
    
    check_files = set(all_files).union(resolved_files)
    
    entry_points = sorted([f for f in check_files if any(f.endswith(p) or f.endswith("/" + p) for p in entry_patterns)])
    config_files = sorted([f for f in check_files if any(f == p or f.endswith("/" + p) for p in config_patterns)])
    
    source_exts = {'.py', '.js', '.ts', '.rs', '.go', '.java', '.cpp', '.c', '.h', '.rb', '.php'}
    source_files_by_ext = defaultdict(int)
    for f in all_files:
        ext = os.path.splitext(f)[1]
        if ext in source_exts:
            source_files_by_ext[ext] += 1
            
    source_str = ", ".join(f"{count} {ext} files" for ext, count in source_files_by_ext.items())
    if not source_str:
        source_str = "None detected"
        
    return {
        'entry_points': ", ".join(entry_points) if entry_points else "None detected",
        'source_files': source_str,
        'config_files': ", ".join(config_files) if config_files else "None detected"
    }
