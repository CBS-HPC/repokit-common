import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import toml

    tomli_w = None
else:
    import tomli_w
    import tomllib as toml


def read_toml_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def load_toml_path(path: str | Path) -> dict:
    toml_path = Path(path)
    if sys.version_info < (3, 11):
        with open(toml_path, "r", encoding="utf-8-sig") as f:
            return toml.load(f)

    return toml.loads(read_toml_text(toml_path))


def dumps_toml(data: dict) -> str:
    if sys.version_info < (3, 11):
        return toml.dumps(data)

    assert tomli_w is not None
    return tomli_w.dumps(data)
