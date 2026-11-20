"""
JSON output formatter for depicts.
"""
import json
from dataclasses import asdict


def format_json(report):
    """Format output as structured JSON.

    Each file is an object with ``path``, ``content`` (null when skipped),
    ``truncated``, ``shown_lines``, ``total_lines`` and ``skipped`` (the
    reason the content was left out, or null).
    """
    data = {
        'stack': report.stack,
        'summary': asdict(report.summary) if report.summary else None,
        'tree': report.tree,
        'files': [asdict(entry) for entry in report.files],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
