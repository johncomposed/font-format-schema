from __future__ import annotations

from pathlib import Path
from typing import Any

from fontTools.designspaceLib import DesignSpaceDocument


def _location(loc: dict[str, Any] | None) -> dict[str, Any]:
    return dict(loc or {})


def inspect(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    doc = DesignSpaceDocument.fromfile(path)
    axes = []
    for a in doc.axes:
        row = {
            "name": a.name,
            "tag": a.tag,
            "default": a.default,
            "hidden": bool(a.hidden),
            "map": [list(pair) for pair in (a.map or [])],
        }
        if hasattr(a, "minimum"):
            row["minimum"] = getattr(a, "minimum", None)
            row["maximum"] = getattr(a, "maximum", None)
        if hasattr(a, "values") and getattr(a, "values", None):
            row["values"] = list(a.values)
        axes.append(row)
    mappings = [
        {
            "input": _location(m.inputLocation),
            "output": _location(m.outputLocation),
            "description": getattr(m, "description", None),
        }
        for m in doc.axisMappings
    ]
    sources = [
        {
            "name": s.name,
            "filename": s.filename,
            "layerName": s.layerName,
            "familyName": s.familyName,
            "styleName": s.styleName,
            "location": _location(s.location),
        }
        for s in doc.sources
    ]
    instances = [
        {
            "name": i.name,
            "filename": i.filename,
            "familyName": i.familyName,
            "styleName": i.styleName,
            "location": _location(i.location),
        }
        for i in doc.instances
    ]
    return {
        "path": str(path),
        "formatVersion": str(doc.formatVersion),
        "axes": axes,
        "mappings": mappings,
        "sources": sources,
        "instances": instances,
        "rules": [
            {
                "name": r.name,
                "conditionSets": r.conditionSets,
                "subs": [list(x) for x in r.subs],
            }
            for r in doc.rules
        ],
    }


def validate(path: str | Path) -> dict[str, Any]:
    data = inspect(path)
    errors: list[str] = []
    names = {a["name"] for a in data["axes"]}
    defaults = {a["name"]: a["default"] for a in data["axes"]}
    for m_i, mapping in enumerate(data["mappings"]):
        for side in ("input", "output"):
            unknown = set(mapping[side]) - names
            if unknown:
                errors.append(f"mapping {m_i} {side} contains unknown axes: {sorted(unknown)}")
    for s_i, source in enumerate(data["sources"]):
        unknown = set(source["location"]) - names
        if unknown:
            errors.append(f"source {s_i} contains unknown axes: {sorted(unknown)}")
    # The default master should exist at the all-axis default location for a normal VF designspace.
    if data["sources"]:
        has_default = any(all(s["location"].get(n, defaults[n]) == defaults[n] for n in names) for s in data["sources"])
        if not has_default:
            errors.append("no source resolves to the all-axis default location")
    return {"path": str(path), "errors": errors, "normalized": data}
