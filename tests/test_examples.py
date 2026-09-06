import json

import pytest
from jsonschema import Draft202012Validator

from fontschema.common import repo_root
from fontschema.designspace.reader import inspect as inspect_designspace, validate as validate_designspace
from fontschema.ufo.reader import inspect as inspect_ufo, validate as validate_ufo

ROOT = repo_root()
MASTERS = sorted((ROOT / "examples/designspace-ufo/masters").glob("*.ufo"))


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, data) -> list[str]:
    return [f"/{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validator.iter_errors(data)]


def test_designspace_example_validates_semantically():
    assert not validate_designspace(ROOT / "examples/designspace-ufo/VariationDemo.designspace")["errors"]


def test_designspace_example_matches_schema():
    data = inspect_designspace(ROOT / "examples/designspace-ufo/VariationDemo.designspace")
    assert not _errors(_validator("designspace"), data)
    assert data["formatVersion"] == "5.2"
    assert data["axisMappings"][0]["inputLocation"] == {"Weight": 700, "Width": 120}


@pytest.mark.parametrize("ufo", MASTERS, ids=[p.stem for p in MASTERS])
def test_ufo_masters_validate_and_match_schema(ufo):
    assert not validate_ufo(ufo)["errors"]
    data = inspect_ufo(ufo)
    assert not _errors(_validator("ufo"), data)


def test_ufo_reader_captures_glif_details():
    data = inspect_ufo(ROOT / "examples/designspace-ufo/masters/VariationDemo-Regular.ufo")
    glyphs = data["layers"][0]["glyphs"]
    stem = glyphs["stem"]
    points = stem["outline"]["contours"][0]["points"]
    assert [p["type"] for p in points] == ["line"] * 4
    assert stem["anchors"] == [{"x": 150, "y": 700, "name": "top"}]
    composite = glyphs["composite"]
    assert composite["outline"]["components"][0]["base"] == "stem"
    var = glyphs["varComposite"]["lib"]["com.black-foundry.variable-components"][0]
    assert var["base"] == "stem"
    assert var["location"] == {"Weight": 700, "Width": 75}
    assert var["transformation"]["translateX"] == 40


def test_ufo_validator_rejects_bad_point_sequences(tmp_path):
    from fontschema.ufo.reader import _check_contour

    errors: list[str] = []
    # line after an offcurve point
    _check_contour("g", 0, [{"x": 0, "y": 0, "type": "offcurve"}, {"x": 1, "y": 1, "type": "line"}], errors)
    assert errors and "preceded by 1 offcurve" in errors[0]
    errors.clear()
    # cubic curve with three off-curves
    pts = [{"x": 0, "y": 0, "type": "curve"}] + [{"x": i, "y": i, "type": "offcurve"} for i in range(3)] + [{"x": 9, "y": 9, "type": "curve"}]
    _check_contour("g", 0, pts, errors)
    assert errors and "max 2" in errors[0]
    errors.clear()
    # valid: closed cubic contour, cyclic lookup
    pts = [{"x": 0, "y": 0, "type": "offcurve"}, {"x": 1, "y": 1, "type": "offcurve"}, {"x": 2, "y": 2, "type": "curve", "smooth": True}]
    _check_contour("g", 0, pts, errors)
    assert not errors
    # valid: quadratic contour with only offcurve points
    _check_contour("g", 0, [{"x": 0, "y": 0, "type": "offcurve"}] * 3, errors)
    assert not errors
