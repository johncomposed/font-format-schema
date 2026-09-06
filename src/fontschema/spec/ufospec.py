"""Extract attribute tables from the UFO specification markdown.

The UFO spec (vendor/ufo-spec) documents every plist key and GLIF attribute in
markdown tables.  This module parses those tables into a JSON document that the
schema generator uses for descriptions, declared types and defaults, so the
generated schemas quote the normative text instead of paraphrasing it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from ..common import dump_json, repo_root
from ..sources import source_path

UFO3 = Path("versions/ufo3")

# (file, section label) pairs.  Section label is derived from the nearest
# preceding "###"/"####"/"#####" heading.
PAGES = {
    "fontinfo": UFO3 / "fontinfo.plist.md",
    "glif": UFO3 / "glyphs/glif.md",
    "metainfo": UFO3 / "metainfo.plist.md",
    "layercontents": UFO3 / "layercontents.plist.md",
    "layerinfo": UFO3 / "glyphs/layerinfo.plist.md",
    "lib": UFO3 / "lib.plist.md",
    "groups": UFO3 / "groups.plist.md",
    "kerning": UFO3 / "kerning.plist.md",
    "contents": UFO3 / "glyphs/contents.plist.md",
}

LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
REF_RE = re.compile(r"\[([^\]]+)\]")


def _clean(cell: str) -> str:
    cell = cell.strip()
    cell = cell.replace("<br>", " ")
    cell = LINK_RE.sub(r"\1", cell)
    cell = REF_RE.sub(r"\1", cell)
    cell = re.sub(r"\s+", " ", cell)
    return cell


def _parse_tables(text: str) -> list[dict[str, Any]]:
    """Return every markdown table with its heading context."""
    tables: list[dict[str, Any]] = []
    heading_stack: list[str] = []
    anchor: str | None = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(#{2,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            heading_stack = heading_stack[: level - 2]
            heading_stack.append(m.group(2).strip())
            i += 1
            continue
        m = re.match(r"^\{:\s*#([\w-]+)\s*\}", line)
        if m:
            anchor = m.group(1)
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-| ]+\|?\s*$", lines[i + 1]):
            header = [_clean(c) for c in line.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                cells = [_clean(c) for c in lines[i].strip().strip("|").split("|")]
                if len(cells) < len(header):
                    cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells)))
                i += 1
            tables.append({"headings": list(heading_stack), "anchor": anchor, "columns": header, "rows": rows})
            continue
        i += 1
    return tables


def _entry(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in (("type", "type"), ("description", "description"), ("default", "default")):
        if row.get(src):
            out[dst] = row[src]
    return out


def extract(spec_root: Path) -> dict[str, Any]:
    commit = None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=spec_root, text=True).strip()
    except Exception:
        pass
    result: dict[str, Any] = {
        "source": "https://github.com/unified-font-object/ufo-spec",
        "commit": commit,
        "pages": {},
    }
    for page, rel in PAGES.items():
        path = spec_root / rel
        if not path.exists():
            continue
        tables = _parse_tables(path.read_text(encoding="utf-8"))
        sections: dict[str, dict[str, Any]] = {}
        for table in tables:
            cols = table["columns"]
            key_col = "key" if "key" in cols else "name" if "name" in cols else None
            if key_col is None or "description" not in cols:
                continue
            section = table["anchor"] or (table["headings"][-1] if table["headings"] else "root")
            # GLIF pages document attributes and child elements of an element
            # under the same anchor; keep them apart.
            kind = "children" if table["headings"] and table["headings"][-1].lower().startswith("child") else "attributes"
            bucket = sections.setdefault(section, {"headings": table["headings"], "attributes": {}, "children": {}})
            for row in table["rows"]:
                key = row.get(key_col, "").strip("`* ")
                if not key:
                    continue
                bucket[kind][key] = _entry(row)
        result["pages"][page] = sections
    return result


def flatten_fontinfo(docs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map fontinfo key -> {type, description} across every fontinfo section."""
    out: dict[str, dict[str, Any]] = {}
    for section, data in docs.get("pages", {}).get("fontinfo", {}).items():
        for key, entry in data["attributes"].items():
            out.setdefault(key, {**entry, "section": section})
    return out


def output_path() -> Path:
    return repo_root() / "sources" / "ufo-spec-docs.json"


def load_docs() -> dict[str, Any]:
    import json
    p = output_path()
    if not p.exists():
        return {"pages": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def refresh() -> Path:
    spec_root = source_path("ufo-spec")
    if spec_root is None:
        raise SystemExit("ufo-spec not found: run `git submodule update --init vendor/ufo-spec` or `fontschema sources sync`")
    docs = extract(spec_root)
    out = output_path()
    dump_json(docs, out)
    return out
