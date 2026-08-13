import builtins
import os
import pathlib
import sys
from types import SimpleNamespace

import pytest

import repokit_common.base as base
import repokit_common.env as env
import repokit_common.env_paths as env_paths
import repokit_common.secretstore as secretstore
import repokit_common.toml_compat as toml_compat
import repokit_common.tomlutils as tomlutils


def test_install_uv_returns_true_when_import_available():
    assert base.install_uv() is True


def test_install_uv_installs_when_import_becomes_available(monkeypatch):
    original_import = builtins.__import__
    attempts = {"uv": 0}
    commands = []

    def import_uv_once_missing(name, *args, **kwargs):
        if name == "uv":
            attempts["uv"] += 1
            if attempts["uv"] == 1:
                raise ImportError
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_uv_once_missing)
    monkeypatch.setattr(base.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    assert base.install_uv() is True
    assert commands == [[sys.executable, "-m", "pip", "install", "--upgrade", "uv"]]


def test_install_uv_returns_false_when_import_still_fails(monkeypatch):
    original_import = builtins.__import__

    def no_uv(name, *args, **kwargs):
        if name == "uv":
            raise ImportError("uv unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_uv)
    monkeypatch.setattr(base.subprocess, "run", lambda *args, **kwargs: None)

    assert base.install_uv() is False


def test_install_base_deps_uses_uv_then_falls_back_to_pip(monkeypatch):
    commands = []
    monkeypatch.setattr(base, "install_uv", lambda: True)
    monkeypatch.setattr(base.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    base.install_base_deps(["one"])
    assert commands[0] == [sys.executable, "-m", "uv", "pip", "install", "--system", "one"]

    commands.clear()
    monkeypatch.setattr(base, "install_uv", lambda: False)
    base.install_base_deps(["two"])
    assert commands == [[sys.executable, "-m", "pip", "install", "two"]]


def test_install_base_deps_falls_back_after_uv_failure(monkeypatch):
    commands = []
    monkeypatch.setattr(base, "install_uv", lambda: True)

    def run(command, **kwargs):
        commands.append(command)
        if "uv" in command:
            raise RuntimeError("uv unavailable")

    monkeypatch.setattr(base.subprocess, "run", run)

    base.install_base_deps(["one"])

    assert commands == [
        [sys.executable, "-m", "uv", "pip", "install", "--system", "one"],
        [sys.executable, "-m", "pip", "install", "one"],
    ]


def test_env_create_uv_project_handles_existing_and_new_projects(tmp_path, monkeypatch):
    commands = []
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env, "install_uv", lambda: True)
    monkeypatch.setattr(env.subprocess, "run", lambda cmd, **kwargs: commands.append((cmd, kwargs)))

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    env.create_uv_project()
    assert commands[0][0] == ["uv", "lock"]

    commands.clear()
    (tmp_path / "pyproject.toml").unlink()
    env.create_uv_project()
    assert commands[0][0] == ["uv", "init"]

    commands.clear()
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    env.create_uv_project()
    assert commands == []


def test_package_installer_skips_installed_and_installs_missing(monkeypatch, tmp_path):
    class Distribution:
        metadata = {"Name": "already-there"}

    commands = []
    monkeypatch.setattr(env.importlib.metadata, "distributions", lambda: [Distribution()])
    monkeypatch.setattr(env.importlib.util, "find_spec", lambda _: None)
    monkeypatch.setattr(env, "install_uv", lambda: False)
    monkeypatch.setattr(env.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    env.package_installer(["already-there", "missing-package>=1"])

    assert commands == [[sys.executable, "-m", "pip", "install", "missing-package>=1"]]


def test_package_installer_prefers_uv_add_when_project_has_lock(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    commands = []
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env.importlib.metadata, "distributions", lambda: [])
    monkeypatch.setattr(env.importlib.util, "find_spec", lambda _: None)
    monkeypatch.setattr(env, "install_uv", lambda: True)
    monkeypatch.setattr(env.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))

    env.package_installer(["missing-package"])

    assert commands == [[sys.executable, "-m", "uv", "add", "missing-package"]]


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("python", "Python 3.12.1"),
        ("pip", "pip 24.0"),
        ("uv", "uv 0.5.0"),
        ("conda", "conda 24.3.0"),
    ],
)
def test_get_version_for_supported_commands(monkeypatch, language, expected):
    monkeypatch.setattr(env, "load_from_env", lambda _: "conda")

    def check_output(cmd, **kwargs):
        outputs = {
            (sys.executable, "--version"): "Python 3.12.1\n",
            ("pip", "--version"): "pip 24.0 from somewhere\n",
            (sys.executable, "-m", "uv", "--version"): "uv 0.5.0\n",
            ("conda", "--version"): "conda 24.3.0\n",
        }
        output = outputs[tuple(cmd)]
        return output if kwargs.get("text") else output.encode()

    monkeypatch.setattr(env.subprocess, "check_output", check_output)

    assert env.get_version(language) == expected


def test_set_program_path_persists_detected_program_and_python(monkeypatch):
    saved = []
    monkeypatch.setattr(env, "load_from_env", lambda name: None)
    monkeypatch.setattr(env.shutil, "which", lambda _: "C:/tools/R.exe")
    monkeypatch.setattr(env, "get_version", lambda language: f"{language}-version")
    monkeypatch.setattr(env, "save_to_env", lambda value, name, *args: saved.append((value, name)))

    env.set_program_path("R")

    assert ("C:/tools/R.exe", "R") in saved
    assert ("R-version", "R_VERSION") in saved
    assert any(name == "PYTHON" for _, name in saved)


def test_ensure_correct_kernel_restarts_with_requested_interpreter(monkeypatch):
    commands = []
    monkeypatch.setattr(env, "load_from_env", lambda _: "C:/alternate")
    monkeypatch.setattr(env.platform, "system", lambda: "Windows")
    monkeypatch.setattr(env.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))
    monkeypatch.setattr(env.sys, "executable", "C:/current/python.exe")
    monkeypatch.setattr(env.sys, "argv", ["script.py", "--flag"])

    @env.ensure_correct_kernel
    def wrapped():
        raise AssertionError("wrapped function should not run")

    with pytest.raises(SystemExit):
        wrapped()

    assert commands == [
        [os.path.join("C:/alternate", "python.exe"), os.path.abspath(env.__file__), "--flag"]
    ]


def test_env_paths_support_missing_and_cookiecutter_storage(tmp_path, monkeypatch):
    saved = []
    executable = tmp_path / "tools" / "tool.exe"
    executable.parent.mkdir()
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(env_paths, "_win_add_to_user_path", lambda _: False)
    monkeypatch.setattr(
        env_paths, "save_to_env", lambda value, name, *args: saved.append((value, name))
    )
    monkeypatch.setenv("PATH", "")

    assert env_paths.exe_to_path("missing", tmp_path / "missing") is False
    assert env_paths.exe_to_env("tool", executable.parent) is True
    assert saved == [(str(executable.parent), "TOOL")]


def test_env_paths_windows_helpers_are_safe_without_registry(monkeypatch):
    monkeypatch.setattr(env_paths, "winreg", None)

    assert env_paths._win_add_to_user_path("C:/tools") is False
    assert env_paths._win_remove_from_user_path("C:/tools") is False


def test_secretstore_keyring_branches(monkeypatch):
    monkeypatch.setattr(secretstore, "_HAS_KEYRING", False)
    assert secretstore._keyring_get("TOKEN") is None
    assert secretstore._keyring_set("TOKEN", "value") is False

    calls = []
    monkeypatch.setattr(secretstore, "_HAS_KEYRING", True)
    monkeypatch.setattr(secretstore, "_project_slug", lambda: "project")
    monkeypatch.setattr(secretstore, "_secret_service_name", lambda: "service")
    monkeypatch.setattr(
        secretstore,
        "keyring",
        SimpleNamespace(
            get_password=lambda service, key: "value" if key == "TOKEN" else None,
            set_password=lambda service, key, value: calls.append((service, key, value)),
        ),
    )

    assert secretstore._keyring_get("TOKEN") == "value"
    assert secretstore._keyring_set("TOKEN", "value") is True
    assert calls == [("service", "project:TOKEN", "value")]


def test_secretstore_toml_fallback_without_tomlkit(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(secretstore, "tomlkit", None)

    secretstore.save_to_env("value", "TOKEN", ".cookiecutter", str(pyproject))

    assert 'TOKEN = "value"' in pyproject.read_text(encoding="utf-8")


def test_tomlutils_fallback_and_dataset_parser(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    monkeypatch.setattr(tomlutils, "tomlkit", None)

    tomlutils.write_toml(
        data={"patterns": ["data/*"]},
        folder=str(tmp_path),
        tool_name="datasets",
        toml_path=str(pyproject),
    )

    assert tomlutils.read_toml(folder=str(tmp_path), tool_name="datasets") == {
        "patterns": ["data/*"]
    }
    assert tomlutils._parse_dataset_path("./data/*") == {
        "parent_path": pathlib.Path("data"),
        "sub_dir": True,
    }
    assert tomlutils._parse_dataset_path("/") == {
        "parent_path": pathlib.Path("."),
        "sub_dir": False,
    }


def test_toml_compat_reads_bom_and_dumps_data(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("\ufeff[demo]\nvalue = 'yes'\n", encoding="utf-8")

    assert toml_compat.read_toml_text(path).startswith("[demo]")
    assert toml_compat.load_toml_path(path) == {"demo": {"value": "yes"}}
    assert "[demo]" in toml_compat.dumps_toml({"demo": {"value": "yes"}})
