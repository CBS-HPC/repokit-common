import repokit_common.secretstore as secretstore
import repokit_common.tomlutils as tomlutils


def test_save_to_env_updates_bom_pyproject(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\ufeff[project]\nname = \"smoke\"\n\n[tool.cookiecutter]\nrepo_name = \"smoke\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)

    secretstore.save_to_env("Py310 Smoke", "PROJECT_NAME", ".cookiecutter", str(pyproject))

    config = tomlutils.read_toml(folder=str(tmp_path), tool_name="cookiecutter")
    assert config["PROJECT_NAME"] == "Py310 Smoke"


def test_read_toml_accepts_utf8_bom(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\ufeff[project]\nname = \"smoke\"\n\n[tool.datasets]\npatterns = \"data/*\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tomlutils, "PROJECT_ROOT", tmp_path)

    config = tomlutils.read_toml(folder=str(tmp_path), tool_name="datasets")
    assert config["patterns"] == "data/*"
