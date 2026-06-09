import os

def format_md(stack, summary, tree, files_content):
    lines = []
    lines.append(f"# Project Summary")
    lines.append(f"**STACK:** {stack}\n")
    
    if summary:
        lines.append("## Summary")
        lines.append(f"- **Entry points:** {summary['entry_points']}")
        lines.append(f"- **Source files:** {summary['source_files']}")
        lines.append(f"- **Config files:** {summary['config_files']}\n")
        
    lines.append("## Directory Tree")
    lines.append("```")
    lines.extend(tree)
    lines.append("```\n")
    
    for filepath, content in files_content:
        lines.append(f"## File: `{filepath}`")
        ext = os.path.splitext(filepath)[1][1:] # get extension without dot
        lines.append(f"```{ext}")
        lines.append(content.strip())
        lines.append("\n```\n")
        
    return "\n".join(lines)
