# font-format-schema

Typed models of the three source surfaces in a variable-font pipeline, derived
from the reference implementation and the specifications, and emitted as JSON
Schema, TypeScript types and Zod schemas:

| Surface | Schema | What it models | Derived from |
|---|---|---|---|
| **UFO 3** (authoring source) | `schemas/ufo.schema.json` | metainfo, every fontinfo key, lib/groups/kerning, layers, full GLIF (points with `move/line/offcurve/curve/qcurve`, `smooth`, identifiers, components, anchors, guidelines, images), the variable-components glyph.lib extension | `fontTools.ufoLib` attribute tables + `vendor/ufo-spec` markdown + `vendor/variable-components-in-ufo` |
| **Designspace 5** (interpolation source) | `schemas/designspace.schema.json` | axes (continuous and discrete), avar2 `<mappings>`, labels, sources, instances, rules, variable-font subsets | `fontTools.designspaceLib` descriptor attribute lists, asserted at generation time |
| **TTX** (compiled, fontTools XML) | `schemas/ttx.schema.json` | JSON projection of TTX for `fvar`, `avar` (v1 and v2), `gvar`, `cvar`, `glyf`, `hmtx`/`vmtx`, `cmap`, `name`, `post`, `head`/`hhea`/`vhea`/`maxp`/`OS/2` (field lists parsed from fontTools `sstruct` formats), plus a generic tree for otData tables | pinned fontTools `toXML`/`fromXML` behaviour |
| OpenType binary structures | `schemas/ttx-otdata-variation.schema.json` | fontTools `otData` struct definitions for `STAT`, `HVAR`, `VVAR`, `MVAR`, `VARC`, `avar`, VarStore, MultiVarStore, FeatureVariations... | `fontTools.ttLib.tables.otData` |
| Anything else | `schemas/xml-ast.schema.json` | ordered XML AST | – |

TTX has no XSD: it is whatever the pinned fontTools writes. This repository
therefore treats fontTools 4.64.0 as the executable reference, checks in
synthetic fonts built with it, converts their TTX to the JSON model, and
validates that JSON against the schemas in both Python and TypeScript.

## Layout

```text
schemas/                     generated JSON Schemas (2020-12)
generated/typescript/        TypeScript types (json-schema-to-typescript)
generated/zod/               Zod v4 schemas (tools/jsonschema-to-zod.ts)
generated/ufo/*.json         example UFO masters parsed into the UFO model
generated/designspace/       example designspace parsed into the Designspace model
generated/ttx/json/*.json    synthetic fonts' TTX converted to the TTX model
generated/ttx/json-ast/      focused TTX examples as XML AST
generated/ttx/               otData metadata and table inventory
examples/designspace-ufo/    Designspace 5.2 + four UFO masters (variable component, anchors, avar2 mapping)
examples/ttx-synthetic/      fontTools-built fonts: vf-demo (varLib), avar2-demo, hvar-demo, varc-demo
sources/upstreams.toml       upstream refs;  sources/ufo-spec-docs.json  tables extracted from the UFO spec
vendor/                      git submodules: fonttools @ 4.64.0, ufo-spec, variable-components-in-ufo, boring-expansion-spec
src/fontschema/schema/       schema builders (ufo.py, designspace.py, ttx.py, js.py helpers)
src/fontschema/ufo/          UFO reader (full GLIF) + semantic validation
src/fontschema/designspace/  Designspace reader + validation
src/fontschema/ttx/          TTX -> JSON (tojson.py), otData extraction, dump, round-trip validation
src/fontschema/spec/         UFO spec markdown table extractor
tools/                       Node generators (types, zod) and the JSON-Schema-to-Zod emitter
tests/  tests-ts/            pytest and node:test suites
```

## Setup

```bash
git submodule update --init          # shallow clones of fontTools 4.64.0 and the spec repos
uv sync --extra dev
npm install
```

## Build

```bash
uv run python scripts/build-synthetic-fonts.py   # examples/ttx-synthetic/*  (fontTools 4.64.0)
uv run fontschema generate                        # schemas/ + generated/*.json
npm run generate                                  # generated/typescript + generated/zod
uv run pytest -q && npm test                      # both suites
```

`make all` runs the same sequence. Tests fail if a checked-in schema is stale
relative to the generator, so regenerate after changing `src/fontschema/schema`.

## How the types are derived

**UFO.** `fontTools.ufoLib.fontInfoAttributesVersion3ValueData` lists all 108
fontinfo keys with their Python value type and the validator function bound to
each key; `schema/ufo.py` maps the types to JSON types and mirrors the
validators (width class 1–9, panose 10 ints, style map style enum, blue-zone
list lengths, WOFF metadata records, guideline x/y rules...). Descriptions,
declared types and defaults are quoted from the UFO specification tables that
`fontschema spec extract` parses out of `vendor/ufo-spec` into
`sources/ufo-spec-docs.json`. The GLIF model asserts that it covers exactly the
attribute sets `glifLib` accepts, and the `Point.type` enum carries the spec's
description of each point type under `x-point-types`.

**Designspace.** Each `fontTools.designspaceLib` descriptor declares its
serialisable attributes in `_attrs`; `schema/designspace.py` asserts that every
declared attribute is modelled, so a fontTools upgrade that adds a field fails
generation instead of silently dropping it.

**TTX.** Header tables are parsed from the fontTools `sstruct` format strings
(`headFormat`, `hheaFormat`, `OS2_format_5`, ...). The hand-written tables
(`fvar`, `avar`, `gvar`, `cvar`, `glyf`, `cmap`, `name`, ...) follow the pinned
`toXML` implementation and `ttx/tojson.py` documents the element-to-JSON
mapping. Conventions: repeated elements become arrays; `glyph=`/`axis=` keyed
elements become objects; hex, binary-string and `[list]` values become numbers.
otData tables (`STAT`, `HVAR`, `VARC`...) are converted generically into an
`OtTable` tree whose field names match the otData schema; count fields, null
offsets and packed formats that TTX omits are optional there.

## Commands

```bash
uv run fontschema ufo inspect  examples/designspace-ufo/masters/VariationDemo-Regular.ufo
uv run fontschema ufo validate examples/designspace-ufo/masters/VariationDemo-Regular.ufo   # point-sequence, component and identifier checks
uv run fontschema designspace inspect|validate examples/designspace-ufo/VariationDemo.designspace
uv run fontschema ttx tojson   examples/ttx-synthetic/vf-demo.full.ttx      # TTX -> ttx.schema.json model
uv run fontschema ttx xmljson  examples/ttx-synthetic/vf-demo.ttx           # TTX -> XML AST
uv run fontschema ttx validate examples/ttx-synthetic/vf-demo.ttf           # fontTools round-trip + fvar/VARC semantic checks
uv run fontschema ttx dump path/to/font.ttf --out generated/ttx/fonts/my-font
uv run fontschema schema validate schemas/ufo.schema.json generated/ufo/VariationDemo-Regular.json
uv run fontschema spec extract                                              # refresh sources/ufo-spec-docs.json from vendor/ufo-spec
uv run fontschema fixtures download | dump-fonts | collect-fonttools        # real fonts (Roboto Flex) and fontTools test fixtures
```

## Using the TypeScript output

```ts
import { UfoPackage, Point } from "./generated/zod/ufo.ts";
import { TtxFont } from "./generated/zod/ttx.ts";
import type { GlyphTupleVariation } from "./generated/typescript/ttx.ts";

const ufo = UfoPackage.parse(JSON.parse(text));         // validated, with GLIF defaults applied
const point = Point.parse({ x: 10, y: 20 });            // { x, y, type: "offcurve", smooth: false }
const font = TtxFont.parse(ttxJson);
const tuples: GlyphTupleVariation[] = font.gvar!.glyphVariations["A"] ?? [];
```

Every `$defs` entry is exported as a standalone Zod schema and a type of the
same name. Recursive definitions (`XmlElement`, `OtTable`/`OtValue`) are typed
against the json-schema-to-typescript output. `tools/jsonschema-to-zod.ts`
supports exactly the keyword subset the Python builders emit and throws on
anything else, so a generator change cannot silently weaken the validators.

## Extending the model

The schemas are the contract between authoring, compilation and usage in this
pipeline. Extensions (for example 3D points, lofts, or per-glyph axes beyond
what variable-components-in-ufo defines) belong in new `$defs` next to the
UFO ones — `Point` for a `z` coordinate, `GlyphLib` for new `public.`-style
keys, `GlyphDesignspace` for local axes — with matching TTX-side structures in
`schema/ttx.py`. The Python readers, the JSON examples and both test suites
then verify the round trip the same way they do for the standard formats.

## Upstreams

`vendor/` holds shallow submodules pinned in `.gitmodules`; `sources/upstreams.toml`
records the intended refs. `fontschema sources sync` can alternatively clone
them into `.cache/upstreams/` and `sources status` reports what is active.
Type data always comes from the *installed* fontTools (`uv.lock`), not from the
submodule; the submodule provides the `Tests/` fixtures for
`fixtures collect-fonttools` and documentation provenance.

- fontTools: <https://github.com/fonttools/fonttools>
- Designspace XML docs: <https://fonttools.readthedocs.io/en/latest/designspaceLib/xml.html>
- UFO specification: <https://github.com/unified-font-object/ufo-spec>
- Variable Components in UFO: <https://github.com/fontra/variable-components-in-ufo>
- avar2 / VARC design docs: <https://github.com/harfbuzz/boring-expansion-spec>
- Microsoft OpenType spec: <https://learn.microsoft.com/typography/opentype/spec/>
