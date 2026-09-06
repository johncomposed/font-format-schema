"""Convert TTX XML into the JSON model described by ``schemas/ttx.schema.json``.

The mapping is intentionally simple and documented per table so it can be
re-implemented in another language (the TypeScript side of this project):

* attribute/element values are parsed with :func:`parse_value` — decimal and
  hex integers, floats, ``[...]`` lists, and fontTools binary strings
  (``"00000000 00000011"``) all become numbers;
* repeated XML elements become arrays; elements keyed by an attribute
  (``glyph=``, ``axis=``, ``name=``) become objects keyed by that attribute;
* otData driven tables are converted generically by :func:`ot_table_to_json`.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET

from fontTools.ttLib import xmlToTag

from ..xmlast import element_to_ast
from ..schema.ttx import SSTRUCT_FORMATS, TTX_STRING_FIELDS, parse_sstruct

BINARY_RE = re.compile(r"^[01]{8}( [01]{8})*$")


def parse_value(text: str | None) -> Any:
    """Parse a TTX scalar the way fontTools' ``safeEval`` does, plus binary strings."""
    if text is None:
        return None
    s = text.strip()
    if BINARY_RE.match(s):
        return int(s.replace(" ", ""), 2)
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return s


def _int(text: str | None, default: int | None = None) -> Any:
    """Integer when the text is integral; falls through to the parsed value otherwise."""
    v = parse_value(text)
    if v is None:
        return default
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _num(text: str | None) -> float | int | None:
    return parse_value(text)


def _bool(text: str | None, default: bool = False) -> bool:
    if text is None:
        return default
    v = parse_value(text)
    if isinstance(v, str):
        return v.lower() in {"true", "yes", "1"}
    return bool(v)


# ---------------------------------------------------------------------------
# generic otData tree


def ot_table_to_json(el: ET.Element) -> dict[str, Any]:
    """Generic conversion for tables serialised by fontTools' otConverters.

    * ``<Field value="x"/>`` -> ``{"Field": x}``
    * ``<Struct index="0">...</Struct>`` (or repeated tags) -> ``{"Struct": [...]}``
    * ``<Struct>...</Struct>`` -> ``{"Struct": {...}}``
    * a ``Format`` attribute on a struct element becomes a ``Format`` field.
    """
    out: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for child in el:
        counts[child.tag] = counts.get(child.tag, 0) + 1
    for child in el:
        is_array = "index" in child.attrib or counts[child.tag] > 1
        if len(child) == 0 and "value" in child.attrib:
            value: Any = parse_value(child.attrib["value"])
        elif len(child) == 0 and child.attrib.keys() - {"index", "Format"} and "value" not in child.attrib:
            # e.g. <Map glyph=".notdef" outer="0" inner="0"/> or <Glyph value=.../>
            value = {k: parse_value(v) for k, v in child.attrib.items() if k != "index"}
        else:
            value = ot_table_to_json(child)
            if "Format" in child.attrib:
                value = {"Format": parse_value(child.attrib["Format"]), **value}
            for k, v in child.attrib.items():
                if k not in {"index", "Format"}:
                    value.setdefault(k, parse_value(v))
        if is_array:
            out.setdefault(child.tag, []).append(value)
        else:
            out[child.tag] = value
    return out


# ---------------------------------------------------------------------------
# sstruct tables


def _sstruct_table(tag: str) -> Callable[[ET.Element], dict[str, Any]]:
    string_fields = {name for (t, name) in TTX_STRING_FIELDS if t == tag}

    def convert(el: ET.Element) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for child in el:
            if child.tag == "panose":
                out["panose"] = {c.tag: _int(c.attrib.get("value")) for c in child}
            elif child.tag == "psNames":
                out["psNames"] = {c.attrib["name"]: c.attrib["psName"] for c in child if c.tag == "psName"}
            elif child.tag == "extraNames":
                out["extraNames"] = [c.attrib["name"] for c in child if c.tag == "psName"]
            elif child.tag == "mapping":
                out["mapping"] = {c.attrib["name"]: _int(c.attrib.get("code")) for c in child if c.tag == "map"}
            elif "value" in child.attrib:
                raw = child.attrib["value"]
                out[child.tag] = raw if child.tag in string_fields else parse_value(raw)
        return out

    return convert


# ---------------------------------------------------------------------------
# hand written tables


def _glyph_order(el: ET.Element) -> list[str]:
    return [c.attrib["name"] for c in el if c.tag == "GlyphID"]


def _hmtx(el: ET.Element) -> list[dict[str, Any]]:
    return [{"name": c.attrib["name"], "width": _int(c.attrib["width"]), "lsb": _int(c.attrib["lsb"])} for c in el if c.tag == "mtx"]


def _vmtx(el: ET.Element) -> list[dict[str, Any]]:
    return [{"name": c.attrib["name"], "height": _int(c.attrib["height"]), "tsb": _int(c.attrib["tsb"])} for c in el if c.tag == "mtx"]


def _cmap(el: ET.Element) -> dict[str, Any]:
    out: dict[str, Any] = {"tableVersion": 0, "subtables": []}
    for child in el:
        if child.tag == "tableVersion":
            out["tableVersion"] = _int(child.attrib.get("version"), 0)
        elif child.tag.startswith("cmap_format_"):
            fmt = int(child.tag[len("cmap_format_"):])
            sub: dict[str, Any] = {
                "format": fmt,
                "platformID": _int(child.attrib["platformID"]),
                "platEncID": _int(child.attrib["platEncID"]),
                "language": _int(child.attrib.get("language"), 0),
            }
            if fmt == 14:
                uvs: dict[str, list] = {}
                for m in child:
                    if m.tag != "map":
                        continue
                    uv = str(_int(m.attrib["uvs"]))
                    name = m.attrib.get("name")
                    uvs.setdefault(uv, []).append([_int(m.attrib["uv"]), None if name in (None, "None") else name])
                sub["uvs"] = uvs
            else:
                sub["map"] = {str(_int(m.attrib["code"])): m.attrib["name"] for m in child if m.tag == "map"}
            out["subtables"].append(sub)
    return out


def _name(el: ET.Element) -> dict[str, Any]:
    records = []
    for c in el:
        if c.tag != "namerecord":
            continue
        rec: dict[str, Any] = {
            "nameID": _int(c.attrib["nameID"]),
            "platformID": _int(c.attrib["platformID"]),
            "platEncID": _int(c.attrib["platEncID"]),
            "langID": _int(c.attrib["langID"]),
            "text": (c.text or "").strip(),
        }
        if "unicode" in c.attrib:
            rec["unicode"] = _bool(c.attrib["unicode"])
        records.append(rec)
    return {"records": records}


def _glyf(el: ET.Element) -> dict[str, Any]:
    glyphs: dict[str, Any] = {}
    for g in el:
        if g.tag != "TTGlyph":
            continue
        glyph: dict[str, Any] = {"name": g.attrib["name"]}
        for k in ("xMin", "yMin", "xMax", "yMax"):
            if k in g.attrib:
                glyph[k] = _int(g.attrib[k])
        contours, components = [], []
        for c in g:
            if c.tag == "contour":
                points = []
                for p in c:
                    if p.tag != "pt":
                        continue
                    pt: dict[str, Any] = {"x": _int(p.attrib["x"]), "y": _int(p.attrib["y"]), "on": _bool(p.attrib.get("on"))}
                    if "overlap" in p.attrib:
                        pt["overlap"] = _bool(p.attrib["overlap"])
                    if "cubic" in p.attrib:
                        pt["cubic"] = _bool(p.attrib["cubic"])
                    points.append(pt)
                contours.append({"points": points})
            elif c.tag == "component":
                comp: dict[str, Any] = {"glyphName": c.attrib["glyphName"]}
                for k in ("x", "y", "firstPt", "secondPt"):
                    if k in c.attrib:
                        comp[k] = _int(c.attrib[k])
                for k in ("scale", "scalex", "scale01", "scale10", "scaley"):
                    if k in c.attrib:
                        comp[k] = _num(c.attrib[k])
                comp["flags"] = _int(c.attrib.get("flags"), 0)
                components.append(comp)
            elif c.tag == "instructions":
                asm = c.find("assembly")
                glyph["instructions"] = (asm.text or "").strip() if asm is not None else None
        if contours:
            glyph["contours"] = contours
        if components:
            glyph["components"] = components
        glyphs[glyph["name"]] = glyph
    return {"glyphs": glyphs}


def _cvt(el: ET.Element) -> list[Any]:
    return [_int(c.attrib["value"]) for c in el if c.tag == "cv"]


def _fvar(el: ET.Element) -> dict[str, Any]:
    axes, instances = [], []
    for c in el:
        if c.tag == "Axis":
            fields = {f.tag: (f.text or "").strip() for f in c}
            axes.append({
                "axisTag": fields["AxisTag"],
                "flags": _int(fields.get("Flags"), 0),
                "minValue": _num(fields["MinValue"]),
                "defaultValue": _num(fields["DefaultValue"]),
                "maxValue": _num(fields["MaxValue"]),
                "axisNameID": _int(fields["AxisNameID"]),
            })
        elif c.tag == "NamedInstance":
            inst: dict[str, Any] = {
                "flags": _int(c.attrib.get("flags"), 0),
                "subfamilyNameID": _int(c.attrib["subfamilyNameID"]),
                "coordinates": {k.attrib["axis"]: _num(k.attrib["value"]) for k in c if k.tag == "coord"},
            }
            if "postscriptNameID" in c.attrib:
                inst["postscriptNameID"] = _int(c.attrib["postscriptNameID"])
            instances.append(inst)
    return {"axes": axes, "instances": instances}


def _avar(el: ET.Element) -> dict[str, Any]:
    out: dict[str, Any] = {"version": {"major": 1, "minor": 0}, "segments": {}}
    for c in el:
        if c.tag == "version":
            out["version"] = {"major": _int(c.attrib.get("major"), 1), "minor": _int(c.attrib.get("minor"), 0)}
        elif c.tag == "segment":
            out["segments"][c.attrib["axis"]] = [
                {"from": _num(m.attrib["from"]), "to": _num(m.attrib["to"])} for m in c if m.tag == "mapping"
            ]
        elif c.tag in ("VarIdxMap", "VarStore"):
            table = ot_table_to_json(c)
            if "Format" in c.attrib:
                table = {"Format": parse_value(c.attrib["Format"]), **table}
            out[c.tag] = table
    return out


def _tuple(el: ET.Element) -> dict[str, Any]:
    axes: dict[str, Any] = {}
    deltas: list[dict[str, Any]] = []
    for c in el:
        if c.tag == "coord":
            axis: dict[str, Any] = {"value": _num(c.attrib["value"])}
            if "min" in c.attrib:
                axis["min"] = _num(c.attrib["min"])
            if "max" in c.attrib:
                axis["max"] = _num(c.attrib["max"])
            axes[c.attrib["axis"]] = axis
        elif c.tag == "delta":
            if "pt" in c.attrib:
                deltas.append({"pt": _int(c.attrib["pt"]), "x": _int(c.attrib["x"]), "y": _int(c.attrib["y"])})
            else:
                deltas.append({"cvt": _int(c.attrib["cvt"]), "value": _int(c.attrib["value"])})
    return {"axes": axes, "deltas": deltas}


def _gvar(el: ET.Element) -> dict[str, Any]:
    out: dict[str, Any] = {"version": 1, "reserved": 0, "glyphVariations": {}}
    for c in el:
        if c.tag == "version":
            out["version"] = _int(c.attrib["value"])
        elif c.tag == "reserved":
            out["reserved"] = _int(c.attrib["value"])
        elif c.tag == "glyphVariations":
            out["glyphVariations"][c.attrib["glyph"]] = [_tuple(t) for t in c if t.tag == "tuple"]
    return out


def _cvar(el: ET.Element) -> dict[str, Any]:
    out: dict[str, Any] = {"version": {"major": 1, "minor": 0}, "variations": []}
    for c in el:
        if c.tag == "version":
            out["version"] = {"major": _int(c.attrib.get("major"), 1), "minor": _int(c.attrib.get("minor"), 0)}
        elif c.tag == "tuple":
            out["variations"].append(_tuple(c))
    return out


CONVERTERS: dict[str, Callable[[ET.Element], Any]] = {
    "GlyphOrder": _glyph_order,
    "head": _sstruct_table("head"),
    "hhea": _sstruct_table("hhea"),
    "vhea": _sstruct_table("vhea"),
    "maxp": _sstruct_table("maxp"),
    "OS_2": _sstruct_table("OS/2"),
    "post": _sstruct_table("post"),
    "hmtx": _hmtx,
    "vmtx": _vmtx,
    "cmap": _cmap,
    "name": _name,
    "glyf": _glyf,
    "loca": lambda el: {},
    "cvt": _cvt,
    "fvar": _fvar,
    "avar": _avar,
    "gvar": _gvar,
    "cvar": _cvar,
}
OTDATA_TABLES = {"STAT", "HVAR", "VVAR", "MVAR", "VARC", "GDEF", "GSUB", "GPOS", "BASE"}


def ttx_to_json(root: ET.Element) -> dict[str, Any]:
    if root.tag != "ttFont":
        raise ValueError(f"expected <ttFont>, got <{root.tag}>")
    out: dict[str, Any] = {"sfntVersion": root.attrib.get("sfntVersion", "\\x00\\x01\\x00\\x00")}
    if "ttLibVersion" in root.attrib:
        out["ttLibVersion"] = root.attrib["ttLibVersion"]
    out["GlyphOrder"] = []
    for table in root:
        name = table.tag
        if name in CONVERTERS:
            out[name] = CONVERTERS[name](table)
        elif name in OTDATA_TABLES:
            out[name] = ot_table_to_json(table)
        else:
            out.setdefault("tables", {})[name] = element_to_ast(table)
    return out


def ttx_file_to_json(path: str | Path) -> dict[str, Any]:
    return ttx_to_json(ET.parse(path).getroot())


def table_tag(xml_name: str) -> str:
    """TTX element name -> 4 byte table tag (e.g. 'OS_2' -> 'OS/2')."""
    return xmlToTag(xml_name)
