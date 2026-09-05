from __future__ import annotations

import plistlib
from types import SimpleNamespace
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from fontTools.ufoLib import UFOReader

VARIABLE_COMPONENTS_KEY = "com.black-foundry.variable-components"
GLYPH_DESIGNSPACE_KEY = "com.black-foundry.glyph-designspace"


def _plist_value(el: ET.Element) -> Any:
    if el.tag == "dict":
        out: dict[str, Any] = {}
        children = list(el)
        i = 0
        while i < len(children):
            key = children[i]
            if key.tag != "key" or i + 1 >= len(children):
                raise ValueError("malformed plist dict")
            out[key.text or ""] = _plist_value(children[i + 1])
            i += 2
        return out
    if el.tag == "array":
        return [_plist_value(x) for x in el]
    if el.tag == "string" or el.tag == "date" or el.tag == "data":
        return el.text or ""
    if el.tag == "integer":
        return int(el.text or "0")
    if el.tag == "real":
        return float(el.text or "0")
    if el.tag == "true":
        return True
    if el.tag == "false":
        return False
    raise ValueError(f"unsupported plist node {el.tag}")


def _read_glif(path: Path, glyph_name: str, layer_name: str) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    components = []
    outline = root.find("outline")
    if outline is not None:
        for c in outline.findall("component"):
            components.append({
                "base": c.attrib["base"],
                "transform": {
                    "xScale": float(c.attrib.get("xScale", 1)),
                    "xyScale": float(c.attrib.get("xyScale", 0)),
                    "yxScale": float(c.attrib.get("yxScale", 0)),
                    "yScale": float(c.attrib.get("yScale", 1)),
                    "xOffset": float(c.attrib.get("xOffset", 0)),
                    "yOffset": float(c.attrib.get("yOffset", 0)),
                },
                "identifier": c.attrib.get("identifier"),
            })
    anchors = [
        {"name": a.attrib.get("name"), "x": float(a.attrib["x"]), "y": float(a.attrib["y"]), "identifier": a.attrib.get("identifier")}
        for a in root.findall("anchor")
    ]
    lib: dict[str, Any] = {}
    lib_el = root.find("lib")
    if lib_el is not None and len(lib_el):
        lib = _plist_value(list(lib_el)[0])
    return {
        "name": glyph_name,
        "layer": layer_name,
        "file": str(path),
        "width": float(root.find("advance").attrib.get("width", 0)) if root.find("advance") is not None else None,
        "components": components,
        "anchors": anchors,
        "variableComponents": lib.get(VARIABLE_COMPONENTS_KEY, []),
        "glyphDesignspace": lib.get(GLYPH_DESIGNSPACE_KEY),
    }


def inspect(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    # UFOReader is used first as the structural parser/validator for the package.
    reader = UFOReader(path, validate=True)
    info = SimpleNamespace()
    reader.readInfo(info)
    layercontents_path = path / "layercontents.plist"
    if layercontents_path.exists():
        layercontents = plistlib.loads(layercontents_path.read_bytes())
    else:
        layercontents = [["public.default", "glyphs"]]
    glyphs: list[dict[str, Any]] = []
    for layer_name, directory in layercontents:
        glyph_dir = path / directory
        contents_path = glyph_dir / "contents.plist"
        if not contents_path.exists():
            continue
        contents = plistlib.loads(contents_path.read_bytes())
        for glyph_name, filename in contents.items():
            glyphs.append(_read_glif(glyph_dir / filename, glyph_name, layer_name))
    return {
        "path": str(path),
        "formatVersion": reader.formatVersionTuple.major,
        "glyphCount": len(glyphs),
        "glyphs": glyphs,
    }


def validate(path: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        data = inspect(path)
    except Exception as e:
        return {"path": str(path), "errors": [f"UFO parse failed: {e}"]}
    names = {g["name"] for g in data["glyphs"]}
    for g in data["glyphs"]:
        for c in g["components"]:
            if c["base"] not in names:
                errors.append(f"{g['name']}: component base {c['base']!r} not present in UFO")
        for c in g["variableComponents"]:
            base = c.get("base") if isinstance(c, dict) else None
            if not base:
                errors.append(f"{g['name']}: variable component missing base")
            elif base not in names:
                errors.append(f"{g['name']}: variable component base {base!r} not present in UFO")
    return {"path": str(path), "errors": errors, "normalized": data}
