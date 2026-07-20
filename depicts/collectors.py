"""
File collection and summary generation.
"""
import os
import glob
import fnmatch
from collections import defaultdict

def matches_gitignore(rel_path, gitignore_rules, is_dir):
    """
    Check if rel_path (relative to root) matches any rule in gitignore_rules.
    gitignore_rules is a list of tuples: (pattern, is_dir_only, is_anchored)
    """
    if not gitignore_rules:
        return False
        
    for pattern, is_dir_only, is_anchored in gitignore_rules:
        if is_dir_only and not is_dir:
            continue
            
        # Match anchored patterns (must match from the start of rel_path)
        if is_anchored:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, pattern + '/*'):
                return True
        else:
            # Unanchored patterns match any path segment or suffix
            parts = rel_path.split('/')
            for i in range(len(parts)):
                subpath = '/'.join(parts[i:])
                if fnmatch.fnmatch(subpath, pattern) or fnmatch.fnmatch(subpath, pattern + '/*'):
                    return True
                if fnmatch.fnmatch(parts[i], pattern):
                    return True
    return False

def is_excluded(rel_path, excludes, gitignore_rules=None, is_dir=False):
    """Check if a file or directory should be excluded, supporting path-based patterns and gitignore."""
    parts = rel_path.split('/')
    
    # Name-based exclusion (e.g. if any segment matches excludes, like 'node_modules')
    for part in parts:
        if part in excludes:
            return True
        if part.endswith('.egg-info'):
            return True
        
    # Path-based exclusion (e.g. 'src/tests')
    for ex in excludes:
        if '/' in ex:
            if rel_path == ex or rel_path.startswith(ex + '/'):
                return True
            
    # Gitignore matching
    if gitignore_rules and matches_gitignore(rel_path, gitignore_rules, is_dir):
        return True
            
    return False

def build_tree_and_files(root, excludes, max_depth=3, current_depth=1, current_relpath="", gitignore_rules=None):
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
        
    # Filter out excluded entries first to know which one is the last
    valid_entries = []
    for entry in entries:
        rel_path = os.path.join(current_relpath, entry).replace('\\', '/')
        is_dir = os.path.isdir(os.path.join(root, entry))
        if not is_excluded(rel_path, excludes, gitignore_rules, is_dir):
            valid_entries.append((entry, rel_path, is_dir))
            
    for i, (entry, rel_path, is_dir) in enumerate(valid_entries):
        full_path = os.path.join(root, entry)
        
        is_last = (i == len(valid_entries) - 1)
        prefix_connector = "└── " if is_last else "├── "
        
        prefix = "    " * (current_depth - 1) + prefix_connector
        
        if is_dir:
            tree_lines.append(f"{prefix}{entry}/")
            sub_lines, sub_files = build_tree_and_files(
                full_path, excludes, max_depth, current_depth + 1, rel_path, gitignore_rules
            )
            tree_lines.extend(sub_lines)
            all_files.extend(sub_files)
        else:
            tree_lines.append(f"{prefix}{entry}")
            all_files.append(rel_path)
            
    return tree_lines, all_files

def get_all_non_excluded_files(root, excludes, gitignore_rules=None):
    """
    Recursively find all files under root, skipping excluded directories.
    Returns relative paths.
    """
    all_files = []
    
    def _walk(current_dir, current_relpath):
        try:
            entries = os.listdir(current_dir)
        except PermissionError:
            return
            
        for entry in entries:
            rel_path = os.path.join(current_relpath, entry).replace('\\', '/')
            full_path = os.path.join(current_dir, entry)
            is_dir = os.path.isdir(full_path)
            
            if is_excluded(rel_path, excludes, gitignore_rules, is_dir):
                continue
                
            if is_dir:
                _walk(full_path, rel_path)
            else:
                all_files.append(rel_path)
                
    _walk(root, "")
    return all_files

def resolve_priority_files(root, priority_patterns, force_includes, excludes, gitignore_rules=None):
    """
    Resolve priority files by matching patterns against non-excluded files.
    """
    resolved_files = set()
    patterns_to_check = priority_patterns + force_includes
    
    if not patterns_to_check:
        return []
        
    all_non_excluded = get_all_non_excluded_files(root, excludes, gitignore_rules)
    
    for pattern in patterns_to_check:
        # Standardize pattern path separators
        pattern = pattern.replace('\\', '/')
        
        for rel_path in all_non_excluded:
            if fnmatch.fnmatch(rel_path, pattern):
                resolved_files.add(rel_path)
            elif fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                # Allow matching by base name if pattern has no slashes, e.g. "*.py"
                if '/' not in pattern:
                    resolved_files.add(rel_path)
                    
    # Also handle literal files that might be outside excludes but forced
    for pattern in force_includes:
        pattern = pattern.replace('\\', '/')
        full_path = os.path.join(root, pattern)
        if os.path.isfile(full_path):
            rel_path = os.path.relpath(full_path, root).replace('\\', '/')
            resolved_files.add(rel_path)
            
    return sorted(list(resolved_files))

def read_file_content(root, filepath, max_lines, full_mode):
    """
    Read the content of a file, respecting truncation rules, and protecting against OOM.
    """
    full_path = os.path.join(root, filepath)
    
    # Simple binary check based on extensions
    binary_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz', '.pyc', '.so', '.dll', '.exe', '.bin', '.snap'}
    ext = os.path.splitext(filepath)[1].lower()
    if ext in binary_exts:
        return "<binary file, skipped>"
        
    try:
        # Protect against opening huge files
        file_size = os.path.getsize(full_path)
        if file_size > 10 * 1024 * 1024:  # 10 MB limit
            return "<file too large, skipped (>10MB)>"

        # Also try to detect binary by reading a chunk and checking for null bytes
        with open(full_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return "<binary file, skipped>"
                
        is_readme = os.path.basename(filepath).lower().startswith('readme')
        
        lines = []
        is_truncated = False
        
        limit = None
        if not full_mode and not is_readme:
            limit = max(201, max_lines + 1)
            
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                lines.append(line)
                if limit and len(lines) >= limit:
                    is_truncated = True
                    break
                    
        if is_truncated and len(lines) > max_lines:
            lines = lines[:max_lines]
            content = "".join(lines)
            content += f"\n... (truncated to {max_lines} lines) ...\n"
        else:
            content = "".join(lines)
            
        return content
    except UnicodeDecodeError:
        return "<binary file, skipped (UnicodeDecodeError)>"
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
