import pathlib
import sys

import repokit_common
import repokit_common.base as base
import repokit_common.env as env


def test_public_api_has_release_version_and_no_private_helpers():
    assert repokit_common.__version__ == "0.1.0"
    assert "run_command" in repokit_common.__all__
    assert "_run" not in repokit_common.__all__
    assert "_keyring_get" not in repokit_common.__all__


def test_find_project_root_uses_parent_marker(tmp_path, monkeypatch):
    root = tmp_path / "project"
    nested = root / "src" / "module"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    monkeypatch.chdir(nested)

    assert base._find_project_root_from_cwd() == root
    assert base.project_root() == root


def test_find_project_root_supports_extra_markers(tmp_path, monkeypatch):
    root = tmp_path / "project"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "custom.marker").write_text("", encoding="utf-8")
    monkeypatch.chdir(nested)

    assert base._find_project_root_from_cwd(["custom.marker"]) == root


def test_install_base_deps_falls_back_to_pip(monkeypatch):
    commands = []
    monkeypatch.setattr(base, "install_uv", lambda: False)
    monkeypatch.setattr(base.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    base.install_base_deps(["example-package"])

    assert commands == [[sys.executable, "-m", "pip", "install", "example-package"]]


def test_set_packages_selects_language_and_dvc_dependency(monkeypatch):
    monkeypatch.setattr(env, "is_installed", lambda *args: False)

    assert env.set_packages("dvc", "python") == ["jupyterlab", "pytest", "dvc"]
    assert env.set_packages("none", "r") == []
    assert env.set_packages(None, "python") == []


def test_write_uv_requires_preserves_comments(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "# keep\n[project]\nname = 'demo'\nrequires-python = '>=3.10'\n", encoding="utf-8"
    )
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env.subprocess, "check_output", lambda *args, **kwargs: b"Python 3.12.1\n")

    env.write_uv_requires()

    text = pyproject.read_text(encoding="utf-8")
    assert "# keep" in text
    assert 'requires-python = ">= 3.12.1"' in text


def test_run_script_and_run_command(tmp_path):
    assert env.run_script("python", "print('ok')") == "ok"

    result = env.run_command(
        [sys.executable, "-c", "print('command-ok')"],
        pathlib.Path(tmp_path),
        capture=True,
    )

    assert result.stdout.strip() == "command-ok"


def test_run_script_returns_command_error():
    result = env.run_script("python", "import sys; sys.exit(4)")

    assert result.startswith("Error running script:")


def test_ensure_correct_kernel_runs_wrapped_function(monkeypatch):
    monkeypatch.setattr(env, "load_from_env", lambda _: None)

    @env.ensure_correct_kernel
    def value():
        return "ok"

    assert value() == "ok"
