# Designspace/UFO example

This fixture is intentionally small and source-oriented. It demonstrates:

- two continuous axes (`wght`, `wdth`);
- Designspace 5.2 `<mappings>` with a multi-axis input/output mapping;
- a normal UFO GLIF component with `xOffset` / `yOffset`;
- named anchors on component/source glyphs;
- a variable component stored in `glyph.lib` under `com.black-foundry.variable-components`, with its own location and decomposed transformation.

The outlines are simple rectangles so diffs stay readable. The fixture is for parsing/schema/validation tests, not typographic output quality.
