from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common import dump_json, repo_root
from ..ttx.otdata import extract_variation_otdata, otdata_json_schema, otdata_typescript, table_inventory


def xml_ast_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:xml-ast",
        "title": "Ordered XML AST",
        "$ref": "#/$defs/element",
        "$defs": {
            "element": {
                "type": "object",
                "required": ["tag", "attributes", "children"],
                "properties": {
                    "tag": {"type": "string"},
                    "attributes": {"type": "object", "additionalProperties": {"type": "string"}},
                    "text": {"type": "string"},
                    "children": {"type": "array", "items": {"$ref": "#/$defs/element"}},
                },
                "additionalProperties": False,
            }
        },
    }


def variation_schema() -> dict[str, Any]:
    num = {"type": "number"}
    transform = {
        "type": "object",
        "properties": {
            "translateX": num, "translateY": num, "rotation": num,
            "scaleX": num, "scaleY": num, "skewX": num, "skewY": num,
            "tCenterX": num, "tCenterY": num,
        },
        "additionalProperties": False,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:canonical-variation",
        "title": "Canonical variation-oriented font source model",
        "$defs": {
            "Axis": {
                "type": "object", "required": ["name", "tag", "default"],
                "properties": {
                    "name": {"type": "string"}, "tag": {"type": "string", "minLength": 4, "maxLength": 4},
                    "minimum": num, "default": num, "maximum": num,
                }, "additionalProperties": False,
            },
            "DecomposedTransform": transform,
            "VariableComponent": {
                "type": "object", "required": ["base"],
                "properties": {
                    "base": {"type": "string"},
                    "location": {"type": "object", "additionalProperties": num},
                    "transformation": {"$ref": "#/$defs/DecomposedTransform"},
                    "resetUnspecifiedAxes": {"type": "boolean"},
                }, "additionalProperties": False,
            },
            "AffineComponent": {
                "type": "object", "required": ["base", "transform"],
                "properties": {
                    "base": {"type": "string"},
                    "transform": {
                        "type": "object",
                        "required": ["xScale", "xyScale", "yxScale", "yScale", "xOffset", "yOffset"],
                        "properties": {k: num for k in ["xScale", "xyScale", "yxScale", "yScale", "xOffset", "yOffset"]},
                        "additionalProperties": False,
                    },
                }, "additionalProperties": True,
            },
        },
        "oneOf": [
            {"$ref": "#/$defs/Axis"},
            {"$ref": "#/$defs/VariableComponent"},
            {"$ref": "#/$defs/AffineComponent"},
        ],
    }


def designspace_schema() -> dict[str, Any]:
    num = {"type": ["number", "null"]}
    location = {"type": "object", "additionalProperties": {"type": "number"}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:designspace-normalized",
        "type": "object", "required": ["formatVersion", "axes", "mappings", "sources", "instances", "rules"],
        "properties": {
            "path": {"type": "string"}, "formatVersion": {"type": "string"},
            "axes": {"type": "array", "items": {"type": "object", "required": ["name", "tag", "default"], "properties": {
                "name": {"type": "string"}, "tag": {"type": "string"}, "minimum": num, "default": {"type": "number"}, "maximum": num,
                "hidden": {"type": "boolean"}, "map": {"type": "array"}, "values": {"type": "array", "items": {"type": "number"}},
            }, "additionalProperties": True}},
            "mappings": {"type": "array", "items": {"type": "object", "required": ["input", "output"], "properties": {"input": location, "output": location, "description": {"type": ["string", "null"]}}, "additionalProperties": False}},
            "sources": {"type": "array", "items": {"type": "object", "required": ["location"], "properties": {"location": location}, "additionalProperties": True}},
            "instances": {"type": "array", "items": {"type": "object", "required": ["location"], "properties": {"location": location}, "additionalProperties": True}},
            "rules": {"type": "array"},
        }, "additionalProperties": True,
    }


def ufo_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:font-format-schema:ufo-normalized",
        "type": "object", "required": ["glyphCount", "glyphs"],
        "properties": {
            "path": {"type": "string"}, "formatVersion": {"type": "integer"}, "glyphCount": {"type": "integer", "minimum": 0},
            "glyphs": {"type": "array", "items": {"type": "object", "required": ["name", "components", "anchors", "variableComponents"], "properties": {
                "name": {"type": "string"}, "layer": {"type": "string"}, "file": {"type": "string"}, "width": {"type": ["number", "null"]},
                "components": {"type": "array"}, "anchors": {"type": "array"}, "variableComponents": {"type": "array"},
                "glyphDesignspace": {},
            }, "additionalProperties": True}},
        }, "additionalProperties": True,
    }


def canonical_typescript() -> str:
    return '''// Generated. Canonical source-oriented types.

export type AxisTag = string;
export type Location = Record<string, number>;

export interface Axis {
  name: string;
  tag: AxisTag;
  minimum?: number | null;
  default: number;
  maximum?: number | null;
  hidden?: boolean;
  map?: [number, number][];
  values?: number[];
}

export interface DecomposedTransform {
  translateX?: number;
  translateY?: number;
  rotation?: number;
  scaleX?: number;
  scaleY?: number;
  skewX?: number;
  skewY?: number;
  tCenterX?: number;
  tCenterY?: number;
}

export interface VariableComponent {
  base: string;
  location?: Location;
  transformation?: DecomposedTransform;
  resetUnspecifiedAxes?: boolean;
}

export interface AffineTransform {
  xScale: number;
  xyScale: number;
  yxScale: number;
  yScale: number;
  xOffset: number;
  yOffset: number;
}

export interface AffineComponent {
  base: string;
  transform: AffineTransform;
  identifier?: string | null;
}

export interface Anchor {
  name?: string | null;
  x: number;
  y: number;
  identifier?: string | null;
}

export interface NormalizedGlyph {
  name: string;
  layer: string;
  file: string;
  width: number | null;
  components: AffineComponent[];
  anchors: Anchor[];
  variableComponents: VariableComponent[];
  glyphDesignspace?: unknown;
}

export interface UfoNormalized {
  path: string;
  formatVersion: number;
  glyphCount: number;
  glyphs: NormalizedGlyph[];
}

export interface DesignspaceMapping {
  input: Location;
  output: Location;
  description?: string | null;
}

export interface DesignspaceSource {
  name?: string | null;
  filename?: string | null;
  layerName?: string | null;
  familyName?: string | null;
  styleName?: string | null;
  location: Location;
}

export interface DesignspaceInstance {
  name?: string | null;
  filename?: string | null;
  familyName?: string | null;
  styleName?: string | null;
  location: Location;
}

export interface DesignspaceNormalized {
  path: string;
  formatVersion: string;
  axes: Axis[];
  mappings: DesignspaceMapping[];
  sources: DesignspaceSource[];
  instances: DesignspaceInstance[];
  rules: unknown[];
}

export interface XmlAstElement {
  tag: string;
  attributes: Record<string, string>;
  text?: string;
  children: XmlAstElement[];
}
'''


def generate_all() -> list[Path]:
    root = repo_root()
    meta = extract_variation_otdata()
    outputs: list[Path] = []
    payloads = {
        root / "generated/ttx/otdata-variation.json": meta,
        root / "generated/ttx/table-inventory.json": table_inventory(),
        root / "schemas/ttx-otdata-variation.schema.json": otdata_json_schema(meta),
        root / "schemas/xml-ast.schema.json": xml_ast_schema(),
        root / "schemas/canonical-variation.schema.json": variation_schema(),
        root / "schemas/designspace-normalized.schema.json": designspace_schema(),
        root / "schemas/ufo-normalized.schema.json": ufo_schema(),
    }
    for path, data in payloads.items():
        dump_json(data, path)
        outputs.append(path)
    ts1 = root / "generated/typescript/font-variation.ts"
    ts1.parent.mkdir(parents=True, exist_ok=True)
    ts1.write_text(canonical_typescript(), encoding="utf-8")
    outputs.append(ts1)
    ts2 = root / "generated/typescript/opentype-variation-otdata.ts"
    ts2.write_text(otdata_typescript(meta), encoding="utf-8")
    outputs.append(ts2)
    return outputs
