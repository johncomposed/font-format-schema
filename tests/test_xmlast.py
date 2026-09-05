from pathlib import Path
from fontschema.xmlast import xml_file_to_ast


def test_xml_ast_preserves_repeated_children(tmp_path: Path):
    p = tmp_path / "x.xml"
    p.write_text('<root><item value="1"/><item value="2"/></root>')
    ast = xml_file_to_ast(p)
    assert [x["attributes"]["value"] for x in ast["children"]] == ["1", "2"]
