"""Executable resolution and installation checks."""

from __future__ import annotations

import os
import pathlib
import platform
import shutil

from .base import PROJECT_ROOT
from .secretstore import load_from_env, save_to_env


def _candidate_executable_names(executable: str) -> list[str]:
    names = [executable]
    if platform.system().lower() == "windows":
        for ext in (".exe", ".bat", ".cmd"):
            if not executable.lower().endswith(ext):
                names.append(f"{executable}{ext}")
    return names


def _is_within_root(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _find_executable_in_root(root: pathlib.Path, names: list[str]) -> pathlib.Path | None:
    if not root.exists():
        return None
    for n in names:
        p = root / n
        if p.is_file():
            return p.resolve()
    for n in names:
        try:
            for p in root.rglob(n):
                if p.is_file():
                    return p.resolve()
        except OSError:
            pass
    return None


def _resolve_from_config_or_path(executable: str, names: list[str]) -> pathlib.Path | None:
    configured = load_from_env(executable)
    if configured:
        p = pathlib.Path(configured).resolve()
        if p.exists():
            if p.is_file() and p.name in names:
                return p
            if p.is_dir():
                return _find_executable_in_root(p, names)
    resolved = shutil.which(executable)
    return pathlib.Path(resolved).resolve() if resolved else None


def resolve_executable(executable: str, local_path: str | None = None) -> pathlib.Path | None:
    """
    Resolve executable path.
    - If local_path is provided, only return paths under that local root.
    - Otherwise resolve from configured env path first, then PATH.
    """
    names = _candidate_executable_names(executable)

    if local_path is not None:
        local_root = pathlib.Path(local_path)
        if not local_root.is_absolute():
            local_root = PROJECT_ROOT / local_root
        local_root = local_root.resolve()

        configured = load_from_env(executable)
        if configured:
            p = pathlib.Path(configured).resolve()
            if p.exists() and _is_within_root(p, local_root):
                if p.is_file() and p.name in names:
                    return p
                if p.is_dir():
                    m = _find_executable_in_root(p, names)
                    if m:
                        return m

        local_match = _find_executable_in_root(local_root, names)
        if local_match:
            return local_match

        which_match = shutil.which(executable)
        if which_match:
            p = pathlib.Path(which_match).resolve()
            if _is_within_root(p, local_root):
                return p
        return None

    return _resolve_from_config_or_path(executable, names)


def persist_executable_path(executable: str, executable_path: pathlib.Path) -> bool:
    """Persist executable directory to .env and process environment."""
    p = executable_path.resolve()
    pdir = p.parent if p.is_file() else p
    save_to_env(str(pdir), executable.upper())
    os.environ[executable.upper()] = str(pdir)
    return True


def is_installed(
    executable: str = None,
    name: str = None,
    local_path: str | None = None,
) -> bool:
    if name is None:
        name = executable

    if (
        not isinstance(executable, str)
        or not isinstance(name, str)
        or (local_path is not None and not isinstance(local_path, str))
    ):
        raise ValueError(
            "'executable' and 'name' must be strings; 'local_path' must be string or None."
        )

    resolved = resolve_executable(executable=executable, local_path=local_path)
    if resolved is None:
        print(f"{name} is not on Path")
        return False
    return persist_executable_path(executable, resolved)
