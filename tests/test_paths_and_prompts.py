import builtins
import os

import pytest

import repokit_common.paths as paths
import repokit_common.prompts as prompts


def test_from_root_and_change_dir(tmp_path, monkeypatch):
    original = os.getcwd()
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)

    assert paths.from_root("child", "file.txt") == child / "file.txt"
    with paths.change_dir("child"):
        assert os.getcwd() == str(child)
    assert os.getcwd() == original


def test_get_relative_path_for_descendant(tmp_path, monkeypatch):
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(tmp_path)

    assert paths.get_relative_path(child) == "child"


def test_make_safe_path_formats_languages(tmp_path, monkeypatch):
    target = tmp_path / "folder" / "script.py"
    target.parent.mkdir()
    target.write_text("", encoding="utf-8")
    monkeypatch.setattr(paths.platform, "system", lambda: "Windows")

    assert paths.make_safe_path(str(target), "python").endswith("folder/script.py")
    assert paths.make_safe_path(str(target), "r").endswith("folder/script.py")
    assert paths.make_safe_path(str(target), "matlab").startswith("'")
    assert paths.make_safe_path(str(target), "stata").startswith('"')
    with pytest.raises(ValueError, match="Unsupported language"):
        paths.make_safe_path(str(target), "unknown")


def test_split_multi_returns_normalized_list():
    assert prompts.split_multi("one; two,three") == ["one", "two", "three"]
    assert prompts.split_multi(None) == []
    assert prompts.split_multi(123) == []


def test_ask_yes_no_retries_until_valid(monkeypatch):
    answers = iter(["maybe", "Y"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))

    assert prompts.ask_yes_no("Continue?") is True


def test_prompt_user_retries_until_valid_selection(monkeypatch):
    answers = iter(["0", "not-a-number", "2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))

    assert prompts.prompt_user("Choose", ["first", "second"]) == "second"
