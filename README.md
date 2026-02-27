# repokit-common

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/CBS-HPC/repokit-common/actions/workflows/ci.yml/badge.svg)](https://github.com/CBS-HPC/repokit-common/actions/workflows/ci.yml)

Shared utilities used across the **repokit** ecosystem. This package is intentionally lightweight and focused on cross-cutting helpers (env, prompts, paths, config utilities).

## Highlights

- Environment helpers (load/save `.env`, config paths)
- Prompt utilities and safe defaults
- File/path utilities used by setup flows

## Installation

`repokit-common` is not published on PyPI yet. Use local wheel installation.

Install from local wheel files (`/dist`):

```bash
pip install https://github.com/CBS-HPC/repokit-common/raw/main/dist/repokit_common-0.1-py3-none-any.whl
```

## Usage

`repokit-common` is primarily a dependency of other packages, but can also be used directly:

```python
from repokit_common import load_from_env, save_to_env
```

## Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
