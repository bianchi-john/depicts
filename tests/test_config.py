from depicts.config import DEFAULT_FULL_FILE_THRESHOLD, DEFAULT_MAX_LINES, load_config


def test_defaults(tmp_path):
    config = load_config(tmp_path)
    assert '.git' in config.excludes
    assert config.max_lines == DEFAULT_MAX_LINES
    assert not config.max_lines_explicit
    assert config.truncate_threshold == DEFAULT_FULL_FILE_THRESHOLD


def test_yaml_values_are_merged_and_cli_wins(make_files):
    root = make_files({".depicts.yml": "exclude_dirs: [logs]\nmax_lines: 40\nextra_files: [docs/a.md]\n"})
    config = load_config(root, cli_excludes=["tmp"], cli_lines=7, cli_force_includes=["x.py"])
    assert {"logs", "tmp"} <= set(config.excludes)
    assert config.max_lines == 7 and config.max_lines_explicit
    assert config.truncate_threshold == 7
    assert config.extra_files == ["docs/a.md"]
    assert config.cli_files == ["x.py"]


def test_explicit_limit_from_yaml_is_a_hard_limit(make_files):
    config = load_config(make_files({".depicts.yml": "max_lines: 5\n"}))
    assert config.max_lines_explicit
    assert config.truncate_threshold == 5


def test_string_instead_of_list_is_accepted(make_files):
    # Regression: 'exclude_dirs: logs' used to add the characters l, o, g, s as excludes.
    config = load_config(make_files({".depicts.yml": "exclude_dirs: logs\nextra_files: docs/x.md\n"}))
    assert "logs" in config.excludes
    assert "s" not in config.excludes
    assert config.extra_files == ["docs/x.md"]


def test_invalid_max_lines_warns_and_uses_default(make_files, capsys):
    for bad in ("abc", "0", "-3", "true"):
        config = load_config(make_files({".depicts.yml": f"max_lines: {bad}\n"}))
        assert config.max_lines == DEFAULT_MAX_LINES
        assert not config.max_lines_explicit
        assert "max_lines" in capsys.readouterr().err


def test_non_mapping_yaml_is_ignored_with_warning(make_files, capsys):
    config = load_config(make_files({".depicts.yml": "- a\n- b\n"}))
    assert config.extra_files == []
    assert "must contain a mapping" in capsys.readouterr().err


def test_unknown_key_warns(make_files, capsys):
    load_config(make_files({".depicts.yml": "max_line: 10\n"}))
    assert "unknown setting 'max_line'" in capsys.readouterr().err


def test_wrong_list_type_is_ignored_with_warning(make_files, capsys):
    config = load_config(make_files({".depicts.yml": "extra_files: {a: 1}\n"}))
    assert config.extra_files == []
    assert "extra_files" in capsys.readouterr().err


def test_broken_yaml_warns(make_files, capsys):
    config = load_config(make_files({".depicts.yml": "max_lines: [\n"}))
    assert config.max_lines == DEFAULT_MAX_LINES
    assert "could not parse" in capsys.readouterr().err
