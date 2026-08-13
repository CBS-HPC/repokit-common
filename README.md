# repokit-common

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/CBS-HPC/repokit-common/actions/workflows/ci.yml/badge.svg)](https://github.com/CBS-HPC/repokit-common/actions/workflows/ci.yml)

Shared utilities used across the **Repokit** ecosystem. This package is focused
on cross-cutting helpers for project roots, paths, executable discovery,
configuration, prompts, and TOML-backed metadata.

## Highlights

- Environment and executable helpers
- `.env` and `pyproject.toml` configuration utilities
- Path and project-root helpers
- Prompt utilities used by project setup flows

## Installation

Release artifacts are published as immutable GitHub Release assets. Install a
specific version rather than a mutable branch URL:

```bash
pip install https://github.com/CBS-HPC/repokit-common/releases/download/v1.0.0/repokit_common-1.0.0-py3-none-any.whl
```

Each release includes `SHA256SUMS` for artifact verification.

## Usage

`repokit-common` is primarily a dependency of other packages, but can also be used directly:

```python
from repokit_common import is_installed, load_from_env, save_to_env

token = load_from_env("GITHUB_TOKEN")
is_available = is_installed("rclone", "Rclone", local_path="./bin")
```

## Stable API and side effects

The names in `repokit_common.__all__` are the supported 1.x API. Names with a
leading underscore and module-internal imports are not compatibility promises.

Some public functions intentionally change external state:

- `save_to_env()` and `write_toml()` write `.env` or `pyproject.toml`.
- `toml_dataset_path()` may write the resolved dataset pattern to TOML.
- `exe_to_path()` and `is_installed()` modify the current process PATH; on
  Windows they may also update the user PATH for future shells.
- `install_uv()`, `install_base_deps()`, and `package_installer()` install
  packages.

`load_from_env()` resolves values in this order: optional keyring, an existing
process environment variable, `.env`, then a TOML tool section.

## Development

```powershell
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=repokit_common --cov-report=term-missing
uv build
uv tool run twine check dist/*
```

The supported test matrix is Python 3.10 and 3.12 on Linux, Windows, and macOS.
See `CONTRIBUTING.md` for compatibility and release rules.

## License

MIT
