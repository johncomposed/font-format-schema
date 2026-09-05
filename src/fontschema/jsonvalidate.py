from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def validate_json(schema_path: str | Path, data_path: str | Path) -> dict[str, Any]:
    schema_path = Path(schema_path)
    data_path = Path(data_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(data_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(x) for x in error.absolute_path)
        errors.append({"path": path, "message": error.message})
    return {"schema": str(schema_path), "data": str(data_path), "errors": errors}
