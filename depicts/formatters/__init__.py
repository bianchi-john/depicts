"""
Registry for output formatters.
"""
from .json_out import format_json
from .markdown import format_md
from .plain import format_plain

FORMATTERS = {
    'plain': format_plain,
    'md': format_md,
    'json': format_json
}
