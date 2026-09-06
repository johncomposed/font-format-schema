import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { test } from "node:test";
import assert from "node:assert/strict";

import * as ufo from "../generated/zod/ufo.ts";
import * as designspace from "../generated/zod/designspace.ts";
import * as ttx from "../generated/zod/ttx.ts";
import * as xmlAst from "../generated/zod/xml-ast.ts";
import * as otdata from "../generated/zod/ttx-otdata-variation.ts";
import type { UfoPackage } from "../generated/typescript/ufo.ts";
import type { TtxFont } from "../generated/typescript/ttx.ts";

const root = resolve(import.meta.dirname, "..");
const load = (rel: string): unknown => JSON.parse(readFileSync(join(root, rel), "utf8"));

test("every generated UFO example parses with the UfoPackage schema", () => {
  const dir = join(root, "generated", "ufo");
  for (const file of readdirSync(dir)) {
    const parsed = ufo.UfoPackage.parse(load(`generated/ufo/${file}`));
    const typed: UfoPackage = parsed; // Zod output is assignable to the json-schema-to-typescript type
    assert.equal(typed.metainfo.formatVersion, 3);
    const stem = parsed.layers[0]!.glyphs["stem"]!;
    assert.deepEqual(
      stem.outline!.contours!.map((c) => c.points.map((p) => p.type)),
      [["line", "line", "line", "line"]],
    );
  }
});

test("GLIF point defaults are applied by Zod", () => {
  const point = ufo.Point.parse({ x: 1, y: 2 });
  assert.equal(point.type, "offcurve");
  assert.equal(point.smooth, false);
  assert.throws(() => ufo.Point.parse({ x: 1, y: 2, type: "spline" }));
  const component = ufo.Component.parse({ base: "A" });
  assert.deepEqual([component.xScale, component.xyScale, component.yxScale, component.yScale], [1, 0, 0, 1]);
});

test("fontinfo refinements from ufoLib validators are enforced", () => {
  assert.throws(() => ufo.FontInfo.parse({ openTypeOS2WidthClass: 12 }));
  assert.throws(() => ufo.FontInfo.parse({ styleMapStyleName: "Bold" }));
  assert.throws(() => ufo.FontInfo.parse({ openTypeOS2Panose: [1, 2, 3] }));
  assert.throws(() => ufo.FontInfo.parse({ guidelines: [{ angle: 90 }] }));
  ufo.FontInfo.parse({ unitsPerEm: 1000, guidelines: [{ x: 10 }], openTypeOS2FamilyClass: [1, 2] });
});

test("designspace example parses", () => {
  const doc = designspace.DesignspaceDocument.parse(load("generated/designspace/example.json"));
  assert.equal(doc.axes.length, 2);
  assert.deepEqual(doc.axisMappings![0]!.outputLocation, { Weight: 650, Width: 110 });
});

test("TTX JSON examples parse with the TtxFont schema", () => {
  for (const stem of ["vf-demo", "avar2-demo", "hvar-demo", "varc-demo"]) {
    const font = ttx.TtxFont.parse(load(`generated/ttx/json/${stem}.json`));
    const typed: TtxFont = font;
    assert.ok(typed.GlyphOrder.length > 0);
    assert.equal(font.fvar!.axes[0]!.axisTag, "wght");
  }
  const vf = ttx.TtxFont.parse(load("generated/ttx/json/vf-demo.json"));
  const tuples = vf.gvar!.glyphVariations["stem"]!;
  assert.ok(tuples.some((t) => t.axes["wght"]?.min !== undefined));
  assert.equal(vf.avar!.version.major, 1);
});

test("otData tables validate against the otData derived schema", () => {
  const hvar = ttx.TtxFont.parse(load("generated/ttx/json/hvar-demo.json")).HVAR;
  otdata.HVAR.parse(hvar);
  const varc = ttx.TtxFont.parse(load("generated/ttx/json/varc-demo.json")).VARC;
  otdata.VARC.parse(varc);
});

test("recursive XML AST schema", () => {
  const ast = xmlAst.XmlElement.parse(load("generated/ttx/json-ast/varc-demo.json"));
  assert.equal(ast.tag, "ttFont");
  assert.ok(ast.children.some((c) => c.tag === "VARC"));
});
