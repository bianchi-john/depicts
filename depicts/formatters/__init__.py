"""
Registry for output formatters.
"""
from .plain import format_plain
from .markdown import format_md

FORMATTERS = {
    'plain': format_plain,
    'md': format_md
}
