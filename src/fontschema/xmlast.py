from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def element_to_ast(el: ET.Element) -> dict[str, Any]:
    node: dict[str, Any] = {
        "tag": el.tag,
        "attributes": dict(el.attrib),
        "children": [element_to_ast(child) for child in list(el)],
    }
    if el.text and el.text.strip():
        node["text"] = el.text.strip()
    return node


def xml_file_to_ast(path: str | Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    return element_to_ast(root)
