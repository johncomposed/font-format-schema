"""Read a Designspace document into the JSON model of ``schemas/designspace.schema.json``."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    DiscreteAxisDescriptor,
    RangeAxisSubsetDescriptor,
    ValueAxisSubsetDescriptor,
)


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    """Drop None values and empty containers so the JSON mirrors the XML."""
    return {k: v for k, v in d.items() if v is not None and v != {} and v != []}


def _location(loc: dict[str, Any] | None) -> dict[str, Any]:
    return dict(loc or {})


def _axis_label(label: Any) -> dict[str, Any]:
    return _clean(
        {
            "name": label.name,
            "userValue": label.userValue,
            "userMinimum": label.userMinimum,
            "userMaximum": label.userMaximum,
            "elidable": label.elidable,
            "olderSibling": label.olderSibling,
            "linkedUserValue": label.linkedUserValue,
            "labelNames": dict(label.labelNames or {}),
        }
    )


def _axis(a: AxisDescriptor | DiscreteAxisDescriptor) -> dict[str, Any]:
    row: dict[str, Any] = {
        "tag": a.tag,
        "name": a.name,
        "labelNames": dict(a.labelNames or {}),
        "hidden": bool(a.hidden),
        "map": [[float(i), float(o)] for i, o in (a.map or [])],
        "axisOrdering": a.axisOrdering,
        "axisLabels": [_axis_label(l) for l in (a.axisLabels or [])],
    }
    if isinstance(a, DiscreteAxisDescriptor):
        row["values"] = list(a.values)
        row["default"] = a.default
    else:
        row["minimum"] = a.minimum
        row["default"] = a.default
        row["maximum"] = a.maximum
    return _clean(row)


def _source(s: Any) -> dict[str, Any]:
    return _clean(
        {
            "filename": s.filename,
            "name": s.name,
            "layerName": s.layerName,
            "location": _location(s.location),
            "familyName": s.familyName,
            "styleName": s.styleName,
            "localisedFamilyName": dict(s.localisedFamilyName or {}),
            "copyLib": s.copyLib or None,
            "copyGroups": s.copyGroups or None,
            "copyFeatures": s.copyFeatures or None,
            "muteKerning": s.muteKerning or None,
            "muteInfo": s.muteInfo or None,
            "mutedGlyphNames": list(s.mutedGlyphNames or []),
        }
    )


def _instance(i: Any) -> dict[str, Any]:
    return _clean(
        {
            "filename": i.filename,
            "name": i.name,
            "locationLabel": i.locationLabel,
            "designLocation": _location(i.designLocation),
            "userLocation": _location(i.userLocation),
            "familyName": i.familyName,
            "styleName": i.styleName,
            "postScriptFontName": i.postScriptFontName,
            "styleMapFamilyName": i.styleMapFamilyName,
            "styleMapStyleName": i.styleMapStyleName,
            "localisedFamilyName": dict(i.localisedFamilyName or {}),
            "localisedStyleName": dict(i.localisedStyleName or {}),
            "localisedStyleMapFamilyName": dict(i.localisedStyleMapFamilyName or {}),
            "localisedStyleMapStyleName": dict(i.localisedStyleMapStyleName or {}),
            "glyphs": dict(i.glyphs or {}),
            "kerning": None if i.kerning else False,
            "info": None if i.info else False,
            "lib": dict(i.lib or {}),
        }
    )


def _rule(r: Any) -> dict[str, Any]:
    return _clean(
        {
            "name": r.name,
            "conditionSets": [
                [_clean({"name": c["name"], "minimum": c.get("minimum"), "maximum": c.get("maximum")}) for c in cs]
                for cs in r.conditionSets
            ],
            "subs": [[a, b] for a, b in r.subs],
        }
    )


def _variable_font(vf: Any) -> dict[str, Any]:
    subsets = []
    for s in vf.axisSubsets:
        if isinstance(s, ValueAxisSubsetDescriptor):
            subsets.append({"name": s.name, "userValue": s.userValue})
        elif isinstance(s, RangeAxisSubsetDescriptor):
            subsets.append(
                _clean({"name": s.name, "userMinimum": s.userMinimum, "userDefault": s.userDefault, "userMaximum": s.userMaximum})
            )
    return _clean({"name": vf.name, "filename": vf.filename, "axisSubsets": subsets, "lib": dict(vf.lib or {})})


def inspect(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    doc = DesignSpaceDocument.fromfile(path)
    return _clean(
        {
            "path": str(path),
            "formatVersion": str(doc.formatVersion),
            "axes": [_axis(a) for a in doc.axes],
            "axisMappings": [
                _clean(
                    {
                        "inputLocation": _location(m.inputLocation),
                        "outputLocation": _location(m.outputLocation),
                        "description": m.description,
                        "groupDescription": m.groupDescription,
                    }
                )
                for m in doc.axisMappings
            ],
            "locationLabels": [
                _clean(
                    {
                        "name": l.name,
                        "elidable": l.elidable or None,
                        "olderSibling": l.olderSibling or None,
                        "userLocation": _location(l.userLocation),
                        "labelNames": dict(l.labelNames or {}),
                    }
                )
                for l in doc.locationLabels
            ],
            "sources": [_source(s) for s in doc.sources],
            "variableFonts": [_variable_font(v) for v in doc.variableFonts],
            "instances": [_instance(i) for i in doc.instances],
            "rules": [_rule(r) for r in doc.rules],
            "rulesProcessingLast": doc.rulesProcessingLast or None,
            "lib": dict(doc.lib or {}),
        }
    )


def validate(path: str | Path) -> dict[str, Any]:
    data = inspect(path)
    errors: list[str] = []
    axes = {a["name"]: a for a in data["axes"]}
    names = set(axes)
    defaults = {n: a["default"] for n, a in axes.items()}
    for a in data["axes"]:
        if "values" in a:
            if a["default"] not in a["values"]:
                errors.append(f"axis {a['name']}: default {a['default']} is not one of its discrete values")
        elif not (a["minimum"] <= a["default"] <= a["maximum"]):
            errors.append(f"axis {a['name']}: default {a['default']} outside [{a['minimum']}, {a['maximum']}]")
        if a.get("map"):
            inputs = [i for i, _ in a["map"]]
            if inputs != sorted(inputs):
                errors.append(f"axis {a['name']}: map inputs are not sorted")
    for m_i, mapping in enumerate(data.get("axisMappings", [])):
        for side in ("inputLocation", "outputLocation"):
            unknown = set(mapping[side]) - names
            if unknown:
                errors.append(f"mapping {m_i} {side} contains unknown axes: {sorted(unknown)}")
    for s_i, source in enumerate(data["sources"]):
        unknown = set(source["location"]) - names
        if unknown:
            errors.append(f"source {s_i} contains unknown axes: {sorted(unknown)}")
    for r in data.get("rules", []):
        for cs in r["conditionSets"]:
            for c in cs:
                if c["name"] not in names:
                    errors.append(f"rule {r.get('name')}: condition on unknown axis {c['name']!r}")
    if data["sources"]:
        # Sources are in design coordinates; compare against the mapped default.
        def design_default(name: str) -> float:
            a = axes[name]
            for i, o in a.get("map", []):
                if i == a["default"]:
                    return o
            return a["default"]

        has_default = any(
            all(s["location"].get(n, design_default(n)) == design_default(n) for n in names) for s in data["sources"]
        )
        if not has_default:
            errors.append("no source resolves to the all-axis default location")
    return {"path": str(path), "errors": errors, "normalized": data}
