"""
JSON output formatter for depicts.
"""
import json


def format_json(stack, summary, tree, files_content):
    """Format output as structured JSON."""
    data = {
        'stack': stack,
        'summary': summary,
        'tree': tree,
        'files': {filepath: content for filepath, content in files_content}
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
