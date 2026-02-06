# repokit/common/base.py  (stdlib only)
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_DEPS = [
    "python-dotenv>=1.0",
    "pathspec>=0.12",
    'toml>=0.10 ; python_version < "3.11"',
    'tomli-w>=1.0 ; python_version >= "3.11"',
]


def install_uv():
    try:
        import uv  # noqa: F401

        return True
    except ImportError:
        try:
            print("Installing 'uv' package into current Python environment...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "uv"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print("'uv' installed successfully.")

            import uv  # noqa: F401

            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install 'uv' via pip: {e}")
            return False


def install_base_deps(deps: list[str] = BASE_DEPS) -> None:
    # best-effort installer; fine to call early from project_setup.py
    if install_uv():
        try:
            env = os.environ.copy()
            env["UV_LINK_MODE"] = "copy"
            subprocess.run(
                [sys.executable, "-m", "uv", "pip", "install", "--system", *deps],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            return
        except Exception:
            pass
    # fallback to pip
    for dep in deps:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", dep],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            # keep going: some users may be offline; libs will be required lazily later
            pass


def _find_project_root_from_cwd() -> Path | None:
    cwd = Path.cwd().resolve()
    markers = {
        "activate.ps1",
        "activate.sh",
        "deactivate.ps1",
        "deactivate.sh",
        "pyproject.toml",
        "dmp.json",
        ".venv",
        ".conda",
    }
    for p in (cwd, *cwd.parents):
        if any((p / m).exists() for m in markers):
            return p
    return None


def project_root() -> Path:
    # 1) cwd-based marker detection (works for non-editable installs)
    cwd_root = _find_project_root_from_cwd()
    if cwd_root:
        return cwd_root

    # 2) vendored layout under setup/repokit/external
    here = Path(__file__).resolve()
    try:
        if (
            here.parents[2].name == "repokit-common"
            and here.parents[3].name == "external"
            and here.parents[4].name == "repokit"
            and here.parents[5].name == "setup"
        ):
            return here.parents[6]
    except IndexError:
        pass

    # 3) standalone mode: use the current working directory directly.
    return Path.cwd().resolve()


# Convenience constant + helper
PROJECT_ROOT = project_root()
