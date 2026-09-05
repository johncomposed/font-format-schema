from __future__ import annotations

from pathlib import Path
from fontTools.ttLib import TTFont

DEFAULT_TABLES = ["fvar", "avar", "STAT", "gvar", "cvar", "HVAR", "VVAR", "MVAR", "VARC", "CFF2", "GDEF", "GPOS", "GSUB", "BASE"]


def dump_font(font_path: str | Path, out_dir: str | Path, tables: list[str] | None = None) -> list[Path]:
    font_path = Path(font_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    font = TTFont(font_path, lazy=False)
    selected = [tag for tag in (tables or DEFAULT_TABLES) if tag in font]
    outputs: list[Path] = []
    full = out_dir / "variation.ttx"
    font.saveXML(full, tables=selected)
    outputs.append(full)
    for tag in selected:
        p = out_dir / f"{tag}.ttx"
        font.saveXML(p, tables=[tag])
        outputs.append(p)
    return outputs
