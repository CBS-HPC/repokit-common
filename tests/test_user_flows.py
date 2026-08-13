import builtins
from types import SimpleNamespace

import repokit_common.env as env
import repokit_common.prompts as prompts


def test_git_user_info_uses_cookiecutter_defaults(monkeypatch):
    saved = []
    answers = iter(["", ""])
    monkeypatch.setattr(
        prompts,
        "load_from_env",
        lambda name, *_: {"AUTHORS": "Ada Lovelace", "EMAIL": "ada@example.test"}[name],
    )
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    monkeypatch.setattr(prompts, "save_to_env", lambda value, name: saved.append((value, name)))

    assert prompts.git_user_info("git") == ("Ada Lovelace", "ada@example.test")
    assert saved == [("Ada Lovelace", "GIT_USER"), ("ada@example.test", "GIT_EMAIL")]


def test_git_user_info_skips_non_git_version_control():
    assert prompts.git_user_info("none") == (None, None)


def test_repo_user_info_retries_visibility_and_saves_credentials(monkeypatch):
    saved = []
    answers = iter(["ada", "internal", "ada", "public"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    monkeypatch.setattr(prompts, "load_from_env", lambda _: None)
    monkeypatch.setattr(prompts.getpass, "getpass", lambda _: "secret")
    monkeypatch.setattr(prompts, "save_to_env", lambda value, name: saved.append((value, name)))

    assert prompts.repo_user_info("git", "demo", "github") == (
        "ada",
        "public",
        "secret",
        "github.com",
    )
    assert saved == [
        ("ada", "GITHUB_USER"),
        ("public", "GITHUB_PRIVACY"),
        ("demo", "GITHUB_REPO"),
        ("secret", "GITHUB_TOKEN"),
        ("github.com", "GITHUB_HOSTNAME"),
    ]


def test_repo_user_info_skips_unsupported_host_or_vcs():
    assert prompts.repo_user_info("none", "demo", "github") == (None, None, None, None)
    assert prompts.repo_user_info("git", "demo", "other") == (None, None, None, None)


def test_repo_user_info_supports_codeberg(monkeypatch):
    saved = []
    answers = iter(["ada", ""])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    monkeypatch.setattr(prompts, "load_from_env", lambda _: "stored-token")
    monkeypatch.setattr(prompts, "save_to_env", lambda value, name: saved.append((value, name)))

    assert prompts.repo_user_info("git", "demo", "codeberg") == (
        "ada",
        "private",
        "stored-token",
        "codeberg.org",
    )
    assert ("ada", "CODEBERG_USER") in saved
    assert ("stored-token", "CODEBERG_TOKEN") in saved


def test_get_version_for_external_programs(monkeypatch):
    def get_path(language):
        return {
            "r": "C:/tools/R.exe",
            "matlab": "C:/tools/matlab.exe",
            "stata": "C:/Stata18/StataSE.exe",
            "sas": "C:/tools/sas.exe",
        }.get(language)

    monkeypatch.setattr(env, "load_from_env", get_path)
    monkeypatch.setattr(
        env.subprocess,
        "run",
        lambda command, **_: SimpleNamespace(
            stdout="R version 4.4.0" if command[0].endswith("R.exe") else "24.1"
        ),
    )

    assert env.get_version("r") == "R version 4.4.0"
    assert env.get_version("matlab") == "Matlab 24.1"
    assert env.get_version("stata") == "Stata 18 SE"
    assert env.get_version("sas") == "24.1"
    assert env.get_version("missing") == "Unknown"


def test_run_script_builds_supported_external_commands(monkeypatch):
    commands = []
    monkeypatch.setattr(
        env,
        "load_from_env",
        lambda name: {"r": "R.exe", "rscript": "Rscript.exe", "matlab": "matlab"}.get(name.lower()),
    )
    monkeypatch.setattr(
        env.subprocess,
        "run",
        lambda command, **_: commands.append(command) or SimpleNamespace(stdout="ok"),
    )

    assert env.run_script("r", ["-e", "--args", "print('ok')"]) == "ok"
    assert commands[-1] == ["Rscript.exe", "-e", "print('ok')"]
    assert env.run_script("matlab", ["disp(1)"]) == "ok"
    assert commands[-1] == ["matlab", "-batch", "disp(1)"]
    assert env.run_script("unknown", ["x"]) == "Unknown executable path"


def test_create_uv_project_handles_unavailable_uv_and_command_failure(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env, "install_uv", lambda: False)

    assert env.create_uv_project() is None

    monkeypatch.setattr(env, "install_uv", lambda: True)
    monkeypatch.setattr(
        env.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(env.subprocess.CalledProcessError(1, "uv")),
    )
    assert env.create_uv_project() is None


def test_write_uv_requires_uses_plain_toml_fallback(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env, "tomlkit", None)
    monkeypatch.setattr(env.subprocess, "check_output", lambda *args: b"Python 3.11.9\n")

    env.write_uv_requires()

    assert 'requires-python = ">= 3.11.9"' in pyproject.read_text(encoding="utf-8")


def test_package_installer_retries_uv_then_pip(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(env, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(env.importlib.metadata, "distributions", lambda: [])
    monkeypatch.setattr(env.importlib.util, "find_spec", lambda _: None)
    monkeypatch.setattr(env, "install_uv", lambda: True)

    def run(command, **kwargs):
        commands.append(command)
        if "uv" in command:
            raise env.subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(env.subprocess, "run", run)

    env.package_installer(["missing"])

    assert commands == [
        [env.sys.executable, "-m", "uv", "pip", "install", "missing"],
        [env.sys.executable, "-m", "uv", "pip", "install", "--system", "missing"],
        [env.sys.executable, "-m", "pip", "install", "missing"],
    ]


def test_get_version_returns_command_name_when_pip_or_uv_fail(monkeypatch):
    monkeypatch.setattr(
        env.subprocess,
        "check_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(env.subprocess.CalledProcessError(1, args)),
    )

    assert env.get_version("pip") == "pip"
    assert env.get_version("uv") == "uv"


def test_ensure_correct_kernel_runs_when_interpreter_directory_matches(monkeypatch):
    monkeypatch.setattr(env, "load_from_env", lambda _: "C:/current")
    monkeypatch.setattr(env.platform, "system", lambda: "Windows")
    monkeypatch.setattr(env.sys, "executable", "C:/current/python.exe")

    @env.ensure_correct_kernel
    def value():
        return "ok"

    assert value() == "ok"
