import json

import repokit_common.tomlutils as tomlutils


def test_toml_ignore_prefers_ignore_file(tmp_path):
    (tmp_path / ".ignore").write_text("# comment\n*.tmp\nbuild/\n", encoding="utf-8")

    spec, patterns = tomlutils.toml_ignore(folder=str(tmp_path), ignore_filename=".ignore")

    assert patterns == ["*.tmp", "build/"]
    assert spec.match_file("notes.tmp")
    assert spec.match_file("build/output.txt")


def test_toml_ignore_reads_tool_section(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.treeignore]\npatterns = ['.venv/', 'build/']\n", encoding="utf-8"
    )

    spec, patterns = tomlutils.toml_ignore(folder=str(tmp_path), tool_name="treeignore")

    assert patterns == [".venv/", "build/"]
    assert spec.match_file("build/output.txt")


def test_read_toml_prefers_json_fallback(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"source": "json"}), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.settings]\nsource = 'toml'\n", encoding="utf-8")

    result = tomlutils.read_toml(
        folder=str(tmp_path), json_filename="settings.json", tool_name="settings"
    )

    assert result == {"source": "json"}


def test_write_toml_preserves_comments(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "# keep\n[tool.datasets]\n# paths\npatterns = ['old/*']\n", encoding="utf-8"
    )

    tomlutils.write_toml(
        data={"patterns": ["data/*"]},
        folder=str(tmp_path),
        tool_name="datasets",
    )

    text = pyproject.read_text(encoding="utf-8")
    assert "# keep" in text
    assert "# paths" in text
    assert tomlutils.read_toml(folder=str(tmp_path), tool_name="datasets") == {
        "patterns": ["data/*"]
    }


def test_dataset_path_normalizes_and_persists_config(tmp_path, monkeypatch):
    monkeypatch.setattr(tomlutils, "PROJECT_ROOT", tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.datasets]\npatterns = ['./inputs/*']\n", encoding="utf-8"
    )

    config, pattern = tomlutils.toml_dataset_path()

    assert pattern == "./inputs/*"
    assert config == {"parent_path": tomlutils.Path("inputs"), "sub_dir": True}


def test_dataset_path_explicit_value_overrides_config(tmp_path, monkeypatch):
    monkeypatch.setattr(tomlutils, "PROJECT_ROOT", tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.datasets]\npatterns = 'old/*'\n", encoding="utf-8"
    )

    config, pattern = tomlutils.toml_dataset_path("data/")

    assert pattern == "data/"
    assert config == {"parent_path": tomlutils.Path("data"), "sub_dir": False}
