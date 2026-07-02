"""
Registry for output formatters.
"""
from .plain import format_plain
from .markdown import format_md
from .json_out import format_json

FORMATTERS = {
    'plain': format_plain,
    'md': format_md,
    'json': format_json
}
