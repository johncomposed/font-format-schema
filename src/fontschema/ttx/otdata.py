from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from typing import Any

from fontTools.ttLib import getTableClass
from fontTools.ttLib.tables import otData

# Top-level tables plus shared variation data structures worth keeping even if
# fontTools' generic Offset fields make graph traversal ambiguous.
ROOTS = [
    "avar", "AxisSegmentMap", "VarIdxMap",
    "HVAR", "VVAR", "MVAR", "VARC", "STAT",
    "FeatureVariations", "ConditionList", "ConditionSet",
    "VarStore", "VarRegionList", "VarRegion", "VarRegionAxis", "VarData",
    "DeltaSetIndexMapFormat0", "DeltaSetIndexMapFormat1",
    "MultiVarStore", "MultiVarData", "SparseVarRegionList", "SparseVarRegion", "SparseVarRegionAxis",
    "AxisIndicesList", "VarCompositeGlyphs",
]

TABLE_TAGS = ["fvar", "avar", "STAT", "gvar", "cvar", "HVAR", "VVAR", "MVAR", "VARC", "CFF2", "GDEF", "GPOS", "GSUB", "BASE"]


def _field_dict(field: Any) -> dict[str, Any]:
    if is_dataclass(field):
        return asdict(field)
    if hasattr(field, "_asdict"):
        return field._asdict()
    return {
        "type": getattr(field, "type", None),
        "name": getattr(field, "name", None),
        "repeat": getattr(field, "repeat", None),
        "aux": getattr(field, "aux", None),
        "description": getattr(field, "description", ""),
    }


def definitions() -> dict[str, list[Any]]:
    return {name: fields for name, fields in otData.otData}


def _type_ref(type_name: str, defs: set[str]) -> str | None:
    if type_name in defs:
        return type_name
    m = re.search(r"(?:OffsetTo|LOffsetTo)\(([^)]+)\)", type_name)
    if m and m.group(1) in defs:
        return m.group(1)
    return None


def extract_variation_otdata() -> dict[str, Any]:
    defs = definitions()
    names = set(defs)
    keep = set(n for n in ROOTS if n in defs)
    queue = list(keep)
    while queue:
        name = queue.pop()
        for field in defs.get(name, []):
            ref = _type_ref(getattr(field, "type", ""), names)
            if ref and ref not in keep:
                keep.add(ref)
                queue.append(ref)
            # `struct` fields conventionally refer to a definition named after the field.
            if getattr(field, "type", None) == "struct":
                candidate = getattr(field, "name", "")
                if candidate in names and candidate not in keep:
                    keep.add(candidate)
                    queue.append(candidate)
    return {
        "fontToolsVersion": __import__("fontTools").__version__,
        "roots": ROOTS,
        "definitions": {
            name: [_field_dict(f) for f in defs[name]]
            for name in sorted(keep)
        },
        "notes": [
            "This is fontTools otData metadata, not a normative TTX XSD.",
            "Generic Offset/LOffset fields can resolve to structures using converter context; custom XML handlers can differ from this metadata.",
        ],
    }


def table_inventory() -> dict[str, Any]:
    rows = []
    custom = {"fvar", "gvar", "cvar", "CFF2"}
    hybrid = {"avar", "VARC"}
    defs = definitions()
    for tag in TABLE_TAGS:
        cls = getTableClass(tag)
        if tag in custom:
            serialization = "custom/table-specific"
        elif tag in hybrid:
            serialization = "hybrid: otData + custom XML/substructures"
        elif tag in defs:
            serialization = "otData/generated"
        else:
            serialization = "custom/table-specific"
        rows.append({
            "tag": tag,
            "class": f"{cls.__module__}.{cls.__name__}",
            "otDataRoot": tag if tag in defs else None,
            "serialization": serialization,
        })
    return {"fontToolsVersion": __import__("fontTools").__version__, "tables": rows}


SCALAR_NUMBER_TYPES = {
    "uint8", "int8", "uint16", "int16", "uint24", "uint32", "int32",
    "F2Dot14", "Fixed", "Version", "NameID", "GlyphID", "DeciPoints",
}


def _schema_for_type(type_name: str, defs: set[str], field_name: str) -> dict[str, Any]:
    ref = _type_ref(type_name, defs)
    if ref:
        return {"$ref": f"#/$defs/{ref}", "x-fonttools-type": type_name}
    if type_name in SCALAR_NUMBER_TYPES:
        return {"type": "number", "x-fonttools-type": type_name}
    if type_name in {"Tag", "GlyphName"}:
        return {"type": "string", "x-fonttools-type": type_name}
    if type_name in {"Offset", "LOffset"}:
        # Converter context determines the target. Keep it open rather than lying.
        return {"x-fonttools-type": type_name, "description": f"Context-dependent offset target for {field_name}"}
    return {"x-fonttools-type": type_name}


def otdata_json_schema(meta: dict[str, Any]) -> dict[str, Any]:
    defs = set(meta["definitions"])
    out_defs: dict[str, Any] = {}
    for name, fields in meta["definitions"].items():
        props: dict[str, Any] = {}
        required: list[str] = []
        for f in fields:
            schema = _schema_for_type(f.get("type") or "", defs, f.get("name") or "")
            if f.get("repeat") not in (None, ""):
                schema = {"type": "array", "items": schema, "x-fonttools-repeat": f.get("repeat")}
            if f.get("description"):
                schema = {**schema, "description": f["description"]}
            props[f["name"]] = schema
            if not f.get("aux"):
                required.append(f["name"])
        out_defs[name] = {
            "type": "object",
            "properties": props,
            "required": required,
            "additionalProperties": True,
        }
    roots = [r for r in meta["roots"] if r in out_defs]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:ttx-otdata-variation",
        "title": "fontTools variation-oriented otData semantic structures",
        "oneOf": [{"$ref": f"#/$defs/{r}"} for r in roots],
        "$defs": out_defs,
    }


def _ts_type(type_name: str, defs: set[str]) -> str:
    ref = _type_ref(type_name, defs)
    if ref:
        return ref
    if type_name in SCALAR_NUMBER_TYPES:
        return "number"
    if type_name in {"Tag", "GlyphName"}:
        return "string"
    return "unknown"


def otdata_typescript(meta: dict[str, Any]) -> str:
    defs = set(meta["definitions"])
    lines = [
        "// Generated from fontTools otData.py. Semantic structure metadata, not an exact TTX DOM.\n",
        f"// fontTools {meta['fontToolsVersion']}\n\n",
    ]
    for name, fields in meta["definitions"].items():
        lines.append(f"export interface {name} {{\n")
        for f in fields:
            typ = _ts_type(f.get("type") or "", defs)
            if f.get("repeat") not in (None, ""):
                typ += "[]"
            optional = "?" if f.get("aux") else ""
            desc = (f.get("description") or "").replace("*/", "* /")
            if desc:
                lines.append(f"  /** {desc} | fontTools type: {f.get('type')} */\n")
            else:
                lines.append(f"  /** fontTools type: {f.get('type')} */\n")
            lines.append(f"  {f['name']}{optional}: {typ};\n")
        lines.append("}\n\n")
    return "".join(lines)
