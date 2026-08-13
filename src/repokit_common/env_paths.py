"""PATH and executable env persistence helpers."""

from __future__ import annotations

import ctypes
import os
import pathlib
import platform
import sys

from dotenv import load_dotenv

from .paths import check_path_format, get_relative_path
from .secretstore import load_from_env, save_to_env

if sys.platform == "win32":
    import winreg
else:
    winreg = None


def _win_add_to_user_path(path: str) -> bool:
    if winreg is None:
        return False
    path = check_path_format(path)
    if not path or not os.path.exists(path):
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
        ) as key:
            current_path, _ = winreg.QueryValueEx(key, "Path")
            current_path = current_path or ""
            parts = [p for p in current_path.split(";") if p]
            if path not in parts:
                parts.append(path)
                new_path = ";".join(parts)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
                return True
            return False
    except Exception:
        return False


def exe_to_path(executable: str, path=None, *, prepend: bool = False) -> bool:
    """Add an executable directory to the current process PATH.

    When ``prepend`` is true, the directory takes precedence over an existing
    executable with the same name elsewhere on PATH. Windows installations are
    also recorded in the user PATH for future shells.
    """
    if path is None:
        path = load_from_env(executable, ".cookiecutter")
    path = check_path_format(path)
    if not path:
        print(f"{executable}:path missing")
        return False

    path_obj = pathlib.Path(path).expanduser()
    if path_obj.is_file():
        path_obj = path_obj.parent
    if not path_obj.is_dir():
        print(f"{executable}:path does not exist: {path}")
        return False

    path_text = str(path_obj.resolve())
    normalized_path = _norm_for_compare(path_text)
    current_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    other_entries = [
        entry for entry in current_entries if _norm_for_compare(entry) != normalized_path
    ]
    updated_entries = [path_text, *other_entries] if prepend else [*other_entries, path_text]
    os.environ["PATH"] = os.pathsep.join(updated_entries)

    if platform.system().lower() == "windows":
        if _win_add_to_user_path(path_text):
            print(f"{executable} added to user PATH persistently")
        else:
            print(f"{executable} added to process PATH only")
    print(f"{executable}:path set to {path_text}")
    return True


def _norm_for_compare(p: str) -> str:
    return pathlib.Path(p).expanduser().resolve().as_posix().lower()


def _win_remove_from_user_path(path: str) -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
        ) as key:
            current_path, _ = winreg.QueryValueEx(key, "Path")
            current_path = current_path or ""
            parts = [p for p in current_path.split(";") if p]
            target = _norm_for_compare(path)
            kept = [p for p in parts if _norm_for_compare(p) != target]
            if kept != parts:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(kept))
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
                return True
    except Exception:
        return False
    return False


def remove_from_env(executable: str, path: str = None):
    if not path:
        path = load_from_env(executable)
    if not path:
        return False
    path = check_path_format(path)
    if not path:
        return False
    os.environ["PATH"] = os.pathsep.join(
        [
            p
            for p in os.environ.get("PATH", "").split(os.pathsep)
            if _norm_for_compare(p) != _norm_for_compare(path)
        ]
    )
    if platform.system().lower() == "windows":
        _win_remove_from_user_path(path)
    return True


def exe_to_env(executable: str, path=None, relative=False):
    if path is None:
        path = load_from_env(executable, ".cookiecutter")
    path = check_path_format(path)
    if not path:
        print(f"{executable}:path missing")
        return False
    if relative:
        path = get_relative_path(path)
    if os.path.exists(path):
        path_name = executable.upper()
        if path_name == "R":
            path_name = "R_PATH"
        save_to_env(path, path_name, ".cookiecutter")
        os.environ[path_name] = path
        load_dotenv(".cookiecutter", override=True)
        print(f"executable:{executable}:path set in .cookiecutter to {path}")
        return True
    print(f"{executable}:path does not exist: {path}")
    return False
