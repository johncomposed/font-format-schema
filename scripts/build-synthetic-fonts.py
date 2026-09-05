#!/usr/bin/env python3
"""Build tiny, readable TTX fixtures for avar2, HVAR and VARC.

These are not production fonts. They exist so the repository always has
fontTools-generated XML examples for recent variation structures, even before
external fixtures are downloaded.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from fontTools import varLib
from fontTools.designspaceLib import AxisDescriptor, AxisMappingDescriptor
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


def save(fb: FontBuilder, stem: str, tables: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ttf = OUT / f"{stem}.ttf"
    ttx = OUT / f"{stem}.ttx"
    full_ttx = OUT / f"{stem}.full.ttx"
    fb.font.save(ttf)
    compiled = TTFont(ttf)
    compiled.saveXML(ttx, tables=tables)
    compiled.saveXML(full_ttx)
    print(ttf.relative_to(ROOT))
    print(ttx.relative_to(ROOT))
    print(full_ttx.relative_to(ROOT))


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
    build_avar2()
    build_hvar()
    build_varc()


if __name__ == "__main__":
    main()
