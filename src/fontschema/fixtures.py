from __future__ import annotations

import hashlib
import shutil
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

from .common import dump_json, repo_root
from .sources import source_path
from .ttx.dump import dump_font

VARIATION_TERMS = ("varc", "avar", "hvar", "vvar", "mvar", "gvar", "cvar", "fvar", "variation", "varstore")


def load_fonts() -> list[dict[str, Any]]:
    path = repo_root() / "sources" / "fonts.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")).get("font", [])


def download_fonts() -> list[dict[str, Any]]:
    out = repo_root() / "fixtures" / "downloaded"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in load_fonts():
        dest = out / item["filename"]
        if not dest.exists():
            print(f"download {item['name']} -> {dest}")
            urllib.request.urlretrieve(item["url"], dest)
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        rows.append({**item, "path": str(dest), "sha256": digest, "bytes": dest.stat().st_size})
    dump_json(rows, out / "inventory.json")
    return rows


def dump_fonts() -> list[str]:
    root = repo_root()
    downloaded = root / "fixtures" / "downloaded"
    if not downloaded.exists():
        raise SystemExit("no downloaded fonts; run `fontschema fixtures download`")
    outputs = []
    for item in load_fonts():
        path = downloaded / item["filename"]
        if not path.exists():
            continue
        out = root / "generated" / "ttx" / "fonts" / item["name"]
        outputs.extend(str(p) for p in dump_font(path, out))
    return outputs


def collect_fonttools() -> dict[str, Any]:
    src = source_path("fonttools")
    if src is None:
        raise SystemExit("fonttools source not found; run `fontschema sources sync` or vendor it as a subtree")
    tests = src / "Tests"
    out = repo_root() / "generated" / "ttx" / "fonttools-fixtures"
    out.mkdir(parents=True, exist_ok=True)
    extensions = {".ttx", ".ttf", ".otf", ".xml", ".designspace"}
    matches: list[dict[str, str]] = []
    for p in tests.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue
        rel_lower = str(p.relative_to(tests)).lower()
        if not any(term in rel_lower for term in VARIATION_TERMS):
            continue
        rel = p.relative_to(tests)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        matches.append({"source": str(p.relative_to(src)), "copy": str(dest.relative_to(repo_root()))})
    inventory = {"fonttools": str(src), "count": len(matches), "files": matches}
    dump_json(inventory, out / "inventory.json")
    return inventory
