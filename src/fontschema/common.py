from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def dump_json(data: Any, path: str | Path | None = None) -> str:
    text = json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    if path is not None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return text


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()
