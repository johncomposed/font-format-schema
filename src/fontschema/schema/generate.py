"""Generate every schema and example JSON document in the repository.

Outputs (all deterministic for the pinned fontTools version):

schemas/
  ufo.schema.json                  UFO 3 package model (fontinfo, GLIF, lib, groups, kerning, layers)
  designspace.schema.json          Designspace 5 document model
  ttx.schema.json                  JSON projection of TTX for the core variable-font tables
  ttx-otdata-variation.schema.json fontTools otData structures for variation tables
  xml-ast.schema.json              generic ordered XML AST
generated/
  ttx/otdata-variation.json        raw otData metadata
  ttx/table-inventory.json         which tables are otData driven vs custom
  ttx/json/<stem>.json             examples/ttx-synthetic/*.full.ttx converted to the TTX JSON model
  ttx/json-ast/<stem>.json         the focused .ttx examples as XML AST
  designspace/example.json         examples/designspace-ufo/VariationDemo.designspace
  ufo/<master>.json                every master UFO in examples/designspace-ufo

TypeScript types and Zod schemas are generated from the schemas by the Node
toolchain (``npm run generate``), see tools/.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common import dump_json, repo_root
from ..designspace.reader import inspect as inspect_designspace
from ..ttx.otdata import extract_variation_otdata, otdata_json_schema, table_inventory
from ..ttx.tojson import ttx_file_to_json
from ..ufo.reader import inspect as inspect_ufo
from ..xmlast import xml_file_to_ast
from .designspace import designspace_schema
from .ttx import ttx_schema
from .ufo import ufo_schema


def xml_ast_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:xml-ast",
        "title": "Ordered XML AST",
        "$ref": "#/$defs/XmlElement",
        "$defs": {
            "XmlElement": {
                "type": "object",
                "required": ["tag", "attributes", "children"],
                "properties": {
                    "tag": {"type": "string"},
                    "attributes": {"type": "object", "additionalProperties": {"type": "string"}},
                    "text": {"type": "string"},
                    "children": {"type": "array", "items": {"$ref": "#/$defs/XmlElement"}},
                },
                "additionalProperties": False,
            }
        },
    }


SCHEMAS = {
    "ufo": ufo_schema,
    "designspace": designspace_schema,
    "ttx": ttx_schema,
    "xml-ast": xml_ast_schema,
}


def generate_schemas(root: Path) -> list[Path]:
    outputs: list[Path] = []
    meta = extract_variation_otdata()
    payloads: dict[Path, Any] = {
        root / "generated/ttx/otdata-variation.json": meta,
        root / "generated/ttx/table-inventory.json": table_inventory(),
        root / "schemas/ttx-otdata-variation.schema.json": otdata_json_schema(meta),
    }
    for name, builder in SCHEMAS.items():
        payloads[root / f"schemas/{name}.schema.json"] = builder()
    for path, data in payloads.items():
        dump_json(data, path)
        outputs.append(path)
    return outputs


def generate_examples(root: Path) -> list[Path]:
    outputs: list[Path] = []
    examples = root / "examples"
    ds = examples / "designspace-ufo" / "VariationDemo.designspace"
    if ds.exists():
        out = root / "generated/designspace/example.json"
        dump_json(inspect_designspace(ds.relative_to(root).as_posix()), out)
        outputs.append(out)
    for ufo in sorted((examples / "designspace-ufo" / "masters").glob("*.ufo")):
        out = root / "generated/ufo" / f"{ufo.stem}.json"
        dump_json(inspect_ufo(ufo.relative_to(root).as_posix()), out)
        outputs.append(out)
    for ttx in sorted((examples / "ttx-synthetic").glob("*.full.ttx")):
        stem = ttx.name[: -len(".full.ttx")]
        out = root / "generated/ttx/json" / f"{stem}.json"
        dump_json(ttx_file_to_json(ttx), out)
        outputs.append(out)
    for ttx in sorted((examples / "ttx-synthetic").glob("*.ttx")):
        if ttx.name.endswith(".full.ttx"):
            continue
        out = root / "generated/ttx/json-ast" / f"{ttx.stem}.json"
        dump_json(xml_file_to_ast(ttx), out)
        outputs.append(out)
    return outputs


def generate_all() -> list[Path]:
    root = repo_root()
    # Paths are relative to the repository so the JSON is stable across machines.
    import os

    cwd = os.getcwd()
    os.chdir(root)
    try:
        outputs = generate_schemas(root)
        outputs += generate_examples(root)
    finally:
        os.chdir(cwd)
    return outputs
