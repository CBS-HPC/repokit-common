# Contributing to repokit-common

`repokit-common` provides shared behavior used by the wider Repokit ecosystem.
Changes to exported functions should therefore be treated as compatibility work.

## Development setup

```powershell
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=repokit_common --cov-report=term-missing
uv build
uv tool run twine check dist/*
```

## Compatibility rules

- Only names in `repokit_common.__all__` are part of the supported public API.
- Preserve behavior across Python 3.10 and 3.12 on Linux, Windows, and macOS.
- Add a regression test for every bug fix that changes configuration, paths,
  executable lookup, or TOML output.
- Treat `PROJECT_ROOT`, `.env`, `pyproject.toml`, PATH, and Windows user PATH
  writes as externally visible behavior.
- Update `CHANGELOG.md` for user-visible changes.

## Release preparation

- Keep `uv.lock` synchronized with `pyproject.toml`.
- Build the wheel and source distribution from a clean checkout.
- Verify downstream consumers before merging a shared API change.
- A `vX.Y.Z` tag triggers the immutable GitHub Release workflow. The tag must
  match the package version exactly.
