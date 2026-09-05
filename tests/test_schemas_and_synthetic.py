from pathlib import Path

from fontschema.common import repo_root
from fontschema.jsonvalidate import validate_json
from fontschema.ttx.validate import validate as validate_ttx


def test_synthetic_fonts_and_full_ttx_roundtrip():
    root = repo_root() / "examples" / "ttx-synthetic"
    for stem in ["avar2-demo", "hvar-demo", "varc-demo"]:
        assert not validate_ttx(root / f"{stem}.ttf")["errors"]
        assert not validate_ttx(root / f"{stem}.full.ttx")["errors"]


def test_generated_normalized_examples_match_json_schemas():
    root = repo_root()
    cases = [
        ("schemas/designspace-normalized.schema.json", "generated/designspace/example.json"),
        ("schemas/ufo-normalized.schema.json", "generated/ufo/example.json"),
        ("schemas/xml-ast.schema.json", "generated/ttx/json-ast/varc-demo.json"),
        ("schemas/xml-ast.schema.json", "generated/ttx/json-ast/avar2-demo.json"),
    ]
    for schema, data in cases:
        assert not validate_json(root / schema, root / data)["errors"]
