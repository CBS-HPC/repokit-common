import pathlib

import repokit_common.secretstore as secretstore


def test_process_environment_has_priority_over_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("TOKEN", "from-process")

    assert secretstore.load_from_env("TOKEN") == "from-process"


def test_load_from_env_falls_back_to_dotenv_then_toml(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TOKEN=from-file\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.cookiecutter]\nTOKEN = 'from-toml'\n", encoding="utf-8"
    )
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("TOKEN", raising=False)

    assert secretstore.load_from_env("TOKEN") == "from-file"
    assert secretstore.load_from_env("TOKEN", env_file=".cookiecutter") == "from-toml"


def test_save_to_env_updates_dotenv_without_touching_other_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TOKEN=old\nOTHER=keep\n", encoding="utf-8")
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)

    secretstore.save_to_env("new", "token")

    assert env_file.read_text(encoding="utf-8") == "TOKEN=new\nOTHER=keep\n"


def test_save_to_env_uses_keyring_without_file_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(
        secretstore, "_keyring_set", lambda name, value: calls.append((name, value)) or True
    )

    secretstore.save_to_env(
        "secret",
        "token",
        use_keyring=True,
        also_write_file_fallback=False,
    )

    assert calls == [("TOKEN", "secret")]
    assert not (tmp_path / ".env").exists()


def test_toml_save_preserves_comments_and_bom(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\ufeff# project-comment\n[tool.cookiecutter]\n# token-comment\nTOKEN = 'old'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)

    secretstore.save_to_env("new", "TOKEN", ".cookiecutter", str(pyproject))

    text = pyproject.read_text(encoding="utf-8-sig")
    assert "# project-comment" in text
    assert "# token-comment" in text
    assert 'TOKEN = "new"' in text


def test_slug_helpers_are_stable(monkeypatch, tmp_path):
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", pathlib.Path(tmp_path / "My Project"))
    monkeypatch.setenv("PROJECT_SLUG", "A Project / 2026")
    monkeypatch.setenv("SECRET_SERVICE_NAME", "repokit-test")

    assert secretstore._slugify("A Project / 2026") == "a-project-2026"
    assert secretstore._project_slug() == "a-project-2026"
    assert secretstore._secret_service_name() == "repokit-test::a-project-2026"


def test_project_slug_uses_git_root_and_keyring_global_fallback(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("PROJECT_SLUG", raising=False)
    monkeypatch.delenv("RT_PROJECT_SLUG", raising=False)
    monkeypatch.setattr(secretstore, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        secretstore.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "C:/work/My Repo\n"}
        )(),
    )
    monkeypatch.setattr(secretstore, "_HAS_KEYRING", True)
    monkeypatch.setattr(secretstore, "_secret_service_name", lambda: "service")
    monkeypatch.setattr(
        secretstore,
        "keyring",
        type(
            "Keyring",
            (),
            {
                "get_password": staticmethod(
                    lambda service, key: (
                        calls.append((service, key)) or ("global" if key == "TOKEN" else None)
                    )
                )
            },
        ),
    )

    assert secretstore._project_slug() == "my-repo"
    assert secretstore._keyring_get("TOKEN") == "global"
    assert calls == [("service", "my-repo:TOKEN"), ("service", "TOKEN")]


def test_save_to_env_writes_global_keyring_alias(monkeypatch):
    calls = []
    monkeypatch.setattr(secretstore, "_HAS_KEYRING", True)
    monkeypatch.setenv("SECRET_WRITE_GLOBAL_ALIAS", "true")
    monkeypatch.setattr(secretstore, "_project_slug", lambda: "project")
    monkeypatch.setattr(secretstore, "_secret_service_name", lambda: "service")
    monkeypatch.setattr(
        secretstore,
        "keyring",
        type(
            "Keyring",
            (),
            {
                "set_password": staticmethod(
                    lambda service, key, value: calls.append((service, key, value))
                )
            },
        ),
    )

    assert secretstore._keyring_set("TOKEN", "value") is True
    assert calls == [("service", "project:TOKEN", "value"), ("service", "TOKEN", "value")]
