#!/usr/bin/env python3
"""Build tiny, readable TTX fixtures for the variation tables.

These are not production fonts. They exist so the repository always has
fontTools-generated XML examples for the structures this project models:

vf-demo     a two-axis variable font compiled with varLib from in-memory
            masters: fvar with a named instance, avar version 1 (non-linear
            map), gvar with an intermediate master and a composite glyph,
            cvar, HVAR, STAT, glyf/hmtx/cmap/name/post
avar2-demo  avar version 2 with VarIdxMap and VarStore
hvar-demo   HVAR with a VarStore and explicit AdvWidthMap
varc-demo   VARC with AxisIndicesList and a VarCompositeGlyph
"""
from __future__ import annotations

# fontTools table objects are built dynamically and ship no type stubs.
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false

import array
from collections import OrderedDict
from pathlib import Path

from fontTools import varLib
from fontTools.designspaceLib import AxisDescriptor, AxisMappingDescriptor, DesignSpaceDocument, InstanceDescriptor, SourceDescriptor
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.otTables import VarComponent, VarComponentFlags, VarCompositeGlyph
from fontTools.varLib import builder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "ttx-synthetic"


def base_font(family: str, glyph_order: list[str], axes: list[tuple[str, int, int, int, str]]) -> FontBuilder:
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    glyphs = {}
    for name in glyph_order:
        pen = TTGlyphPen(None)
        if name == "stem":
            pen.moveTo((100, 0)); pen.lineTo((200, 0)); pen.lineTo((200, 700)); pen.lineTo((100, 700)); pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({g: (600, 0) for g in glyph_order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    cmap = {0x41 + i: g for i, g in enumerate(glyph_order) if g != ".notdef"}
    fb.setupCharacterMap(cmap)
    fb.setupNameTable({"familyName": family, "styleName": "Regular", "fullName": f"{family} Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    fb.setupFvar(axes, [])
    return fb


def save_font(font: TTFont, stem: str, tables: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ttf = OUT / f"{stem}.ttf"
    ttx = OUT / f"{stem}.ttx"
    full_ttx = OUT / f"{stem}.full.ttx"
    font.save(ttf)
    compiled = TTFont(ttf)
    compiled.saveXML(ttx, tables=tables)
    compiled.saveXML(full_ttx)
    for p in (ttf, ttx, full_ttx):
        print(p.relative_to(ROOT))


def save(fb: FontBuilder, stem: str, tables: list[str]) -> None:
    save_font(fb.font, stem, tables)


# ---------------------------------------------------------------------------
# vf-demo: a real varLib build


def _master(wght: float, wdth: float) -> TTFont:
    """One master. wght/wdth are *design* coordinates (see the axis maps below)."""
    order = [".notdef", "stem", "arch", "archstem"]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    glyphs: dict = {}
    pen = TTGlyphPen(glyphs)
    glyphs[".notdef"] = pen.glyph()
    # stem: a rectangle whose width follows weight.
    pen = TTGlyphPen(glyphs)
    w = 60 + wght
    pen.moveTo((100, 0)); pen.lineTo((100 + w, 0)); pen.lineTo((100 + w, 700)); pen.lineTo((100, 700)); pen.closePath()
    glyphs["stem"] = pen.glyph()
    # arch: a quadratic curve whose height follows width, so gvar has off-curve deltas.
    pen = TTGlyphPen(glyphs)
    pen.moveTo((50, 0)); pen.qCurveTo((200, 300 + wdth), (350, 0)); pen.closePath()
    glyphs["arch"] = pen.glyph()
    # archstem: a composite of the two, with a component offset that varies.
    pen = TTGlyphPen(glyphs)
    pen.addComponent("stem", (1, 0, 0, 1, wdth, 0))
    pen.addComponent("arch", (1, 0, 0, 1, 0, 0))
    glyphs["archstem"] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (500 + int(wght), 50) for n in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupCharacterMap({0x7C: "stem", 0x41: "arch", 0x42: "archstem"})
    fb.setupNameTable({"familyName": "VF Demo", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    cvt = newTable("cvt ")
    cvt.values = array.array("h", [int(wght), 50])
    fb.font["cvt "] = cvt
    return fb.font


def build_vf() -> None:
    doc = DesignSpaceDocument()
    weight = AxisDescriptor()
    weight.name, weight.tag = "Weight", "wght"
    weight.minimum, weight.default, weight.maximum = 100, 400, 900
    # Non-linear user->design map so avar version 1 is emitted.
    weight.map = [(100, 0), (400, 40), (600, 50), (900, 100)]
    width = AxisDescriptor()
    width.name, width.tag = "Width", "wdth"
    width.minimum, width.default, width.maximum = 75, 100, 125
    doc.addAxis(weight)
    doc.addAxis(width)
    masters = [
        ("Light", 0, 100),
        ("Regular", 40, 100),
        ("Medium", 70, 100),  # intermediate master -> gvar tuples with min/max
        ("Black", 100, 100),
        ("Condensed", 40, 75),
        ("Extended", 40, 125),
    ]
    for name, wght, wdth in masters:
        src = SourceDescriptor()
        src.name = name
        src.font = _master(wght, wdth)
        src.location = {"Weight": wght, "Width": wdth}
        doc.addSource(src)
    inst = InstanceDescriptor()
    inst.styleName = "Bold"
    inst.postScriptFontName = "VFDemo-Bold"
    inst.location = {"Weight": 80, "Width": 100}
    doc.addInstance(inst)
    vf, _, _ = varLib.build(doc, optimize=True)
    save_font(vf, "vf-demo", ["fvar", "avar", "gvar", "cvar", "HVAR", "STAT"])


# ---------------------------------------------------------------------------
# focused fixtures


def build_varc() -> None:
    fb = base_font("VARC Demo", [".notdef", "stem", "parent"], [("wght", 100, 400, 900, "Weight")])
    varc = newTable("VARC")
    table = otTables.VARC()
    varc.table = table
    table.Version = 0x00010000
    coverage = otTables.Coverage(); coverage.glyphs = ["parent"]; table.Coverage = coverage
    table.MultiVarStore = None
    table.ConditionList = None
    axis_indices = otTables.AxisIndicesList(); axis_indices.Item = [(0,)]; table.AxisIndicesList = axis_indices
    component = VarComponent()
    component.glyphName = "stem"
    component.axisIndicesIndex = 0
    component.axisValues = (0.5,)
    component.flags |= VarComponentFlags.HAVE_TRANSLATE_X
    component.transform.translateX = 50
    composites = otTables.VarCompositeGlyphs()
    composites.VarCompositeGlyph = [VarCompositeGlyph([component])]
    table.VarCompositeGlyphs = composites
    fb.font["VARC"] = varc
    save(fb, "varc-demo", ["fvar", "VARC"])


def build_hvar() -> None:
    order = [".notdef", "A", "B"]
    fb = base_font("HVAR Demo", order, [("wght", 100, 400, 900, "Weight")])
    region_list = builder.buildVarRegionList([{"wght": (0, 1, 1)}], ["wght"])
    var_data = builder.buildVarData([0], [[0], [50], [100]], optimize=False)
    store = builder.buildVarStore(region_list, [var_data])
    adv_width_map = builder.buildVarIdxMap([0, 1, 2], order)
    hvar = newTable("HVAR")
    table = otTables.HVAR(); hvar.table = table
    table.Version = 0x00010000
    table.VarStore = store
    table.AdvWidthMap = adv_width_map
    table.LsbMap = None
    table.RsbMap = None
    fb.font["HVAR"] = hvar
    save(fb, "hvar-demo", ["fvar", "HVAR"])


def build_avar2() -> None:
    axes: OrderedDict[str, AxisDescriptor] = OrderedDict()
    for name, tag, minimum, default, maximum in [
        ("Weight", "wght", 100, 400, 900),
        ("Width", "wdth", 75, 100, 125),
    ]:
        axis = AxisDescriptor()
        axis.name = name; axis.tag = tag
        axis.minimum = minimum; axis.default = default; axis.maximum = maximum
        axis.map = []
        axes[name] = axis
    fb = base_font("avar2 Demo", [".notdef", "A"], [(a.tag, a.minimum, a.default, a.maximum, a.name) for a in axes.values()])
    mapping = AxisMappingDescriptor(
        inputLocation={"Weight": 700, "Width": 120},
        outputLocation={"Weight": 650, "Width": 110},
    )
    # FontBuilder.setupAvar() does not preserve name-keyed mapping context in
    # fontTools 4.63+, so this pinned example calls varLib's implementation
    # directly with the OrderedDict that Designspace/varLib normally supplies.
    varLib._add_avar(fb.font, axes, [mapping], ["wght", "wdth"])
    save(fb, "avar2-demo", ["fvar", "avar"])


def main() -> None:
    build_vf()
    build_avar2()
    build_hvar()
    build_varc()


if __name__ == "__main__":
    main()
