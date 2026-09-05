# font-format-schema

A variation-focused reference and validation pipeline for three related source surfaces:

1. **TTX / compiled OpenType** — derive structure metadata from fontTools, dump real fonts and fontTools fixtures, round-trip TTX, and run cross-table semantic checks.
2. **Designspace** — parse current Designspace 5.x constructs, including `<mappings>` used to compile `avar` version 2 behavior.
3. **UFO / GLIF** — inspect standard components, transforms, anchors and glyph libs, including the variable-components UFO extension.

The repository intentionally does **not** pretend there is a separate normative “TTX XSD.” TTX is fontTools' XML serialization. For TTX, the build pipeline treats the pinned fontTools implementation and its tests as the executable reference.

## Layout

```text
sources/                     declared upstream refs + font fixture manifests
vendor/                      optional git subtrees; ignored by default
.cache/upstreams/            default cloned upstream cache
src/fontschema/ttx/          TTX/OpenType extraction + validation
src/fontschema/designspace/  Designspace normalization + validation
src/fontschema/ufo/          UFO/GLIF normalization + validation
src/fontschema/schema/       canonical JSON Schema + TypeScript generation
examples/designspace-ufo/    small source-format fixtures
schemas/                     generated JSON Schemas
generated/typescript/        generated TypeScript declarations
generated/ttx/               fontTools schema inventory / fixture dumps
```

## Setup

```bash
uv sync --extra dev
uv run fontschema generate
uv run pytest -q
```

No `uv.lock` is fabricated in this archive because the assembly environment could not resolve the 4.64.0 wheel from PyPI. The first networked `uv sync` will resolve the pinned runtime and create the lockfile; commit that lockfile if you want fully frozen application-style builds.

`fonttools==4.64.0` is the target runtime pin. The extraction code depends on the `FieldSpec` representation introduced in 4.63.0; updates are intentionally explicit so generated snapshots can be reviewed. The checked-in bootstrap snapshots were produced with 4.63.0 in the build environment used to assemble this repo; `uv run fontschema generate` and `uv run python scripts/build-synthetic-fonts.py` refresh them under the pinned 4.64.0 runtime.

## Upstream source modes

The tooling supports two ways to reference upstream source.

### Cache clones

This is the default and does not modify your repository history:

```bash
uv run fontschema sources sync
uv run fontschema sources status
```

It clones exact refs from `sources/upstreams.toml` to `.cache/upstreams/`.

### Git subtrees

If you want upstream source committed into this repository:

```bash
./scripts/vendor-init.sh
```

That runs `git subtree add --squash` for the same manifest entries. Later:

```bash
./scripts/vendor-update.sh
```

Spec repositories declared at `main` intentionally follow upstream development. `fontschema sources sync` records their resolved commit hashes in `.cache/upstreams-lock.json`. For a release/tag such as fontTools, edit the manifest ref deliberately before updating.

## Generate schemas and TypeScript

```bash
uv run fontschema generate
```

This creates:

- `generated/ttx/otdata-variation.json` — recursive fontTools `otData` metadata for variation-related tables and structures.
- `generated/ttx/table-inventory.json` — which variation tables are schema-driven versus custom fontTools handlers.
- `schemas/canonical-variation.schema.json`
- `schemas/designspace-normalized.schema.json`
- `schemas/ufo-normalized.schema.json`
- `schemas/xml-ast.schema.json`
- `generated/typescript/font-variation.ts`
- `generated/typescript/opentype-variation-otdata.ts`

The `otData` output is deliberately metadata-rich rather than claiming to be a perfect schema of TTX XML. Some TTX tables have custom `toXML` / `fromXML` behavior; `VARC`, `avar`, `gvar`, `cvar`, `fvar`, and CFF2-related serialization need implementation-aware handling.

## Checked-in synthetic TTX examples

The repo includes tiny fontTools-generated examples that do not require network access:

```text
examples/ttx-synthetic/avar2-demo.ttx
examples/ttx-synthetic/hvar-demo.ttx
examples/ttx-synthetic/varc-demo.ttx
```

Each also has a compiled `.ttf` and a `*.full.ttx` round-trippable full-font dump. Regenerate them with:

```bash
uv run python scripts/build-synthetic-fonts.py
```

## Real font fixtures

Download the font manifest:

```bash
uv run fontschema fixtures download
uv run fontschema fixtures dump-fonts
```

The second command dumps only variation-relevant tables by default. You can also dump any local font:

```bash
uv run fontschema ttx dump path/to/font.ttf --out generated/ttx/fonts/my-font
```

Default table set:

```text
fvar avar STAT gvar cvar HVAR VVAR MVAR VARC CFF2 GDEF GPOS GSUB BASE
```

Only tables present in the font are written.

## fontTools targeted fixtures

New structures such as `VARC` and `avar2` may not occur in a production fixture. After syncing or vendoring fontTools:

```bash
uv run fontschema fixtures collect-fonttools
```

The collector searches fontTools tests for variation-related `.ttx`, `.ttf`, `.otf`, `.designspace`, `.ufo` and XML fixtures, copies them into `generated/ttx/fonttools-fixtures/`, and writes an inventory with original paths.

## TTX → JSON AST

For exact XML preservation use the generic XML AST conversion rather than a lossy object conversion:

```bash
uv run fontschema ttx xmljson input.ttx --out input.ttx.json
```

Shape:

```json
{
  "tag": "VarComponent",
  "attributes": {"index": "0"},
  "children": [
    {"tag": "glyphName", "attributes": {"value": "acute"}, "children": []}
  ]
}
```

This preserves repeated elements and ordering. `schemas/xml-ast.schema.json` validates the representation.

Any generated JSON can be checked against a JSON Schema with:

```bash
uv run fontschema schema validate schemas/xml-ast.schema.json input.ttx.json
uv run fontschema schema validate schemas/designspace-normalized.schema.json generated/designspace/example.json
```

## TTX validation

Binary font:

```bash
uv run fontschema ttx validate font.ttf
```

TTX:

```bash
uv run fontschema ttx validate font.ttx
```

Validation includes XML parsing, fontTools import/compile round-trip when possible, and variation semantic checks such as `fvar` axis bounds and `VARC` axis-index/axis-value consistency.

## Designspace

Inspect/normalize:

```bash
uv run fontschema designspace inspect examples/designspace-ufo/VariationDemo.designspace \
  --out generated/designspace/example.json
```

Validate:

```bash
uv run fontschema designspace validate examples/designspace-ufo/VariationDemo.designspace
```

The included example is Designspace 5.2 and contains a multi-axis `<mappings>` entry as an `avar2`-oriented source example.

## UFO / GLIF

Inspect a UFO into JSON:

```bash
uv run fontschema ufo inspect examples/designspace-ufo/masters/VariationDemo-Regular.ufo \
  --out generated/ufo/example.json
```

The normalized representation includes standard GLIF `<component>` affine transforms and variable components stored under `com.black-foundry.variable-components`.

## Why two validation layers

Structural validation can check shapes and scalar types. Font data also contains cross-references that JSON Schema cannot express conveniently, for example:

- a `VARC` `axisIndicesIndex` must reference an item in `AxisIndicesList`;
- each variable component's `axisValues` length must match its referenced axis-index tuple;
- each axis index must be less than the `fvar` axis count;
- a Designspace mapping can only refer to known axis names.

Those checks live in Python and complement the generated JSON schemas.

## Authoritative/reference inputs

- fontTools: <https://github.com/fonttools/fonttools>
- Designspace XML docs: <https://fonttools.readthedocs.io/en/latest/designspaceLib/xml.html>
- UFO specification: <https://github.com/unified-font-object/ufo-spec>
- Variable Components in UFO: <https://github.com/fontra/variable-components-in-ufo>
- avar2 / VARC public design docs: <https://github.com/harfbuzz/boring-expansion-spec>
- Microsoft OpenType spec: <https://learn.microsoft.com/typography/opentype/spec/>
- ISO/IEC 14496-22:2026: normative Open Font Format edition where applicable; the ISO text is not vendored because it is not an open Git repository.
