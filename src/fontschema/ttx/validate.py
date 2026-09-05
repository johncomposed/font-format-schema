from __future__ import annotations

import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools.ttLib import TTFont


def _validate_font(font: TTFont) -> list[str]:
    errors: list[str] = []
    axis_count = 0
    if "fvar" in font:
        axes = font["fvar"].axes
        axis_count = len(axes)
        tags = [a.axisTag for a in axes]
        if len(tags) != len(set(tags)):
            errors.append("fvar axis tags are not unique")
        for a in axes:
            if not (a.minValue <= a.defaultValue <= a.maxValue):
                errors.append(f"fvar {a.axisTag}: default is outside min/max")

    if "VARC" in font:
        table = font["VARC"].table
        ail = getattr(table, "AxisIndicesList", None)
        axis_items = list(getattr(ail, "Item", []) or []) if ail else []
        for i, item in enumerate(axis_items):
            for axis_index in item:
                if axis_count and axis_index >= axis_count:
                    errors.append(f"VARC AxisIndicesList[{i}] contains axis {axis_index} >= fvar axis count {axis_count}")
        vcg = getattr(table, "VarCompositeGlyphs", None)
        glyphs = list(getattr(vcg, "VarCompositeGlyph", []) or []) if vcg else []
        coverage = getattr(table, "Coverage", None)
        cov_glyphs = list(getattr(coverage, "glyphs", []) or []) if coverage else []
        if cov_glyphs and len(cov_glyphs) != len(glyphs):
            errors.append("VARC Coverage glyph count does not match VarCompositeGlyph count")
        for gi, glyph in enumerate(glyphs):
            for ci, comp in enumerate(getattr(glyph, "components", []) or []):
                idx = getattr(comp, "axisIndicesIndex", None)
                values = tuple(getattr(comp, "axisValues", ()) or ())
                if idx is not None:
                    if idx >= len(axis_items):
                        errors.append(f"VARC glyph {gi} component {ci}: axisIndicesIndex {idx} out of range")
                    elif len(values) != len(axis_items[idx]):
                        errors.append(f"VARC glyph {gi} component {ci}: axisValues length {len(values)} != axis index tuple length {len(axis_items[idx])}")
    return errors


def validate(path: str | Path) -> dict[str, object]:
    path = Path(path)
    result: dict[str, object] = {"path": str(path), "errors": [], "roundTrip": None}
    errors: list[str] = result["errors"]  # type: ignore[assignment]
    if path.suffix.lower() == ".ttx" or path.suffix.lower() == ".xml":
        try:
            ET.parse(path)
        except Exception as e:
            errors.append(f"XML parse failed: {e}")
            return result
        try:
            font = TTFont()
            font.importXML(path)
            with tempfile.NamedTemporaryFile(suffix=".ttf") as tmp:
                font.save(tmp.name)
                reopened = TTFont(tmp.name, lazy=False)
                errors.extend(_validate_font(reopened))
            result["roundTrip"] = True
        except Exception as e:
            result["roundTrip"] = False
            errors.append(f"fontTools TTX compile/round-trip failed: {e}")
    else:
        try:
            font = TTFont(path, lazy=False)
            errors.extend(_validate_font(font))
            result["roundTrip"] = True
        except Exception as e:
            errors.append(f"fontTools font load failed: {e}")
            result["roundTrip"] = False
    return result
