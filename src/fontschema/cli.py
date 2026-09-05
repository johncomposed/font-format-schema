from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import dump_json
from .designspace.reader import inspect as inspect_designspace, validate as validate_designspace
from .fixtures import collect_fonttools, download_fonts, dump_fonts
from .jsonvalidate import validate_json
from .schema.generate import generate_all
from .sources import status as source_status, subtree_init, subtree_update, sync_cache
from .ttx.dump import dump_font
from .ttx.validate import validate as validate_ttx
from .ufo.reader import inspect as inspect_ufo, validate as validate_ufo
from .xmlast import xml_file_to_ast


def _emit(data, out: str | None = None):
    text = dump_json(data, out)
    if out is None:
        print(text, end="")


def main() -> None:
    p = argparse.ArgumentParser(prog="fontschema")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("generate")

    schema = sp.add_parser("schema")
    schsp = schema.add_subparsers(dest="schema_cmd", required=True)
    sv = schsp.add_parser("validate"); sv.add_argument("schema"); sv.add_argument("data")

    sources = sp.add_parser("sources")
    ssp = sources.add_subparsers(dest="sources_cmd", required=True)
    ssp.add_parser("status")
    ssp.add_parser("sync")
    ssp.add_parser("subtree-init")
    ssp.add_parser("subtree-update")

    ttx = sp.add_parser("ttx")
    tsp = ttx.add_subparsers(dest="ttx_cmd", required=True)
    d = tsp.add_parser("dump"); d.add_argument("font"); d.add_argument("--out", required=True); d.add_argument("--tables", nargs="*")
    x = tsp.add_parser("xmljson"); x.add_argument("xml"); x.add_argument("--out")
    v = tsp.add_parser("validate"); v.add_argument("path")

    ds = sp.add_parser("designspace")
    dsp = ds.add_subparsers(dest="ds_cmd", required=True)
    i = dsp.add_parser("inspect"); i.add_argument("path"); i.add_argument("--out")
    v = dsp.add_parser("validate"); v.add_argument("path")

    ufo = sp.add_parser("ufo")
    usp = ufo.add_subparsers(dest="ufo_cmd", required=True)
    i = usp.add_parser("inspect"); i.add_argument("path"); i.add_argument("--out")
    v = usp.add_parser("validate"); v.add_argument("path")

    fx = sp.add_parser("fixtures")
    fsp = fx.add_subparsers(dest="fx_cmd", required=True)
    fsp.add_parser("download"); fsp.add_parser("dump-fonts"); fsp.add_parser("collect-fonttools")

    args = p.parse_args()
    if args.cmd == "generate":
        for path in generate_all(): print(path)
    elif args.cmd == "schema":
        result = validate_json(args.schema, args.data); _emit(result); raise SystemExit(1 if result["errors"] else 0)
    elif args.cmd == "sources":
        if args.sources_cmd == "status": _emit(source_status())
        elif args.sources_cmd == "sync": sync_cache()
        elif args.sources_cmd == "subtree-init": subtree_init()
        elif args.sources_cmd == "subtree-update": subtree_update()
    elif args.cmd == "ttx":
        if args.ttx_cmd == "dump":
            for path in dump_font(args.font, args.out, args.tables): print(path)
        elif args.ttx_cmd == "xmljson": _emit(xml_file_to_ast(args.xml), args.out)
        elif args.ttx_cmd == "validate":
            result = validate_ttx(args.path); _emit(result); raise SystemExit(1 if result["errors"] else 0)
    elif args.cmd == "designspace":
        if args.ds_cmd == "inspect": _emit(inspect_designspace(args.path), args.out)
        else:
            result = validate_designspace(args.path); _emit(result); raise SystemExit(1 if result["errors"] else 0)
    elif args.cmd == "ufo":
        if args.ufo_cmd == "inspect": _emit(inspect_ufo(args.path), args.out)
        else:
            result = validate_ufo(args.path); _emit(result); raise SystemExit(1 if result["errors"] else 0)
    elif args.cmd == "fixtures":
        if args.fx_cmd == "download": _emit(download_fonts())
        elif args.fx_cmd == "dump-fonts": _emit(dump_fonts())
        elif args.fx_cmd == "collect-fonttools": _emit(collect_fonttools())


if __name__ == "__main__":
    main()
