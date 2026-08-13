import os
import pathlib
import shutil

import pytest

import repokit_common.executables as executables
import repokit_common.env_paths as env_paths


def _make_executable(path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def isolated_path(monkeypatch):
    monkeypatch.setattr(env_paths, "_win_add_to_user_path", lambda _: False)
    monkeypatch.setenv("PATH", "")


def test_local_nested_executable_is_preferred_and_callable(tmp_path, monkeypatch, isolated_path):
    local_executable = _make_executable(tmp_path / "bin" / "rclone-v1" / "rclone.exe")
    persisted = {}

    monkeypatch.setattr(executables, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        executables, "save_to_env", lambda value, name: persisted.update({name: value})
    )

    assert executables.is_installed("rclone", "Rclone", local_path="./bin") is True
    assert pathlib.Path(shutil.which("rclone")).resolve() == local_executable.resolve()
    assert persisted["RCLONE"] == str(local_executable.parent.resolve())
    assert os.environ["RCLONE"] == str(local_executable.parent.resolve())


def test_local_executable_takes_precedence_over_global_match(tmp_path, monkeypatch, isolated_path):
    global_executable = _make_executable(tmp_path / "global" / "rclone.exe")
    local_executable = _make_executable(tmp_path / "bin" / "rclone-v1" / "rclone.exe")

    monkeypatch.setattr(executables, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(executables, "save_to_env", lambda *args: None)
    monkeypatch.setenv("PATH", str(global_executable.parent))

    assert executables.is_installed("rclone", "Rclone", local_path="bin") is True
    assert pathlib.Path(shutil.which("rclone")).resolve() == local_executable.resolve()


def test_local_lookup_rejects_global_binary_outside_local_root(
    tmp_path, monkeypatch, isolated_path
):
    global_executable = _make_executable(tmp_path / "global" / "rclone.exe")

    monkeypatch.setattr(executables, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(executables, "save_to_env", lambda *args: None)
    monkeypatch.setenv("PATH", str(global_executable.parent))

    assert executables.is_installed("rclone", "Rclone", local_path="bin") is False
    assert pathlib.Path(shutil.which("rclone")).resolve() == global_executable.resolve()


def test_configured_path_outside_local_root_does_not_override_local_match(
    tmp_path, monkeypatch, isolated_path
):
    configured = _make_executable(tmp_path / "global" / "rclone.exe")
    local_executable = _make_executable(tmp_path / "bin" / "rclone-v1" / "rclone.exe")

    monkeypatch.setattr(executables, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(executables, "load_from_env", lambda _: str(configured))
    monkeypatch.setattr(executables, "save_to_env", lambda *args: None)

    resolved = executables.resolve_executable("rclone", local_path="bin")

    assert resolved == local_executable.resolve()


def test_non_local_resolution_uses_configured_directory(tmp_path, monkeypatch):
    executable = _make_executable(tmp_path / "tools" / "rclone.exe")
    monkeypatch.setattr(executables, "load_from_env", lambda _: str(executable.parent))

    assert executables.resolve_executable("rclone") == executable.resolve()


def test_candidate_names_include_windows_extensions(monkeypatch):
    monkeypatch.setattr(executables.platform, "system", lambda: "Windows")

    assert executables._candidate_executable_names("rclone") == [
        "rclone",
        "rclone.exe",
        "rclone.bat",
        "rclone.cmd",
    ]
    assert executables._candidate_executable_names("rclone.exe") == ["rclone.exe"]


def test_exe_to_path_deduplicates_and_prepends(tmp_path, monkeypatch, isolated_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(second), str(first), str(second)]))

    assert env_paths.exe_to_path("tool", first, prepend=True) is True

    entries = os.environ["PATH"].split(os.pathsep)
    assert pathlib.Path(entries[0]).resolve() == first.resolve()
    assert sum(pathlib.Path(entry).resolve() == first.resolve() for entry in entries) == 1
    assert pathlib.Path(entries[-1]).resolve() == second.resolve()


def test_exe_to_path_accepts_executable_file_path(tmp_path, isolated_path):
    executable = _make_executable(tmp_path / "tools" / "tool.exe")

    assert env_paths.exe_to_path("tool", executable, prepend=True) is True
    assert (
        pathlib.Path(os.environ["PATH"].split(os.pathsep)[0]).resolve()
        == executable.parent.resolve()
    )


def test_remove_from_env_removes_normalized_path(tmp_path, monkeypatch, isolated_path):
    keep = tmp_path / "keep"
    remove = tmp_path / "remove"
    keep.mkdir()
    remove.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(keep), str(remove)]))

    assert env_paths.remove_from_env("tool", str(remove)) is True
    assert [pathlib.Path(entry).resolve() for entry in os.environ["PATH"].split(os.pathsep)] == [
        keep.resolve()
    ]


def test_exe_to_path_reports_persistent_windows_update(tmp_path, monkeypatch, isolated_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    monkeypatch.setattr(env_paths.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        env_paths, "_win_add_to_user_path", lambda path: path == str(tools.resolve())
    )

    assert env_paths.exe_to_path("tool", tools) is True
    assert pathlib.Path(os.environ["PATH"]).resolve() == tools.resolve()


def test_exe_to_env_supports_relative_cookiecutter_paths(tmp_path, monkeypatch):
    executable_dir = tmp_path / "bin"
    executable_dir.mkdir()
    saved = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(env_paths, "get_relative_path", lambda path: "bin")
    monkeypatch.setattr(
        env_paths, "save_to_env", lambda value, name, *_: saved.append((value, name))
    )
    monkeypatch.setattr(env_paths, "load_dotenv", lambda *args, **kwargs: None)

    assert env_paths.exe_to_env("r", executable_dir, relative=True) is True
    assert saved == [("bin", "R_PATH")]
    assert os.environ["R_PATH"] == "bin"
