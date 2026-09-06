"""JSON Schema for the TTX (fontTools XML) representation of a font.

TTX has no XSD: it is whatever ``toXML``/``fromXML`` in fontTools produce.  This
module models a JSON projection of that XML for the tables a variable-font
pipeline needs:

* header/metric tables serialised through ``sstruct`` formats (``head``,
  ``hhea``, ``vhea``, ``maxp``, ``OS/2``, ``post``) — field lists and integer/
  fixed types are parsed straight out of the fontTools format strings;
* tables with hand written XML in fontTools (``fvar``, ``avar``, ``gvar``,
  ``cvar``, ``glyf``, ``hmtx``/``vmtx``, ``cmap``, ``name``, ``cvt``) — modelled
  by hand after the pinned implementation, see ``ttx/tojson.py`` for the exact
  element-to-JSON mapping;
* otData driven tables (``STAT``, ``HVAR``, ``MVAR``, ``VARC``, ``GDEF``...) —
  represented as a generic ``OtTable`` tree whose field names follow
  ``schemas/ttx-otdata-variation.schema.json``;
* anything else — the raw XML AST.
"""
from __future__ import annotations

import re
from typing import Any

from fontTools.ttLib.tables import O_S_2f_2, _h_e_a_d, _h_h_e_a, _m_a_x_p, _p_o_s_t, _v_h_e_a

from . import js

SSTRUCT_FORMATS: dict[str, list[tuple[str, str]]] = {
    "head": [("head", _h_e_a_d.headFormat)],
    "hhea": [("hhea", _h_h_e_a.hheaFormat)],
    "vhea": [("vhea", _v_h_e_a.vheaFormat)],
    "maxp": [("maxp 0.5", _m_a_x_p.maxpFormat_0_5), ("maxp 1.0 addition", _m_a_x_p.maxpFormat_1_0_add)],
    "OS/2": [("OS/2 format 5", O_S_2f_2.OS2_format_5)],
    "post": [("post", _p_o_s_t.postFormat)],
}
PANOSE_FORMAT = O_S_2f_2.panoseFormat

# Fields that TTX writes as something other than a plain number.
TTX_STRING_FIELDS = {("head", "created"), ("head", "modified"), ("OS/2", "achVendID")}
# Fields written as binary/hex strings; the JSON model normalises them to integers.
TTX_BITFIELD_FIELDS = {
    ("head", "flags"), ("head", "macStyle"), ("head", "checkSumAdjustment"), ("head", "magicNumber"),
    ("OS/2", "fsType"), ("OS/2", "fsSelection"),
    ("OS/2", "ulUnicodeRange1"), ("OS/2", "ulUnicodeRange2"), ("OS/2", "ulUnicodeRange3"), ("OS/2", "ulUnicodeRange4"),
    ("OS/2", "ulCodePageRange1"), ("OS/2", "ulCodePageRange2"),
}
# Fields only present for some table formats.
OPTIONAL_FIELDS = {
    "maxp": {"maxPoints", "maxContours", "maxCompositePoints", "maxCompositeContours", "maxZones", "maxTwilightPoints",
             "maxStorage", "maxFunctionDefs", "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions",
             "maxComponentElements", "maxComponentDepth"},
    "OS/2": {"ulCodePageRange1", "ulCodePageRange2", "sxHeight", "sCapHeight", "usDefaultChar", "usBreakChar",
             "usMaxContext", "usLowerOpticalPointSize", "usUpperOpticalPointSize"},
}

FIELD_RE = re.compile(r"^\s*(\w+)\s*:\s*([\w.]+)\s*(?:#\s*(.*))?$")


def parse_sstruct(fmt: str) -> list[dict[str, str]]:
    """Return [{name, format, comment}] for an ``sstruct`` format string."""
    fields = []
    for line in fmt.splitlines():
        line = line.strip()
        if not line or line.startswith(">") or line.startswith("<") or line.startswith("#"):
            continue
        m = FIELD_RE.match(line)
        if not m:
            continue
        fields.append({"name": m.group(1), "format": m.group(2), "comment": (m.group(3) or "").strip()})
    return fields


def _sstruct_field_schema(table: str, field: dict[str, str]) -> dict[str, Any]:
    name, fmt = field["name"], field["format"]
    if (table, name) in TTX_STRING_FIELDS:
        schema = js.string()
    elif fmt.endswith("F"):
        schema = js.number()
    elif fmt in {"b", "B", "h", "H", "l", "L", "i", "I", "q", "Q"}:
        schema = js.integer()
        if fmt.isupper():
            schema["minimum"] = 0
    elif fmt.endswith("s"):
        schema = js.string()
    else:
        schema = {}
    comment = field["comment"]
    if (table, name) in TTX_BITFIELD_FIELDS:
        comment = (comment + " " if comment else "") + "(TTX writes this as a binary or hex string; the JSON model uses the integer value.)"
    schema = js.desc(schema, comment or None)
    schema["x-sstruct-format"] = fmt
    return schema


def sstruct_table_schema(tag: str, description: str, extra: dict[str, Any] | None = None, extra_required: list[str] | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {}
    required: list[str] = []
    for _, fmt in SSTRUCT_FORMATS[tag]:
        for field in parse_sstruct(fmt):
            props[field["name"]] = _sstruct_field_schema(tag, field)
            if field["name"] not in OPTIONAL_FIELDS.get(tag, set()):
                required.append(field["name"])
    if extra:
        props.update(extra)
    if extra_required:
        required.extend(extra_required)
    required = list(dict.fromkeys(required))
    return js.obj(props, required, description=description, additional=False)


def ttx_defs() -> dict[str, Any]:
    glyph_name = js.string("Glyph name as used in GlyphOrder.", minLength=1)
    axis_tag = js.string("Four character axis tag.", minLength=4, maxLength=4)
    f2dot14 = js.number("Normalised axis coordinate (F2Dot14) in [-1, 1].", minimum=-1, maximum=1)

    # -- generic otData tree -------------------------------------------------
    ot_value = js.any_of(
        js.number(), js.string(), js.boolean(), {"type": "null"},
        js.array(js.ref("OtValue")),
        js.ref("OtTable"),
        description=(
            "A field of an otData table: scalar (`<Field value=.../>`), list (`value=\"[..]\"`, possibly nested), "
            "sub-table, or array of sub-tables (`index=` attribute or repeated element). A repeated element that "
            "occurs once (e.g. a single Coverage Glyph) is a scalar, not a one-item array."
        ),
    )
    ot_table = js.record(
        js.ref("OtValue"),
        "Generic JSON projection of fontTools otData XML. Field names match schemas/ttx-otdata-variation.schema.json definitions; count fields that TTX writes as comments are omitted. `Format` attributes become a `Format` field.",
    )

    xml_element = js.obj(
        {
            "tag": js.string(),
            "attributes": js.record(js.string()),
            "text": js.string(),
            "children": js.array(js.ref("XmlElement")),
        },
        ["tag", "attributes", "children"],
        description="Ordered XML AST used for tables without a dedicated JSON model.",
    )

    # -- sstruct tables ------------------------------------------------------
    panose = js.obj({f["name"]: js.integer(minimum=0, maximum=255) for f in parse_sstruct(PANOSE_FORMAT)},
                    [f["name"] for f in parse_sstruct(PANOSE_FORMAT)], description="OS/2 panose classification.")
    head = sstruct_table_schema("head", "Font header. created/modified are TTX date strings (e.g. 'Sat Sep  5 21:03:16 2026').")
    hhea = sstruct_table_schema("hhea", "Horizontal header.")
    vhea = sstruct_table_schema("vhea", "Vertical header.")
    maxp = sstruct_table_schema("maxp", "Maximum profile. Version 0.5 (CFF) has only tableVersion and numGlyphs.")
    os2 = sstruct_table_schema("OS/2", "OS/2 and Windows metrics. Bit fields are integers; achVendID is a 4 character string.",
                               extra={"panose": js.ref("Panose")}, extra_required=["panose"])
    post = sstruct_table_schema(
        "post", "PostScript table. formatType 2.0 carries psNames/extraNames; formatType 4.0 carries mapping.",
        extra={
            "psNames": js.record(js.string(), "Glyph name -> PostScript name where they differ (format 2.0)."),
            "extraNames": js.array(glyph_name, "Names not in the standard Macintosh glyph order (format 2.0)."),
            "mapping": js.record(js.integer(), "Glyph name -> character code (format 4.0)."),
        },
    )

    # -- metrics -------------------------------------------------------------
    hmtx = js.array(js.obj({"name": glyph_name, "width": js.integer(minimum=0), "lsb": js.integer()}, ["name", "width", "lsb"]),
                    "Horizontal metrics: one `<mtx>` per glyph in GlyphOrder.")
    vmtx = js.array(js.obj({"name": glyph_name, "height": js.integer(minimum=0), "tsb": js.integer()}, ["name", "height", "tsb"]),
                    "Vertical metrics: one `<mtx>` per glyph in GlyphOrder.")

    # -- cmap / name ---------------------------------------------------------
    cmap_subtable = js.obj(
        {
            "format": js.integer("Subtable format (element name cmap_format_N).", enum=[0, 2, 4, 6, 10, 12, 13, 14]),
            "platformID": js.integer(minimum=0),
            "platEncID": js.integer(minimum=0),
            "language": js.integer(minimum=0),
            "map": js.record(glyph_name, "Character code (decimal string) -> glyph name. Formats 0, 2, 4, 6, 10, 12, 13.",
                             propertyNames={"pattern": r"^\d+$"}),
            "uvs": js.record(js.array(js.tuple_([js.integer(), js.nullable(glyph_name)])),
                             "Format 14: variation selector (decimal string) -> [base code point, glyph name or null for default]."),
        },
        ["format", "platformID", "platEncID"],
        description="One cmap subtable.",
    )
    cmap = js.obj({"tableVersion": js.integer(default=0), "subtables": js.array(js.ref("CmapSubtable"))}, ["subtables"], description="Character map.")

    name_record = js.obj(
        {
            "nameID": js.integer(minimum=0),
            "platformID": js.integer(minimum=0),
            "platEncID": js.integer(minimum=0),
            "langID": js.integer("Language ID (TTX writes hex).", minimum=0),
            "unicode": js.boolean("Present in TTX only when the encoding is not Unicode compatible: whether the text is given decoded."),
            "text": js.string("Decoded string."),
        },
        ["nameID", "platformID", "platEncID", "langID", "text"],
        description="`<namerecord>`.",
    )
    name = js.obj({"records": js.array(js.ref("NameRecord"))}, ["records"], description="Naming table.")

    # -- glyf ----------------------------------------------------------------
    tt_point = js.obj(
        {
            "x": js.integer(),
            "y": js.integer(),
            "on": js.boolean("On-curve flag. Consecutive off-curve points imply a midpoint on-curve point (quadratic). With `cubic`, pairs of off-curve points are cubic control points."),
            "overlap": js.boolean("OVERLAP_SIMPLE flag on the first point of the glyph.", default=False),
            "cubic": js.boolean("CUBIC flag (glyf format 1 / boring-expansion).", default=False),
        },
        ["x", "y", "on"],
        description="`<pt>`: an absolute TrueType outline point.",
    )
    tt_contour = js.obj({"points": js.array(js.ref("TTPoint"))}, ["points"], description="`<contour>`: a closed TrueType contour.")
    tt_component = js.obj(
        {
            "glyphName": glyph_name,
            "x": js.integer("Offset x (when positioned by offsets)."),
            "y": js.integer("Offset y."),
            "firstPt": js.integer("Parent point index (when positioned by point matching).", minimum=0),
            "secondPt": js.integer("Child point index.", minimum=0),
            "scale": js.number("Uniform scale (WE_HAVE_A_SCALE)."),
            "scalex": js.number("X scale (WE_HAVE_AN_X_AND_Y_SCALE or WE_HAVE_A_TWO_BY_TWO)."),
            "scale01": js.number("2x2 matrix component (WE_HAVE_A_TWO_BY_TWO)."),
            "scale10": js.number("2x2 matrix component (WE_HAVE_A_TWO_BY_TWO)."),
            "scaley": js.number("Y scale."),
            "flags": js.integer("Composite glyph flags (TTX writes hex).", minimum=0),
        },
        ["glyphName", "flags"],
        description="`<component>` of a composite TrueType glyph. Either x/y or firstPt/secondPt is present; at most one of scale, scalex+scaley, or the 2x2 set.",
    )
    tt_glyph = js.obj(
        {
            "name": glyph_name,
            "xMin": js.integer(), "yMin": js.integer(), "xMax": js.integer(), "yMax": js.integer(),
            "contours": js.array(js.ref("TTContour"), "Simple glyph contours (absent for empty and composite glyphs)."),
            "components": js.array(js.ref("TTComponent"), "Composite glyph components."),
            "instructions": js.nullable(js.string("TrueType assembly; null when `<instructions/>` is present but empty.")),
        },
        ["name"],
        description="`<TTGlyph>`. An element with no children is an empty glyph. Bounding box attributes are recalculated by the compiler.",
    )
    glyf = js.obj({"glyphs": js.record(js.ref("TTGlyph"), "Glyph name -> glyph, in GlyphOrder order.")}, ["glyphs"], description="Glyph data.")

    # -- variation tables ----------------------------------------------------
    fvar_axis = js.obj(
        {
            "axisTag": axis_tag,
            "flags": js.integer("Axis flags; bit 0 = HIDDEN_AXIS.", minimum=0, default=0),
            "minValue": js.number("Minimum user coordinate (Fixed)."),
            "defaultValue": js.number("Default user coordinate (Fixed)."),
            "maxValue": js.number("Maximum user coordinate (Fixed)."),
            "axisNameID": js.integer("name table ID for the axis name.", minimum=0),
        },
        ["axisTag", "minValue", "defaultValue", "maxValue", "axisNameID"],
        description="`<Axis>` in fvar (VariationAxisRecord).",
    )
    fvar_instance = js.obj(
        {
            "flags": js.integer(minimum=0, default=0),
            "subfamilyNameID": js.integer(minimum=0),
            "postscriptNameID": js.integer("Absent when 0xFFFF (no PostScript name).", minimum=0),
            "coordinates": js.record(js.number(), "Axis tag -> user coordinate (`<coord axis= value=/>`)."),
        },
        ["subfamilyNameID", "coordinates"],
        description="`<NamedInstance>` in fvar (InstanceRecord).",
    )
    fvar = js.obj({"axes": js.array(js.ref("FvarAxis"), minItems=1), "instances": js.array(js.ref("FvarInstance"))}, ["axes", "instances"],
                  description="Font variations table: axis definitions in user space plus named instances.")

    avar_mapping = js.obj({"from": f2dot14, "to": f2dot14}, ["from", "to"], description="`<mapping from= to=/>`: normalised input -> normalised output.")
    avar = js.obj(
        {
            "version": js.obj({"major": js.integer(minimum=1, maximum=2), "minor": js.integer(minimum=0)}, ["major", "minor"]),
            "segments": js.record(js.array(js.ref("AvarMapping"), "Sorted by `from`; must include -1->-1, 0->0 and 1->1 when non-empty."),
                                  "Axis tag -> piecewise linear segment map (`<segment axis=>`), one per fvar axis."),
            "VarIdxMap": js.ref("OtTable", "avar version 2: DeltaSetIndexMap from axis index to VarStore entry."),
            "VarStore": js.ref("OtTable", "avar version 2: item variation store whose deltas move normalised coordinates."),
        },
        ["version", "segments"],
        description="Axis variations table.",
    )

    tuple_axis = js.obj(
        {
            "value": f2dot14,
            "min": js.number("Start of the intermediate region; defaults to min(value, 0).", minimum=-1, maximum=1),
            "max": js.number("End of the intermediate region; defaults to max(value, 0).", minimum=-1, maximum=1),
        },
        ["value"],
        description="`<coord axis= value= [min= max=]/>`: the peak (and optional intermediate start/end) of a tuple region on one axis. Axes absent from the tuple have peak 0.",
    )
    point_delta = js.obj({"pt": js.integer(minimum=0), "x": js.integer(), "y": js.integer()}, ["pt", "x", "y"],
                         description="`<delta pt= x= y=/>`. Points not listed are inferred (IUP). The last four point indices are the phantom points (left, right, top, bottom side bearings).")
    cvt_delta = js.obj({"cvt": js.integer(minimum=0), "value": js.integer()}, ["cvt", "value"], description="`<delta cvt= value=/>`.")
    glyph_tuple = js.obj(
        {"axes": js.record(js.ref("TupleAxis"), "Axis tag -> region on that axis."), "deltas": js.array(js.ref("PointDelta"))},
        ["axes", "deltas"],
        description="`<tuple>` in gvar: a TupleVariationHeader plus its point deltas.",
    )
    cvt_tuple = js.obj(
        {"axes": js.record(js.ref("TupleAxis")), "deltas": js.array(js.ref("CvtDelta"))},
        ["axes", "deltas"],
        description="`<tuple>` in cvar.",
    )
    gvar = js.obj(
        {
            "version": js.integer(default=1),
            "reserved": js.integer(default=0),
            "glyphVariations": js.record(js.array(js.ref("GlyphTupleVariation")), "Glyph name -> tuple variations (`<glyphVariations glyph=>`). Glyphs without variations are absent."),
        },
        ["version", "reserved", "glyphVariations"],
        description="Glyph variations table.",
    )
    cvar = js.obj(
        {
            "version": js.obj({"major": js.integer(), "minor": js.integer()}, ["major", "minor"]),
            "variations": js.array(js.ref("CvtTupleVariation")),
        },
        ["version", "variations"],
        description="CVT variations table.",
    )
    cvt = js.array(js.integer(), "Control values (`<cv index= value=/>`).")

    font = js.obj(
        {
            "sfntVersion": js.string("'\\x00\\x01\\x00\\x00' (TrueType) or 'OTTO' (CFF)."),
            "ttLibVersion": js.string("fontTools version that wrote the TTX."),
            "GlyphOrder": js.array(glyph_name, "Glyph names in glyph ID order."),
            "head": js.ref("Head"),
            "hhea": js.ref("Hhea"),
            "vhea": js.ref("Vhea"),
            "maxp": js.ref("Maxp"),
            "OS_2": js.ref("OS2"),
            "hmtx": js.ref("Hmtx"),
            "vmtx": js.ref("Vmtx"),
            "cmap": js.ref("Cmap"),
            "name": js.ref("Name"),
            "post": js.ref("Post"),
            "glyf": js.ref("Glyf"),
            "loca": js.obj({}, description="Recalculated by the compiler; carries no data in TTX.", additional=False),
            "cvt": js.ref("Cvt"),
            "fvar": js.ref("Fvar"),
            "avar": js.ref("Avar"),
            "gvar": js.ref("Gvar"),
            "cvar": js.ref("Cvar"),
            "STAT": js.ref("OtTable"),
            "HVAR": js.ref("OtTable"),
            "VVAR": js.ref("OtTable"),
            "MVAR": js.ref("OtTable"),
            "VARC": js.ref("OtTable"),
            "GDEF": js.ref("OtTable"),
            "GSUB": js.ref("OtTable"),
            "GPOS": js.ref("OtTable"),
            "BASE": js.ref("OtTable"),
            "tables": js.record(js.ref("XmlElement"), "Any other table, keyed by TTX element name, as raw XML."),
        },
        ["sfntVersion", "GlyphOrder"],
        description="`<ttFont>`: JSON projection of a TTX dump. Table keys use the TTX element names (tagToXML), e.g. OS_2 for 'OS/2' and cvt for 'cvt '.",
    )

    return {
        "GlyphName": glyph_name,
        "OtValue": ot_value,
        "OtTable": ot_table,
        "XmlElement": xml_element,
        "Panose": panose,
        "Head": head,
        "Hhea": hhea,
        "Vhea": vhea,
        "Maxp": maxp,
        "OS2": os2,
        "Post": post,
        "Hmtx": hmtx,
        "Vmtx": vmtx,
        "CmapSubtable": cmap_subtable,
        "Cmap": cmap,
        "NameRecord": name_record,
        "Name": name,
        "TTPoint": tt_point,
        "TTContour": tt_contour,
        "TTComponent": tt_component,
        "TTGlyph": tt_glyph,
        "Glyf": glyf,
        "FvarAxis": fvar_axis,
        "FvarInstance": fvar_instance,
        "Fvar": fvar,
        "AvarMapping": avar_mapping,
        "Avar": avar,
        "TupleAxis": tuple_axis,
        "PointDelta": point_delta,
        "CvtDelta": cvt_delta,
        "GlyphTupleVariation": glyph_tuple,
        "CvtTupleVariation": cvt_tuple,
        "Gvar": gvar,
        "Cvar": cvar,
        "Cvt": cvt,
        "TtxFont": font,
    }


def ttx_schema() -> dict[str, Any]:
    import fontTools

    return js.document(
        "ttx",
        "TTX font",
        "TtxFont",
        ttx_defs(),
        description=(
            f"JSON projection of fontTools {fontTools.__version__} TTX XML for the core variable-font tables "
            "(fvar, avar, gvar, cvar, glyf, metrics, cmap, name, post, head/hhea/maxp/OS/2) plus a generic tree for otData tables."
        ),
    )
