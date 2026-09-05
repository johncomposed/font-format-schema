from fontschema.ttx.otdata import extract_variation_otdata, table_inventory


def test_variation_roots_are_present():
    meta = extract_variation_otdata()
    defs = meta["definitions"]
    for name in ["HVAR", "VVAR", "MVAR", "VARC", "VarStore", "MultiVarStore"]:
        assert name in defs


def test_table_inventory_distinguishes_custom_tables():
    rows = {r["tag"]: r for r in table_inventory()["tables"]}
    assert rows["HVAR"]["otDataRoot"] == "HVAR"
    assert rows["avar"]["serialization"].startswith("hybrid")
