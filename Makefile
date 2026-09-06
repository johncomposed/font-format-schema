.PHONY: setup generate generate-ts test test-py test-ts validate synthetic spec sources-sync fixture-fonts fixture-fonttools all

setup:
	git submodule update --init
	uv sync --extra dev
	npm install

synthetic:
	uv run python scripts/build-synthetic-fonts.py

spec:
	uv run fontschema spec extract

generate:
	uv run fontschema generate

generate-ts:
	npm run generate

validate:
	uv run fontschema designspace validate examples/designspace-ufo/VariationDemo.designspace
	uv run fontschema ufo validate examples/designspace-ufo/masters/VariationDemo-Regular.ufo

test-py:
	uv run pytest -q

test-ts:
	npm test

test: test-py test-ts

sources-sync:
	uv run fontschema sources sync

fixture-fonts:
	uv run fontschema fixtures download
	uv run fontschema fixtures dump-fonts

fixture-fonttools:
	uv run fontschema fixtures collect-fonttools

all: synthetic generate generate-ts validate test
