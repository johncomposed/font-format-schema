from pathlib import Path
from fontschema.common import repo_root
from fontschema.designspace.reader import validate as validate_designspace
from fontschema.ufo.reader import validate as validate_ufo


def test_designspace_example():
    p = repo_root() / "examples/designspace-ufo/VariationDemo.designspace"
    assert not validate_designspace(p)["errors"]


def test_ufo_example():
    p = repo_root() / "examples/designspace-ufo/masters/VariationDemo-Regular.ufo"
    assert not validate_ufo(p)["errors"]
