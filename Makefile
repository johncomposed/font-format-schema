.PHONY: setup generate test validate examples synthetic sources-sync vendor-init fixture-fonts fixture-fonttools all

setup:
	uv sync --extra dev

generate:
	uv run fontschema generate

synthetic:
	uv run python scripts/build-synthetic-fonts.py

examples:
	uv run fontschema designspace inspect examples/designspace-ufo/VariationDemo.designspace --out generated/designspace/example.json
	uv run fontschema ufo inspect examples/designspace-ufo/masters/VariationDemo-Regular.ufo --out generated/ufo/example.json

validate:
	uv run fontschema designspace validate examples/designspace-ufo/VariationDemo.designspace
	uv run fontschema ufo validate examples/designspace-ufo/masters/VariationDemo-Regular.ufo

test:
	uv run pytest -q

sources-sync:
	uv run fontschema sources sync

vendor-init:
	./scripts/vendor-init.sh

fixture-fonts:
	uv run fontschema fixtures download
	uv run fontschema fixtures dump-fonts

fixture-fonttools:
	uv run fontschema fixtures collect-fonttools

all: generate synthetic examples validate test
