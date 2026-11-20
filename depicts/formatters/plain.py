SEPARATOR = "═" * 32


def format_plain(report):
    lines = [SEPARATOR, f" STACK: {report.stack}", SEPARATOR]

    if report.summary:
        lines.append("[SUMMARY]")
        lines.extend(f"{label:<12} : {value}" for label, value in report.summary.rows())
        lines.append(SEPARATOR)

    lines.append("[DIRECTORY TREE]")
    lines.extend(report.tree)
    lines.append("")

    for entry in report.files:
        lines += [SEPARATOR, f"[FILE: {entry.path}]", SEPARATOR, entry.body(), ""]

    return "\n".join(lines)
