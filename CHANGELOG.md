# Changelog

All notable changes to `repokit-common` are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-08-13

### Added

- A documented stable public API defined by `repokit_common.__all__`.
- A tagged GitHub Release workflow that publishes immutable wheel, source, and
  checksum assets.
- Cross-platform CI for Python 3.10 and 3.12 on Linux, Windows, and macOS.
- Regression tests for executable resolution, environment/config precedence,
  TOML round trips, project roots, path handling, prompts, and commands.

### Changed

- `is_installed(..., local_path=...)` makes a discovered local executable
  available on the current process PATH and gives it precedence over global
  executables with the same name.
- `load_from_env()` now honours an already-set process environment variable
  before reading `.env`, matching its documented precedence.
- `split_multi()` consistently returns a list; missing or invalid input now
  returns `[]`.
- `run_command()` replaces the previously re-exported private `_run()` helper.
- Removed unused runtime dependencies `PyYAML` and `requests`.

### Removed

- Private keyring helpers and `_run()` are no longer re-exported from the
  package root.

## [0.x]

This release establishes the current API baseline. The compatibility promise
will be formalized in a future 1.0 release.
