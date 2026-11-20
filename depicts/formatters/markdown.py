import os
import re

_BACKTICK_RUN = re.compile(r"`{3,}")
_LANGUAGE_BY_NAME = {'dockerfile': 'dockerfile', 'makefile': 'makefile'}


def fence_for(text):
    """A backtick fence longer than any backtick run inside ``text``.

    Without this, the first ``` in a file (e.g. a code block in a README)
    would close the surrounding block and break the rest of the document.
    """
    longest = max((len(m) for m in _BACKTICK_RUN.findall(text)), default=0)
    return "`" * max(3, longest + 1)


def _language(path):
    name = os.path.basename(path).lower()
    for prefix, language in _LANGUAGE_BY_NAME.items():
        if name.startswith(prefix):
            return language
    return os.path.splitext(name)[1][1:]


def format_md(report):
    lines = ["# Project Summary", f"**STACK:** {report.stack}", ""]

    if report.summary:
        lines.append("## Summary")
        lines.extend(f"- **{label}:** {value}" for label, value in report.summary.rows())
        lines.append("")

    tree = "\n".join(report.tree)
    fence = fence_for(tree)
    lines += ["## Directory Tree", fence, tree, fence, ""]

    for entry in report.files:
        body = entry.body()
        fence = fence_for(body)
        lines += [f"## File: `{entry.path}`", f"{fence}{_language(entry.path)}", body, fence, ""]

    return "\n".join(lines)
