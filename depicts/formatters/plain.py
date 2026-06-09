def format_plain(stack, summary, tree, files_content):
    lines = []
    lines.append("════════════════════════════════")
    lines.append(f" STACK: {stack}")
    lines.append("════════════════════════════════")
    
    if summary:
        lines.append("[SUMMARY]")
        lines.append(f"Entry points : {summary['entry_points']}")
        lines.append(f"Source files : {summary['source_files']}")
        lines.append(f"Config files : {summary['config_files']}")
        lines.append("════════════════════════════════")
        
    lines.append("[DIRECTORY TREE]")
    lines.extend(tree)
    lines.append("")
    
    for filepath, content in files_content:
        lines.append(f"════════════════════════════════")
        lines.append(f"[FILE: {filepath}]")
        lines.append(f"════════════════════════════════")
        lines.append(content)
        lines.append("")
        
    return "\n".join(lines)
