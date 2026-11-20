from depicts.collectors import build_summary
from depicts.models import SUMMARY_LIST_LIMIT, Summary


def test_entry_points_match_whole_file_names_only():
    # Regression: domain.py, webapp.py and reindex.js were reported as entry points.
    summary = build_summary(["src/domain.py", "lib/webapp.py", "reindex.js", "main.py", "pkg/__main__.py"])
    assert summary.entry_points == ["main.py", "pkg/__main__.py"]


def test_deeply_nested_entry_points_and_configs_are_not_listed():
    files = ["src/index.js", "src/components/Button/index.js", "package.json", "packages/a/lib/package.json"]
    summary = build_summary(files)
    assert summary.entry_points == ["src/index.js"]
    assert summary.config_files == ["package.json"]


def test_source_counts_sorted_by_frequency():
    summary = build_summary(["a.py", "b.py", "c.ts", "d.tsx", "e.tsx", "f.tsx", "notes.txt"])
    assert summary.source_files == {".tsx": 3, ".py": 2, ".ts": 1}
    assert dict(summary.rows())["Source files"] == "3 .tsx files, 2 .py files, 1 .ts file"


def test_empty_summary_rows():
    rows = dict(Summary().rows())
    assert rows == {"Entry points": "None detected", "Source files": "None detected",
                    "Config files": "None detected"}


def test_long_lists_are_collapsed_in_text():
    summary = Summary(entry_points=[f"e{i}/main.py" for i in range(SUMMARY_LIST_LIMIT + 3)])
    assert dict(summary.rows())["Entry points"].endswith("(+3 more)")
