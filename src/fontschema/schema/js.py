"""Tiny helpers for building JSON Schema 2020-12 documents in Python."""
from __future__ import annotations

from typing import Any

DRAFT = "https://json-schema.org/draft/2020-12/schema"


def desc(schema: dict[str, Any], text: str | None) -> dict[str, Any]:
    if text:
        schema = {**schema, "description": text}
    return schema


def string(description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "string", **kw}, description)


def number(description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "number", **kw}, description)


def integer(description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "integer", **kw}, description)


def boolean(description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "boolean", **kw}, description)


def const(value: Any, description: str | None = None) -> dict[str, Any]:
    return desc({"const": value}, description)


def enum(values: list[Any], description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"enum": values, **kw}, description)


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    if "type" in schema and isinstance(schema["type"], str):
        return {**schema, "type": [schema["type"], "null"]}
    return {"anyOf": [schema, {"type": "null"}]}


def array(items: dict[str, Any], description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "array", "items": items, **kw}, description)


def tuple_(items: list[dict[str, Any]], description: str | None = None) -> dict[str, Any]:
    return desc(
        {"type": "array", "prefixItems": items, "minItems": len(items), "maxItems": len(items), "items": False},
        description,
    )


def record(values: dict[str, Any], description: str | None = None, **kw: Any) -> dict[str, Any]:
    return desc({"type": "object", "additionalProperties": values, **kw}, description)


def obj(
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
    description: str | None = None,
    additional: bool | dict[str, Any] = False,
    **kw: Any,
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = list(required)
    schema["additionalProperties"] = additional
    schema.update(kw)
    return desc(schema, description)


def ref(name: str, description: str | None = None) -> dict[str, Any]:
    return desc({"$ref": f"#/$defs/{name}"}, description)


def any_of(*schemas: dict[str, Any], description: str | None = None) -> dict[str, Any]:
    return desc({"anyOf": list(schemas)}, description)


def one_of(*schemas: dict[str, Any], description: str | None = None) -> dict[str, Any]:
    return desc({"oneOf": list(schemas)}, description)


def document(
    id_: str, title: str, root: str, defs: dict[str, Any], description: str | None = None
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "$schema": DRAFT,
        "$id": f"urn:font-format-schema:{id_}",
        "title": title,
    }
    if description:
        doc["description"] = description
    doc["$ref"] = f"#/$defs/{root}"
    doc["$defs"] = defs
    return doc
