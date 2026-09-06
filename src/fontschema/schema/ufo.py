"""JSON Schema for the UFO 3 package model.

Sources of truth, in order:

1. ``fontTools.ufoLib`` (pinned) — ``fontInfoAttributesVersion3ValueData`` gives
   the complete fontinfo key list plus the Python value type and the validator
   function bound to each key; ``glifLib`` gives the GLIF attribute sets.
2. ``sources/ufo-spec-docs.json`` — attribute tables extracted verbatim from the
   UFO specification (``fontschema spec extract``) for descriptions, declared
   types and defaults.
3. ``vendor/variable-components-in-ufo`` — the glyph.lib extension used by
   Fontra for variable components and glyph-local designspaces.

The JSON model mirrors the XML/plist structures: repeated XML elements become
plural arrays (``points``, ``contours``...), attribute names are kept verbatim,
and ``yes``/``no`` flags become booleans.
"""
from __future__ import annotations

from typing import Any

from fontTools.ufoLib import fontInfoAttributesVersion3ValueData as FONTINFO_V3
from fontTools.ufoLib import glifLib

from ..spec.ufospec import flatten_fontinfo, load_docs
from . import js

VARIABLE_COMPONENTS_KEY = "com.black-foundry.variable-components"
GLYPH_DESIGNSPACE_KEY = "com.black-foundry.glyph-designspace"

POINT_TYPES = ["move", "line", "offcurve", "curve", "qcurve"]
TRANSFORM_ATTRS = ["xScale", "xyScale", "yxScale", "yScale", "xOffset", "yOffset"]
TRANSFORM_DEFAULTS = {"xScale": 1, "xyScale": 0, "yxScale": 0, "yScale": 1, "xOffset": 0, "yOffset": 0}


# ---------------------------------------------------------------------------
# spec docs access


def _glif_attr(docs: dict[str, Any], element: str, attr: str) -> dict[str, Any]:
    return docs.get("pages", {}).get("glif", {}).get(element, {}).get("attributes", {}).get(attr, {})


def _glif_desc(docs: dict[str, Any], element: str, attr: str) -> str | None:
    return _glif_attr(docs, element, attr).get("description")


def _page_attr(docs: dict[str, Any], page: str, key: str) -> dict[str, Any]:
    for section in docs.get("pages", {}).get(page, {}).values():
        if key in section.get("attributes", {}):
            return section["attributes"][key]
    return {}


# ---------------------------------------------------------------------------
# shared primitives


def primitives() -> dict[str, Any]:
    unit = r"(0|1|0?\.\d+|1\.0+)"
    return {
        "Color": js.string(
            "UFO color definition: four comma separated numbers (red, green, blue, alpha), each between 0 and 1.",
            pattern=rf"^\s*{unit}\s*,\s*{unit}\s*,\s*{unit}\s*,\s*{unit}\s*$",
        ),
        "Identifier": js.string(
            "Object identifier per the UFO conventions: 1 to 100 characters drawn from printable ASCII (0x20-0x7E), unique within its scope.",
            minLength=1,
            maxLength=100,
            pattern=r"^[\x20-\x7E]{1,100}$",
        ),
        "GlyphName": js.string("Glyph name. At least one character, no control characters.", minLength=1),
        "LayerName": js.string("Layer name. At least one character, no control characters.", minLength=1),
        "AxisName": js.string("Designspace axis name (the human readable name, not the four letter tag).", minLength=1),
        "Location": js.record(js.number(), "Designspace location: axis name to axis value."),
        "PlistValue": {
            "description": "Any XML property list value: string, number, boolean, date (ISO string), data (base64 string), array or dictionary.",
        },
        "PlistDict": js.record(js.ref("PlistValue"), "Property list dictionary."),
    }


# ---------------------------------------------------------------------------
# fontinfo.plist


def _py_type_schema(py_type: Any) -> dict[str, Any]:
    """Map the fontTools ``type`` entry to a JSON type."""
    if py_type is str:
        return js.string()
    if py_type is bool:
        return js.boolean()
    if py_type is int:
        return js.integer()
    if py_type is float:
        return js.number()
    if py_type is dict:
        return js.record({})
    if py_type is list:
        return js.array({})
    if py_type == "integerList":
        return js.array(js.integer())
    if py_type == "dictList":
        return js.array(js.record({}))
    if isinstance(py_type, tuple) and set(py_type) <= {int, float}:
        return js.number()
    return {}


def _fontinfo_refinements() -> dict[str, dict[str, Any]]:
    """Per-key refinements mirroring the ufoLib validator each key is bound to."""
    r: dict[str, dict[str, Any]] = {}
    r["styleMapStyleName"] = js.enum(["regular", "italic", "bold", "bold italic"])
    r["openTypeOS2WidthClass"] = js.integer(minimum=1, maximum=9)
    r["openTypeOS2WeightClass"] = js.integer(minimum=0)
    r["openTypeOS2FamilyClass"] = js.tuple_([js.integer(minimum=0, maximum=14), js.integer(minimum=0, maximum=15)])
    r["openTypeOS2Panose"] = js.array(js.integer(minimum=0), minItems=10, maxItems=10)
    r["openTypeHeadCreated"] = js.string(pattern=r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$")
    r["openTypeGaspRangeRecords"] = js.array(js.ref("GaspRangeRecord"))
    r["openTypeNameRecords"] = js.array(js.ref("NameRecord"))
    r["postscriptBlueValues"] = js.array(js.number(), maxItems=14)
    r["postscriptOtherBlues"] = js.array(js.number(), maxItems=10)
    r["postscriptFamilyBlues"] = js.array(js.number(), maxItems=14)
    r["postscriptFamilyOtherBlues"] = js.array(js.number(), maxItems=10)
    r["postscriptStemSnapH"] = js.array(js.number(), maxItems=12)
    r["postscriptStemSnapV"] = js.array(js.number(), maxItems=12)
    r["postscriptWindowsCharacterSet"] = js.integer(minimum=1, maximum=20)
    r["guidelines"] = js.array(js.ref("Guideline"))
    r["woffMetadataUniqueID"] = js.ref("WoffMetadataUniqueID")
    r["woffMetadataVendor"] = js.ref("WoffMetadataVendor")
    r["woffMetadataCredits"] = js.ref("WoffMetadataCredits")
    r["woffMetadataDescription"] = js.ref("WoffMetadataDescription")
    r["woffMetadataLicense"] = js.ref("WoffMetadataLicense")
    r["woffMetadataCopyright"] = js.ref("WoffMetadataCopyright")
    r["woffMetadataTrademark"] = js.ref("WoffMetadataTrademark")
    r["woffMetadataLicensee"] = js.ref("WoffMetadataLicensee")
    r["woffMetadataExtensions"] = js.array(js.ref("WoffMetadataExtension"))
    for key in [
        "openTypeHeadFlags",
        "openTypeOS2Selection",
        "openTypeOS2UnicodeRanges",
        "openTypeOS2CodePageRanges",
        "openTypeOS2Type",
    ]:
        r[key] = js.array(js.integer(minimum=0), uniqueItems=True)
    return r


def fontinfo_defs(docs: dict[str, Any]) -> dict[str, Any]:
    spec = flatten_fontinfo(docs)
    refinements = _fontinfo_refinements()
    props: dict[str, Any] = {}
    for key in sorted(FONTINFO_V3):
        data = FONTINFO_V3[key]
        validator = data["valueValidator"].__name__
        schema = refinements.get(key) or _py_type_schema(data["type"])
        if validator in ("genericNonNegativeIntValidator", "genericNonNegativeNumberValidator"):
            schema = {**schema, "minimum": 0}
        entry = spec.get(key, {})
        description = entry.get("description")
        if entry.get("type"):
            description = f"{description or ''} [spec type: {entry['type']}]".strip()
        schema = js.desc(schema, description)
        schema["x-ufolib-validator"] = validator
        props[key] = schema

    def section(key: str) -> str | None:
        return _page_attr(docs, "fontinfo", key).get("description")

    text_record = js.obj(
        {
            "text": js.string(section("text")),
            "language": js.string(),
            "dir": js.enum(["ltr", "rtl"]),
            "class": js.string(),
        },
        ["text"],
    )
    name_like = {
        "name": js.string(),
        "url": js.string(),
        "role": js.string(),
        "dir": js.enum(["ltr", "rtl"]),
        "class": js.string(),
    }
    return {
        "FontInfo": js.obj(
            props,
            description=(
                "fontinfo.plist: every UFO 3 fontinfo key. Key list and base types come from "
                "fontTools.ufoLib.fontInfoAttributesVersion3ValueData; descriptions from the UFO specification."
            ),
            additional=True,
        ),
        "GaspRangeRecord": js.obj(
            {
                "rangeMaxPPEM": js.integer(section("rangeMaxPPEM"), minimum=0),
                "rangeGaspBehavior": js.array(
                    js.integer(minimum=0, maximum=3), section("rangeGaspBehavior"), uniqueItems=True
                ),
            },
            ["rangeMaxPPEM", "rangeGaspBehavior"],
        ),
        "NameRecord": js.obj(
            {
                "nameID": js.integer(section("nameID"), minimum=0),
                "platformID": js.integer(section("platformID"), minimum=0),
                "encodingID": js.integer(section("encodingID"), minimum=0),
                "languageID": js.integer(section("languageID"), minimum=0),
                "string": js.string(section("string")),
            },
            ["nameID", "platformID", "encodingID", "languageID", "string"],
        ),
        "Guideline": js.obj(
            {
                "x": js.number(section("x")),
                "y": js.number(section("y")),
                "angle": js.number(section("angle"), minimum=0, maximum=360),
                "name": js.string(section("name")),
                "color": js.ref("Color", section("color")),
                "identifier": js.ref("Identifier", section("identifier")),
            },
            description=(
                "Guideline (fontinfo.plist, layerinfo.plist and GLIF share this shape). "
                "At least one of x or y is required; angle requires both."
            ),
            anyOf=[{"required": ["x"]}, {"required": ["y"]}],
        ),
        "WoffMetadataUniqueID": js.obj({"id": js.string()}, ["id"]),
        "WoffMetadataVendor": js.obj({k: v for k, v in name_like.items() if k != "role"}, ["name"]),
        "WoffMetadataCredit": js.obj(name_like, ["name"]),
        "WoffMetadataCredits": js.obj({"credits": js.array(js.ref("WoffMetadataCredit"), minItems=1)}, ["credits"]),
        "WoffMetadataTextRecord": text_record,
        "WoffMetadataDescription": js.obj(
            {"url": js.string(), "text": js.array(js.ref("WoffMetadataTextRecord"), minItems=1)}, ["text"]
        ),
        "WoffMetadataLicense": js.obj(
            {"url": js.string(), "id": js.string(), "text": js.array(js.ref("WoffMetadataTextRecord"))}
        ),
        "WoffMetadataCopyright": js.obj({"text": js.array(js.ref("WoffMetadataTextRecord"), minItems=1)}, ["text"]),
        "WoffMetadataTrademark": js.obj({"text": js.array(js.ref("WoffMetadataTextRecord"), minItems=1)}, ["text"]),
        "WoffMetadataLicensee": js.obj(
            {"name": js.string(), "dir": js.enum(["ltr", "rtl"]), "class": js.string()}, ["name"]
        ),
        "WoffMetadataExtensionName": text_record,
        "WoffMetadataExtensionValue": text_record,
        "WoffMetadataExtensionItem": js.obj(
            {
                "id": js.string(),
                "names": js.array(js.ref("WoffMetadataExtensionName"), minItems=1),
                "values": js.array(js.ref("WoffMetadataExtensionValue"), minItems=1),
            },
            ["names", "values"],
        ),
        "WoffMetadataExtension": js.obj(
            {
                "id": js.string(),
                "names": js.array(js.ref("WoffMetadataExtensionName")),
                "items": js.array(js.ref("WoffMetadataExtensionItem"), minItems=1),
            },
            ["items"],
        ),
    }


# ---------------------------------------------------------------------------
# GLIF


def _transform_props(docs: dict[str, Any], element: str) -> dict[str, Any]:
    return {
        attr: js.number(_glif_desc(docs, element, attr), default=TRANSFORM_DEFAULTS[attr]) for attr in TRANSFORM_ATTRS
    }


def glif_defs(docs: dict[str, Any]) -> dict[str, Any]:
    def d(element: str, attr: str) -> str | None:
        return _glif_desc(docs, element, attr)

    point_type_docs = {t: d("point", t) for t in POINT_TYPES}

    # Keep the schema honest against the implementation: every attribute that
    # fontTools' GLIF parser accepts must be modelled here.
    assert glifLib.pointAttributesFormat2 == {"x", "y", "type", "smooth", "name", "identifier"}
    assert glifLib.componentAttributesFormat2 == {"base", *TRANSFORM_ATTRS, "identifier"}
    assert glifLib.contourAttributesFormat2 == {"identifier"}

    point = js.obj(
        {
            "x": js.number(d("point", "x")),
            "y": js.number(d("point", "y")),
            "type": js.enum(POINT_TYPES, d("point", "type"), default="offcurve", **{"x-point-types": point_type_docs}),
            "smooth": js.boolean(d("point", "smooth"), default=False),
            "name": js.string(d("point", "name"), minLength=1),
            "identifier": js.ref("Identifier", d("point", "identifier")),
        },
        ["x", "y"],
        description=(
            "GLIF <point>: an attributed coordinate pair. `type` defaults to offcurve. A contour whose first "
            "point is `move` is open, otherwise it is closed (cyclic). A `curve` is preceded by 0, 1 or 2 "
            "offcurve points (line, quadratic, cubic); a `qcurve` by any number (TrueType implied on-curve "
            "points). `smooth` is only meaningful on on-curve points."
        ),
    )

    contour = js.obj(
        {
            "identifier": js.ref("Identifier", d("contour", "identifier")),
            "points": js.array(
                js.ref("Point"),
                "Ordered points. An empty contour is equivalent to no contour. A contour with only offcurve "
                "points is a closed quadratic (TrueType) contour.",
            ),
        },
        ["points"],
        description="GLIF <contour>.",
    )

    component = js.obj(
        {
            "base": js.ref("GlyphName", d("component", "base")),
            **_transform_props(docs, "component"),
            "identifier": js.ref("Identifier", d("component", "identifier")),
        },
        ["base"],
        description=(
            "GLIF <component>: insert another glyph, transformed by the affine matrix "
            "[xScale xyScale yxScale yScale xOffset yOffset] (default identity). Components must reference "
            "glyphs in the same layer and must not be circular."
        ),
    )

    image = js.obj(
        {
            "fileName": js.string(d("image", "fileName"), minLength=1),
            **_transform_props(docs, "image"),
            "color": js.ref("Color", d("image", "color")),
        },
        ["fileName"],
        description="GLIF <image>: an image reference drawn behind the outline.",
    )

    anchor = js.obj(
        {
            "x": js.number(d("anchor", "x")),
            "y": js.number(d("anchor", "y")),
            "name": js.string(d("anchor", "name"), minLength=1),
            "color": js.ref("Color", d("anchor", "color")),
            "identifier": js.ref("Identifier", d("anchor", "identifier")),
        },
        ["x", "y"],
        description="GLIF <anchor>: a named reference position. Names starting with caret_/vcaret_ are ligature carets.",
    )

    advance = js.obj(
        {
            "width": js.number(d("advance", "width"), default=0),
            "height": js.number(d("advance", "height"), default=0),
        },
        description="GLIF <advance>: horizontal and vertical advance.",
    )

    unicode_ = js.obj(
        {"hex": js.string(d("unicode", "hex"), pattern=r"^[0-9A-Fa-f]{4,6}$")},
        ["hex"],
        description=(
            "GLIF <unicode>: a code point as a hexadecimal string without prefix. "
            "The first occurrence is the primary code point."
        ),
    )

    outline = js.obj(
        {
            "contours": js.array(js.ref("Contour")),
            "components": js.array(js.ref("Component")),
        },
        description=(
            "GLIF <outline>. The XML allows contour and component children in any order; the JSON model "
            "separates them (order among contours and among components is preserved)."
        ),
    )

    glyph = js.obj(
        {
            "name": js.ref("GlyphName", d("glyph", "name")),
            "format": js.enum([1, 2], d("glyph", "format"), default=2),
            "formatMinor": js.integer(d("glyph", "formatMinor"), minimum=0, default=0),
            "advance": js.ref("Advance"),
            "unicodes": js.array(js.ref("Unicode"), "All <unicode> elements in document order."),
            "note": js.string("GLIF <note>: arbitrary text."),
            "image": js.ref("Image"),
            "guidelines": js.array(js.ref("Guideline"), "Glyph-level guidelines."),
            "anchors": js.array(js.ref("Anchor")),
            "outline": js.ref("Outline"),
            "lib": js.ref("GlyphLib"),
        },
        ["name"],
        description="A GLIF 2 glyph. Repeated XML elements are collected into arrays in document order.",
    )

    decomposed = js.obj(
        {
            "translateX": js.number("x translation in font units", default=0),
            "translateY": js.number("y translation in font units", default=0),
            "rotation": js.number("rotation angle in counter-clockwise degrees", default=0),
            "scaleX": js.number("scale factor for the x dimension", default=1),
            "scaleY": js.number("scale factor for the y dimension", default=1),
            "skewX": js.number("skew angle x in counter-clockwise degrees", default=0),
            "skewY": js.number("skew angle y in counter-clockwise degrees", default=0),
            "tCenterX": js.number("the x value for the center of transformation", default=0),
            "tCenterY": js.number("the y value for the center of transformation", default=0),
        },
        description=(
            "Decomposed, interpolation friendly transformation (variable-components-in-ufo). Composed as "
            "translate(tCenter) translate(translate) rotate scale skew translate(-tCenter)."
        ),
    )

    variable_component = js.obj(
        {
            "base": js.ref("GlyphName", "Glyph name of the referenced (variable) glyph."),
            "transformation": js.ref("DecomposedTransform", "Omitted when empty."),
            "location": js.ref(
                "Location",
                "Designspace location of the referenced glyph. May be sparse; unspecified axes inherit the "
                "parent location. Omitted when empty.",
            ),
        },
        ["base"],
        description=f"Variable component stored in glyph.lib['{VARIABLE_COMPONENTS_KEY}'].",
    )

    glyph_axis = js.obj(
        {
            "name": js.ref("AxisName"),
            "minimum": js.number(),
            "default": js.number(),
            "maximum": js.number(),
        },
        ["name", "minimum", "default", "maximum"],
        description="Glyph-local axis (variable-components-in-ufo).",
    )

    glyph_source = js.obj(
        {
            "name": js.string("UI name for the source."),
            "location": js.ref(
                "Location", "Location in the augmented (global + local) designspace. Omitted axes take their default."
            ),
            "layername": js.ref("LayerName", "UFO layer holding the source glyph data; default layer if omitted."),
        },
        ["name", "location"],
        description="Glyph-local variation source (variable-components-in-ufo).",
    )

    glyph_designspace = js.obj(
        {
            "axes": js.array(js.ref("GlyphAxis"), minItems=1),
            "sources": js.array(js.ref("GlyphSource")),
        },
        ["axes"],
        description=f"Glyph-level designspace additions stored in glyph.lib['{GLYPH_DESIGNSPACE_KEY}'] in the default layer.",
    )

    hint_set = js.obj(
        {
            "pointTag": js.string("Unique point name. Must match a point 'name' attribute."),
            "stems": js.array(
                js.string(pattern=r"^(hstem|vstem)( -?\d+(\.\d+)?)+$"),
                "Stem strings: 'hstem'/'vstem' followed by an even number of coordinates.",
            ),
        },
        ["pointTag", "stems"],
    )

    ps_hints = js.obj(
        {
            "formatVersion": js.const("1"),
            "id": js.string("Hash of glyph outlines computed when the glyph was hinted."),
            "hintSetList": js.array(js.ref("PostscriptHintSet")),
            "flexList": js.array(js.string(), "Point names at which flex hints start."),
        },
        ["formatVersion", "id", "hintSetList"],
        description="glyph.lib['public.postscript.hints'].",
    )

    tt_instructions = js.obj(
        {
            "formatVersion": js.const("1"),
            "id": js.string(),
            "assembly": js.string("TrueType assembly, one instruction per line."),
            "coordinates": js.array(js.tuple_([js.number(), js.number()])),
        },
        ["formatVersion", "id", "assembly"],
        description="glyph.lib['public.truetype.instructions'].",
    )

    object_lib_entry = js.obj(
        {
            "public.truetype.roundOffsetToGrid": js.boolean(
                "Component: set ROUND_XY_TO_GRID (bit 2) in the glyf composite flags."
            ),
            "public.truetype.useMyMetrics": js.boolean("Component: set USE_MY_METRICS (bit 9) in the glyf composite flags."),
        },
        additional=js.ref("PlistValue"),
    )
    object_lib = js.record(
        object_lib_entry,
        "public.objectLibs: object identifier -> lib dictionary for a contour, point, component, anchor or guideline.",
    )

    glyph_lib = js.obj(
        {
            "public.markColor": js.ref("Color", "The 'mark' color seen in font editors."),
            "public.verticalOrigin": js.number("Vertical origin of the glyph, used for VORG / vmtx top side bearing."),
            "public.objectLibs": object_lib,
            "public.postscript.hints": js.ref("PostscriptHints"),
            "public.truetype.instructions": js.ref("TrueTypeInstructions"),
            "public.truetype.overlap": js.boolean("Set OVERLAP_SIMPLE / OVERLAP_COMPOUND in glyf flags."),
            VARIABLE_COMPONENTS_KEY: js.array(
                js.ref("VariableComponent"), "Variable components (must be non-empty when present).", minItems=1
            ),
            GLYPH_DESIGNSPACE_KEY: js.ref("GlyphDesignspace"),
        },
        description="glyph.lib. Public keys are typed; other reverse-domain keys carry arbitrary plist values.",
        additional=js.ref("PlistValue"),
    )

    return {
        "Point": point,
        "Contour": contour,
        "Component": component,
        "Image": image,
        "Anchor": anchor,
        "Advance": advance,
        "Unicode": unicode_,
        "Outline": outline,
        "Glyph": glyph,
        "GlyphLib": glyph_lib,
        "PostscriptHints": ps_hints,
        "PostscriptHintSet": hint_set,
        "TrueTypeInstructions": tt_instructions,
        "DecomposedTransform": decomposed,
        "VariableComponent": variable_component,
        "GlyphAxis": glyph_axis,
        "GlyphSource": glyph_source,
        "GlyphDesignspace": glyph_designspace,
    }


# ---------------------------------------------------------------------------
# package level plists


def package_defs(docs: dict[str, Any]) -> dict[str, Any]:
    def m(key: str) -> str | None:
        return _page_attr(docs, "metainfo", key).get("description")

    def li(key: str) -> str | None:
        return _page_attr(docs, "layerinfo", key).get("description")

    metainfo = js.obj(
        {
            "creator": js.string(m("creator")),
            "formatVersion": js.integer(m("formatVersion"), minimum=1, maximum=3),
            "formatVersionMinor": js.integer(m("formatVersionMinor"), minimum=0, default=0),
        },
        ["formatVersion"],
        description="metainfo.plist",
    )

    layer_contents = js.array(
        js.tuple_(
            [
                js.ref("LayerName"),
                js.string(
                    "Directory name: 'glyphs' for the default layer, otherwise 'glyphs.' followed by a name.",
                    pattern=r"^glyphs(\..+)?$",
                ),
            ]
        ),
        (
            "layercontents.plist: ordered [layer name, directory] pairs. The first entry is the default layer; "
            "'public.default' and 'public.background' are the registered layer names."
        ),
        minItems=1,
    )

    layer_info = js.obj(
        {
            "color": js.ref("Color", li("color")),
            "guidelines": js.array(js.ref("Guideline"), "Guidelines that apply to all glyphs in the layer."),
            "lib": js.ref("PlistDict", li("lib")),
        },
        description="layerinfo.plist",
    )

    contents = js.record(
        js.string(
            "GLIF file name, derived from the glyph name by the UFO user-name-to-file-name algorithm.",
            pattern=r"^.+\.glif$",
        ),
        "contents.plist: glyph name to GLIF file name.",
    )

    groups = js.record(
        js.array(js.ref("GlyphName")),
        (
            "groups.plist: group name to glyph names. Kerning groups use the public.kern1. / public.kern2. "
            "prefixes and a glyph may appear in only one group per side."
        ),
    )
    kerning = js.record(
        js.record(js.number()),
        "kerning.plist: first (glyph or public.kern1 group) -> second (glyph or public.kern2 group) -> value.",
    )

    font_lib = js.obj(
        {
            "public.glyphOrder": js.array(js.ref("GlyphName"), "Preferred glyph order.", uniqueItems=True),
            "public.groupOrder": js.array(js.string(), "Preferred group order."),
            "public.postscriptNames": js.record(js.string(), "Glyph name to PostScript (production) name."),
            "public.openTypeCategories": js.record(
                js.enum(["unassigned", "base", "ligature", "mark", "component"]),
                "Glyph name to GDEF glyph class category.",
            ),
            "public.openTypeMeta": js.record(
                js.any_of(js.string(), js.array(js.string())),
                "OpenType meta table tags (dlng, slng as string lists; others as strings/data).",
            ),
            "public.openTypeHeadModified": js.string("Override for the head.modified timestamp (YYYY/MM/DD HH:MM:SS)."),
            "public.openTypePostUnderlinePosition": js.integer("Override for post.underlinePosition."),
            "public.skipExportGlyphs": js.array(
                js.ref("GlyphName"), "Glyphs that must not be exported to binaries (decomposed where referenced)."
            ),
            "public.unicodeVariationSequences": js.record(
                js.record(js.ref("GlyphName")), "Variation selector hex -> base code point hex -> glyph name."
            ),
            "public.objectLibs": js.record(js.ref("PlistDict"), "Guideline identifier -> lib for fontinfo.plist guidelines."),
            "public.truetype.instructions": js.obj(
                {
                    "formatVersion": js.const("1"),
                    "controlValue": js.array(js.tuple_([js.integer(), js.integer()])),
                    "controlValueProgram": js.string(),
                    "fontProgram": js.string(),
                    "maxFunctionDefs": js.integer(minimum=0),
                    "maxInstructionDefs": js.integer(minimum=0),
                    "maxStackElements": js.integer(minimum=0),
                    "maxStorage": js.integer(minimum=0),
                    "maxTwilightPoints": js.integer(minimum=0),
                    "maxZones": js.integer(minimum=0),
                },
                ["formatVersion"],
                description="Font-level TrueType hinting data (cvt, prep, fpgm, maxp).",
            ),
        },
        description="lib.plist. Public keys are typed; other reverse-domain keys carry arbitrary plist values.",
        additional=js.ref("PlistValue"),
    )

    layer = js.obj(
        {
            "name": js.ref("LayerName"),
            "directory": js.string(),
            "layerinfo": js.ref("LayerInfo"),
            "contents": js.ref("Contents"),
            "glyphs": js.record(js.ref("Glyph"), "Glyph name to parsed GLIF."),
        },
        ["name", "directory", "glyphs"],
        description="One glyph layer: a directory listed in layercontents.plist.",
    )

    package = js.obj(
        {
            "path": js.string("File system path of the .ufo package (informational)."),
            "metainfo": js.ref("MetaInfo"),
            "fontinfo": js.ref("FontInfo"),
            "groups": js.ref("Groups"),
            "kerning": js.ref("Kerning"),
            "features": js.string("features.fea: Adobe feature file source."),
            "lib": js.ref("FontLib"),
            "layercontents": js.ref("LayerContents"),
            "layers": js.array(js.ref("Layer"), "Layers in layercontents order."),
            "images": js.array(js.string(), "File names in images/."),
            "data": js.array(js.string(), "Relative file names in data/."),
        },
        ["metainfo", "layercontents", "layers"],
        description="A UFO 3 package parsed into JSON.",
    )

    return {
        "MetaInfo": metainfo,
        "LayerContents": layer_contents,
        "LayerInfo": layer_info,
        "Contents": contents,
        "Groups": groups,
        "Kerning": kerning,
        "FontLib": font_lib,
        "Layer": layer,
        "UfoPackage": package,
    }


def ufo_schema() -> dict[str, Any]:
    docs = load_docs()
    defs = {**primitives(), **fontinfo_defs(docs), **glif_defs(docs), **package_defs(docs)}
    return js.document(
        "ufo",
        "UFO 3 package",
        "UfoPackage",
        defs,
        description=(
            "JSON model of a UFO 3 package: metainfo, fontinfo, lib, groups, kerning, layers and GLIF glyphs, "
            "plus the variable-components-in-ufo glyph.lib extension. Descriptions quote the UFO specification"
            + (f" at commit {docs.get('commit')}" if docs.get("commit") else "")
            + "."
        ),
    )
