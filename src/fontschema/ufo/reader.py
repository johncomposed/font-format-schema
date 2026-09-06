"""Read a UFO 3 package into the JSON model of ``schemas/ufo.schema.json``.

``fontTools.ufoLib.UFOReader`` validates the package structure and reads the
plists; GLIF files are parsed directly so that every attribute the format
allows (point types, smooth flags, identifiers, image transforms, ...) ends
up in the JSON without going through a pen.
"""
from __future__ import annotations

import plistlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

from fontTools.ufoLib import UFOReader

from ..schema.ufo import GLYPH_DESIGNSPACE_KEY, POINT_TYPES, TRANSFORM_ATTRS, VARIABLE_COMPONENTS_KEY


# ---------------------------------------------------------------------------
# plist helpers


def _plist_value(el: ET.Element) -> Any:
    """Convert an XML plist element tree (as embedded in GLIF <lib>) to Python."""
    if el.tag == "dict":
        out: dict[str, Any] = {}
        children = list(el)
        for i in range(0, len(children) - 1, 2):
            key = children[i]
            if key.tag != "key":
                raise ValueError("malformed plist dict")
            out[key.text or ""] = _plist_value(children[i + 1])
        return out
    if el.tag == "array":
        return [_plist_value(x) for x in el]
    if el.tag in ("string", "date", "data"):
        return (el.text or "").strip() if el.tag != "string" else (el.text or "")
    if el.tag == "integer":
        return int(el.text or "0")
    if el.tag == "real":
        return float(el.text or "0")
    if el.tag == "true":
        return True
    if el.tag == "false":
        return False
    raise ValueError(f"unsupported plist node {el.tag}")


def _jsonable(value: Any) -> Any:
    """plistlib output -> JSON friendly (bytes/dates become strings)."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, bytes):
        import base64

        return base64.b64encode(value).decode("ascii")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _num(text: str) -> float | int:
    f = float(text)
    return int(f) if f.is_integer() and "." not in text else f


# ---------------------------------------------------------------------------
# GLIF


def _transform(attrib: dict[str, str]) -> dict[str, Any]:
    return {k: _num(attrib[k]) for k in TRANSFORM_ATTRS if k in attrib}


def _guideline(attrib: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("x", "y", "angle"):
        if k in attrib:
            out[k] = _num(attrib[k])
    for k in ("name", "color", "identifier"):
        if k in attrib:
            out[k] = attrib[k]
    return out


def _point(el: ET.Element) -> dict[str, Any]:
    a = el.attrib
    pt: dict[str, Any] = {"x": _num(a["x"]), "y": _num(a["y"]), "type": a.get("type", "offcurve")}
    if pt["type"] not in POINT_TYPES:
        raise ValueError(f"unknown point type {pt['type']!r}")
    if "smooth" in a:
        pt["smooth"] = a["smooth"] == "yes"
    if "name" in a:
        pt["name"] = a["name"]
    if "identifier" in a:
        pt["identifier"] = a["identifier"]
    return pt


def read_glif(path: Path) -> dict[str, Any]:
    """Parse one GLIF file into a ``Glyph`` object."""
    root = ET.parse(path).getroot()
    if root.tag != "glyph":
        raise ValueError(f"{path}: not a GLIF file")
    glyph: dict[str, Any] = {"name": root.attrib["name"], "format": int(root.attrib.get("format", "1"))}
    if "formatMinor" in root.attrib:
        glyph["formatMinor"] = int(root.attrib["formatMinor"])
    unicodes: list[dict[str, str]] = []
    guidelines: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []
    for el in root:
        if el.tag == "advance":
            adv: dict[str, Any] = {}
            for k in ("width", "height"):
                if k in el.attrib:
                    adv[k] = _num(el.attrib[k])
            glyph["advance"] = adv
        elif el.tag == "unicode":
            unicodes.append({"hex": el.attrib["hex"]})
        elif el.tag == "note":
            glyph["note"] = (el.text or "").strip()
        elif el.tag == "image":
            img: dict[str, Any] = {"fileName": el.attrib["fileName"], **_transform(el.attrib)}
            if "color" in el.attrib:
                img["color"] = el.attrib["color"]
            glyph["image"] = img
        elif el.tag == "guideline":
            guidelines.append(_guideline(el.attrib))
        elif el.tag == "anchor":
            anc: dict[str, Any] = {"x": _num(el.attrib["x"]), "y": _num(el.attrib["y"])}
            for k in ("name", "color", "identifier"):
                if k in el.attrib:
                    anc[k] = el.attrib[k]
            anchors.append(anc)
        elif el.tag == "outline":
            contours, components = [], []
            for child in el:
                if child.tag == "contour":
                    contour: dict[str, Any] = {}
                    if "identifier" in child.attrib:
                        contour["identifier"] = child.attrib["identifier"]
                    contour["points"] = [_point(p) for p in child if p.tag == "point"]
                    contours.append(contour)
                elif child.tag == "component":
                    comp: dict[str, Any] = {"base": child.attrib["base"], **_transform(child.attrib)}
                    if "identifier" in child.attrib:
                        comp["identifier"] = child.attrib["identifier"]
                    components.append(comp)
            outline: dict[str, Any] = {}
            if contours:
                outline["contours"] = contours
            if components:
                outline["components"] = components
            glyph["outline"] = outline
        elif el.tag == "lib":
            if len(el):
                glyph["lib"] = _plist_value(list(el)[0])
    if unicodes:
        glyph["unicodes"] = unicodes
    if guidelines:
        glyph["guidelines"] = guidelines
    if anchors:
        glyph["anchors"] = anchors
    return glyph


# ---------------------------------------------------------------------------
# package


def _read_plist(path: Path) -> Any:
    return _jsonable(plistlib.loads(path.read_bytes())) if path.exists() else None


def inspect(path: str | Path) -> dict[str, Any]:
    """Read a UFO into a ``UfoPackage`` JSON object."""
    path = Path(path)
    reader = UFOReader(path, validate=True)  # structural validation of the package
    info = SimpleNamespace()
    reader.readInfo(info)

    metainfo = _read_plist(path / "metainfo.plist") or {"formatVersion": reader.formatVersion}
    layercontents = _read_plist(path / "layercontents.plist") or [["public.default", "glyphs"]]

    package: dict[str, Any] = {"path": str(path), "metainfo": metainfo}
    fontinfo = {k: v for k, v in vars(info).items() if v is not None}
    if fontinfo:
        package["fontinfo"] = _jsonable(fontinfo)
    groups = _read_plist(path / "groups.plist")
    if groups is not None:
        package["groups"] = groups
    kerning = _read_plist(path / "kerning.plist")
    if kerning is not None:
        package["kerning"] = kerning
    features = path / "features.fea"
    if features.exists():
        package["features"] = features.read_text(encoding="utf-8")
    lib = _read_plist(path / "lib.plist")
    if lib is not None:
        package["lib"] = lib
    package["layercontents"] = layercontents

    layers = []
    for layer_name, directory in layercontents:
        glyph_dir = path / directory
        layer: dict[str, Any] = {"name": layer_name, "directory": directory}
        layerinfo = _read_plist(glyph_dir / "layerinfo.plist")
        if layerinfo is not None:
            layer["layerinfo"] = layerinfo
        contents = _read_plist(glyph_dir / "contents.plist") or {}
        layer["contents"] = contents
        layer["glyphs"] = {name: read_glif(glyph_dir / filename) for name, filename in contents.items()}
        layers.append(layer)
    package["layers"] = layers

    images = path / "images"
    if images.is_dir():
        package["images"] = sorted(p.name for p in images.iterdir() if p.is_file())
    data = path / "data"
    if data.is_dir():
        package["data"] = sorted(str(p.relative_to(data)).replace("\\", "/") for p in data.rglob("*") if p.is_file())
    return package


# ---------------------------------------------------------------------------
# semantic validation


def _check_contour(glyph: str, index: int, points: list[dict[str, Any]], errors: list[str]) -> None:
    if not points:
        return
    types = [p.get("type", "offcurve") for p in points]
    for i, t in enumerate(types):
        if t == "move" and i != 0:
            errors.append(f"{glyph}: contour {index} has a move point at position {i}; move must be first")
    open_contour = types[0] == "move"
    n = len(types)
    # Count off-curve points preceding each on-curve point (cyclic for closed contours).
    for i, t in enumerate(types):
        if t == "offcurve":
            continue
        run = 0
        j = i - 1
        while (j >= 0 or not open_contour) and types[j % n] == "offcurve" and run < n:
            run += 1
            j -= 1
        if t in ("line", "move") and run:
            errors.append(f"{glyph}: contour {index} point {i} is a {t} preceded by {run} offcurve point(s)")
        if t == "curve" and run > 2:
            errors.append(f"{glyph}: contour {index} point {i} is a curve preceded by {run} offcurve points (max 2)")
        if t == "offcurve" and points[i].get("smooth"):
            errors.append(f"{glyph}: contour {index} point {i} is offcurve but smooth")
    if all(t == "offcurve" for t in types) and open_contour:
        errors.append(f"{glyph}: contour {index} is open but has only offcurve points")


def validate(path: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        data = inspect(path)
    except Exception as e:  # noqa: BLE001
        return {"path": str(path), "errors": [f"UFO parse failed: {e}"]}
    for layer in data["layers"]:
        names = set(layer["glyphs"])
        for name, glyph in layer["glyphs"].items():
            outline = glyph.get("outline", {})
            for ci, contour in enumerate(outline.get("contours", [])):
                _check_contour(name, ci, contour["points"], errors)
            for comp in outline.get("components", []):
                if comp["base"] not in names:
                    errors.append(f"{name}: component base {comp['base']!r} not present in layer {layer['name']!r}")
            lib = glyph.get("lib", {})
            for vc in lib.get(VARIABLE_COMPONENTS_KEY, []):
                base = vc.get("base") if isinstance(vc, dict) else None
                if not base:
                    errors.append(f"{name}: variable component missing base")
                elif base not in names:
                    errors.append(f"{name}: variable component base {base!r} not present in layer {layer['name']!r}")
            ds = lib.get(GLYPH_DESIGNSPACE_KEY)
            if isinstance(ds, dict):
                axis_names = {a.get("name") for a in ds.get("axes", [])}
                for src in ds.get("sources", []):
                    if src.get("layername") and src["layername"] not in {l["name"] for l in data["layers"]}:
                        errors.append(f"{name}: glyph designspace source references unknown layer {src['layername']!r}")
                    for axis in src.get("location", {}):
                        if axis not in axis_names:
                            # Global axes are allowed here; only flag if there are no global axes to check against.
                            pass
            identifiers: list[str] = []
            for contour in outline.get("contours", []):
                identifiers += [contour[k] for k in ("identifier",) if k in contour]
                identifiers += [p["identifier"] for p in contour["points"] if "identifier" in p]
            identifiers += [c["identifier"] for c in outline.get("components", []) if "identifier" in c]
            identifiers += [a["identifier"] for a in glyph.get("anchors", []) if "identifier" in a]
            identifiers += [g["identifier"] for g in glyph.get("guidelines", []) if "identifier" in g]
            if len(identifiers) != len(set(identifiers)):
                errors.append(f"{name}: duplicate object identifiers")
    return {"path": str(path), "errors": errors, "normalized": data}
