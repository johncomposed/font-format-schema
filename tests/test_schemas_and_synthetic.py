import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from fontschema.common import repo_root
from fontschema.jsonvalidate import validate_json
from fontschema.schema.generate import SCHEMAS
from fontschema.ttx.tojson import ot_table_to_json, parse_value, ttx_file_to_json
from fontschema.ttx.validate import validate as validate_ttx

ROOT = repo_root()
SYNTHETIC = ROOT / "examples" / "ttx-synthetic"
STEMS = ["vf-demo", "avar2-demo", "hvar-demo", "varc-demo"]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def test_all_schemas_are_valid_2020_12():
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_checked_in_schemas_match_generator():
    """`fontschema generate` must have been run after changing the generator."""
    for name, builder in SCHEMAS.items():
        assert builder() == _schema(name), f"schemas/{name}.schema.json is stale; run `uv run fontschema generate`"


@pytest.mark.parametrize("stem", STEMS)
def test_synthetic_fonts_and_full_ttx_roundtrip(stem):
    assert not validate_ttx(SYNTHETIC / f"{stem}.ttf")["errors"]
    assert not validate_ttx(SYNTHETIC / f"{stem}.full.ttx")["errors"]


@pytest.mark.parametrize("stem", STEMS)
def test_ttx_json_matches_schema(stem):
    data = ttx_file_to_json(SYNTHETIC / f"{stem}.full.ttx")
    errors = list(Draft202012Validator(_schema("ttx")).iter_errors(data))
    assert not errors, [e.message for e in errors]
    checked_in = json.loads((ROOT / "generated/ttx/json" / f"{stem}.json").read_text(encoding="utf-8"))
    assert checked_in == data


def test_vf_demo_core_tables():
    data = ttx_file_to_json(SYNTHETIC / "vf-demo.full.ttx")
    fvar = data["fvar"]
    assert [a["axisTag"] for a in fvar["axes"]] == ["wght", "wdth"]
    # design 80 on map [(100,0),(400,40),(600,50),(900,100)] -> user 780
    assert fvar["instances"][0]["coordinates"] == {"wght": 780.0, "wdth": 100.0}
    avar = data["avar"]
    assert avar["version"] == {"major": 1, "minor": 0}
    assert {"from": 0.4, "to": 0.1667} in avar["segments"]["wght"]
    gvar = data["gvar"]
    tuples = gvar["glyphVariations"]["stem"]
    # An intermediate master produces a tuple with an explicit region.
    assert any("min" in t["axes"].get("wght", {}) for t in tuples)
    assert all({"pt", "x", "y"} == set(d) for t in tuples for d in t["deltas"])
    cvar = data["cvar"]
    assert all({"cvt", "value"} == set(d) for t in cvar["variations"] for d in t["deltas"])
    glyf = data["glyf"]["glyphs"]
    assert glyf["archstem"]["components"][0]["glyphName"] == "stem"
    assert [p["on"] for p in glyf["arch"]["contours"][0]["points"]] == [True, False, True]
    assert data["hmtx"][0] == {"name": ".notdef", "width": 540, "lsb": 50}
    assert data["cmap"]["subtables"][0]["map"]["65"] == "arch"
    assert data["head"]["unitsPerEm"] == 1000 and isinstance(data["head"]["flags"], int)
    assert data["STAT"]["DesignAxisRecord"]["Axis"][0]["AxisTag"] == "wght"
    assert data["HVAR"]["VarStore"]["VarRegionList"]["Region"][0]["VarRegionAxis"][0]["PeakCoord"] == -1.0


def _lenient(schema):
    """otData describes binary structs; TTX omits null offsets, counts and
    fields written by custom converters (e.g. VarIdxMap -> <Map> records), so
    only check the types of the fields that are present."""
    if isinstance(schema, dict):
        return {k: _lenient(v) for k, v in schema.items() if k != "required"}
    if isinstance(schema, list):
        return [_lenient(v) for v in schema]
    return schema


@pytest.mark.parametrize("stem,table", [("hvar-demo", "HVAR"), ("varc-demo", "VARC"), ("vf-demo", "STAT")])
def test_otdata_json_field_types_match_otdata_schema(stem, table):
    data = ttx_file_to_json(SYNTHETIC / f"{stem}.full.ttx")[table]
    schema = _lenient(_schema("ttx-otdata-variation"))
    schema.pop("oneOf")
    validator = Draft202012Validator({**schema, "$ref": f"#/$defs/{table}"})
    errors = [e.message for e in validator.iter_errors(data)]
    assert not errors, errors


def test_parse_value():
    assert parse_value("0x1F") == 31
    assert parse_value("00000000 00000011") == 3
    assert parse_value("1.0") == 1.0
    assert parse_value("[0.5, -1]") == [0.5, -1]
    assert parse_value("parent") == "parent"


def test_generated_examples_match_json_schemas():
    cases = [
        ("designspace", "generated/designspace/example.json"),
        ("ufo", "generated/ufo/VariationDemo-Regular.json"),
        ("xml-ast", "generated/ttx/json-ast/varc-demo.json"),
        ("xml-ast", "generated/ttx/json-ast/avar2-demo.json"),
    ]
    for schema, data in cases:
        assert not validate_json(ROOT / "schemas" / f"{schema}.schema.json", ROOT / data)["errors"]
