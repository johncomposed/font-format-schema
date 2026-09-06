"""JSON Schema for the Designspace 5 document model.

The structure follows ``fontTools.designspaceLib`` (the pinned implementation).
Each descriptor class declares its serialisable attributes in ``_attrs``; the
schema builder asserts that every declared attribute is modelled so that a
fontTools upgrade adding a field fails loudly at generation time.

Documentation: https://fonttools.readthedocs.io/en/latest/designspaceLib/xml.html
"""
from __future__ import annotations

from typing import Any

from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisLabelDescriptor,
    AxisMappingDescriptor,
    DiscreteAxisDescriptor,
    InstanceDescriptor,
    LocationLabelDescriptor,
    RangeAxisSubsetDescriptor,
    RuleDescriptor,
    SourceDescriptor,
    ValueAxisSubsetDescriptor,
    VariableFontDescriptor,
)

from . import js

# Attributes that fontTools keeps on descriptors but that are not part of the
# XML document (runtime state) or that we deliberately model differently.
RUNTIME_ONLY = {
    SourceDescriptor: {"path", "font", "copyInfo"},
    InstanceDescriptor: {"path", "font"},
}
# Attributes fontTools flattens/renames on the way to XML.
RENAMED = {
    InstanceDescriptor: {"glyphs": "glyphs"},
}


def _check(cls: type, props: dict[str, Any]) -> None:
    declared = set(getattr(cls, "_attrs", ()))
    missing = declared - set(props) - RUNTIME_ONLY.get(cls, set())
    assert not missing, f"{cls.__name__} declares attributes not modelled in the schema: {sorted(missing)}"


def designspace_defs() -> dict[str, Any]:
    tag = js.string("Four character OpenType axis tag.", minLength=4, maxLength=4)
    label_names = js.record(js.string(), "Localised names keyed by language tag (xml:lang), e.g. {'en': 'Weight'}.")
    location = js.record(js.number(), "Axis name -> value.")
    number_or_null = js.nullable(js.number())

    axis_label = js.obj(
        {
            "name": js.string("Label name (the default language name)."),
            "userValue": js.number("Value of the label on the axis, in user coordinates."),
            "userMinimum": js.number("Start of the range the label covers (STAT format 2)."),
            "userMaximum": js.number("End of the range the label covers (STAT format 2)."),
            "elidable": js.boolean("Label can be elided from names (STAT flag ELIDABLE_AXIS_VALUE_NAME).", default=False),
            "olderSibling": js.boolean("STAT flag OLDER_SIBLING_FONT_ATTRIBUTE.", default=False),
            "linkedUserValue": js.number("Value this label links to (STAT format 3), e.g. Regular -> Bold."),
            "labelNames": label_names,
        },
        ["name", "userValue"],
        description="<label> inside <axis>: a STAT axis value.",
    )
    _check(AxisLabelDescriptor, axis_label["properties"])

    axis_common = {
        "tag": tag,
        "name": js.string("Axis name used in locations, rules and mappings.", minLength=1),
        "labelNames": label_names,
        "hidden": js.boolean("Hide the axis in UIs (fvar HIDDEN_AXIS flag).", default=False),
        "map": js.array(
            js.tuple_([js.number("input (user)"), js.number("output (design)")]),
            "<map input= output=/> pairs converting user space to design space (compiled to avar version 1).",
        ),
        "axisOrdering": js.integer("STAT axisOrdering; defaults to document order when absent."),
        "axisLabels": js.array(js.ref("AxisLabel")),
    }
    continuous_axis = js.obj(
        {
            **axis_common,
            "minimum": js.number("Minimum value in user space."),
            "default": js.number("Default value in user space."),
            "maximum": js.number("Maximum value in user space."),
        },
        ["tag", "name", "minimum", "default", "maximum"],
        description="<axis> with a continuous range.",
    )
    _check(AxisDescriptor, continuous_axis["properties"])

    discrete_axis = js.obj(
        {
            **axis_common,
            "values": js.array(js.number(), "Discrete values the axis can take (space separated in XML).", minItems=1),
            "default": js.number("Default value; must be one of `values`."),
        },
        ["tag", "name", "values", "default"],
        description="<axis values=...>: a discrete axis (Designspace 5). Discrete axes split the document into separate variable fonts.",
    )
    _check(DiscreteAxisDescriptor, discrete_axis["properties"])

    axis_mapping = js.obj(
        {
            "inputLocation": js.ref("Location", "Axis name -> user value (input side)."),
            "outputLocation": js.ref("Location", "Axis name -> user value (output side)."),
            "description": js.string("Optional human readable description."),
            "groupDescription": js.string("Description of the enclosing <mappings> group."),
        },
        ["inputLocation", "outputLocation"],
        description="<mapping> inside <axes><mappings>: a multi-axis input/output correspondence compiled to avar version 2.",
    )
    _check(AxisMappingDescriptor, axis_mapping["properties"])

    location_label = js.obj(
        {
            "name": js.string(),
            "elidable": js.boolean(default=False),
            "olderSibling": js.boolean(default=False),
            "userLocation": js.ref("Location", "Location in user coordinates."),
            "labelNames": label_names,
        },
        ["name", "userLocation"],
        description="<labels><label>: a named location (STAT format 4).",
    )
    _check(LocationLabelDescriptor, location_label["properties"])

    source = js.obj(
        {
            "filename": js.string("Path to the source UFO, relative to the document."),
            "name": js.string("Unique source name."),
            "layerName": js.string("UFO layer to read; the default layer when absent."),
            "location": js.ref("Location", "Design-space location of the master. Omitted axes take their default."),
            "familyName": js.string(),
            "styleName": js.string(),
            "localisedFamilyName": label_names,
            "copyLib": js.boolean(default=False),
            "copyGroups": js.boolean(default=False),
            "copyFeatures": js.boolean(default=False),
            "muteKerning": js.boolean(default=False),
            "muteInfo": js.boolean(default=False),
            "mutedGlyphNames": js.array(js.string(), "Glyphs of this master excluded from interpolation."),
        },
        ["location"],
        description="<source>: a master.",
    )
    _check(SourceDescriptor, source["properties"])

    instance = js.obj(
        {
            "filename": js.string(),
            "name": js.string(),
            "locationLabel": js.string("Name of a <labels><label> giving the location."),
            "designLocation": js.ref("Location", "Location in design coordinates (xvalue)."),
            "userLocation": js.ref("Location", "Location in user coordinates (uservalue)."),
            "familyName": js.string(),
            "styleName": js.string(),
            "postScriptFontName": js.string(),
            "styleMapFamilyName": js.string(),
            "styleMapStyleName": js.enum(["regular", "italic", "bold", "bold italic"]),
            "localisedFamilyName": label_names,
            "localisedStyleName": label_names,
            "localisedStyleMapFamilyName": label_names,
            "localisedStyleMapStyleName": label_names,
            "glyphs": js.record({}, "Deprecated per-glyph instance overrides (Designspace 3)."),
            "kerning": js.boolean("Interpolate kerning.", default=True),
            "info": js.boolean("Interpolate font info.", default=True),
            "lib": js.ref("PlistDict"),
        },
        description="<instance>: a static instance / named instance.",
    )
    _check(InstanceDescriptor, instance["properties"])

    condition = js.obj(
        {
            "name": js.string("Axis name."),
            "minimum": number_or_null,
            "maximum": number_or_null,
        },
        ["name"],
        description="<condition>: a closed range on one axis; an open bound is null.",
    )
    rule = js.obj(
        {
            "name": js.string(),
            "conditionSets": js.array(
                js.array(js.ref("Condition"), "All conditions in a set must hold (AND)."),
                "Any set may trigger the rule (OR).",
            ),
            "subs": js.array(js.tuple_([js.string("source glyph"), js.string("replacement glyph")])),
        },
        ["conditionSets", "subs"],
        description="<rule>: glyph substitutions active in parts of the design space (compiled to GSUB FeatureVariations).",
    )
    _check(RuleDescriptor, rule["properties"])

    range_subset = js.obj(
        {
            "name": js.string("Axis name."),
            "userMinimum": js.number(),
            "userDefault": js.number(),
            "userMaximum": js.number(),
        },
        ["name"],
        description="<axis-subset> keeping a (sub)range of an axis in the variable font.",
    )
    _check(RangeAxisSubsetDescriptor, range_subset["properties"])
    value_subset = js.obj(
        {"name": js.string("Axis name."), "userValue": js.number()},
        ["name", "userValue"],
        description="<axis-subset uservalue=...> pinning an axis to one value.",
    )
    _check(ValueAxisSubsetDescriptor, value_subset["properties"])

    variable_font = js.obj(
        {
            "name": js.string(),
            "filename": js.string(),
            "axisSubsets": js.array(js.one_of(js.ref("RangeAxisSubset"), js.ref("ValueAxisSubset"))),
            "lib": js.ref("PlistDict"),
        },
        ["name", "axisSubsets"],
        description="<variable-font>: one variable font to build from the document.",
    )
    _check(VariableFontDescriptor, variable_font["properties"])

    document = js.obj(
        {
            "path": js.string("File system path (informational)."),
            "formatVersion": js.string("Document format, e.g. '5.2'.", pattern=r"^\d+(\.\d+)?$"),
            "axes": js.array(js.ref("Axis")),
            "axisMappings": js.array(js.ref("AxisMapping")),
            "locationLabels": js.array(js.ref("LocationLabel")),
            "sources": js.array(js.ref("Source")),
            "variableFonts": js.array(js.ref("VariableFont")),
            "instances": js.array(js.ref("Instance")),
            "rules": js.array(js.ref("Rule")),
            "rulesProcessingLast": js.boolean("Apply rules after other substitutions (<rules processing='last'>).", default=False),
            "lib": js.ref("PlistDict"),
        },
        ["formatVersion", "axes", "sources"],
        description="<designspace>: a Designspace 5 document.",
    )

    return {
        "Location": location,
        "PlistValue": {"description": "Any property list value."},
        "PlistDict": js.record(js.ref("PlistValue")),
        "AxisLabel": axis_label,
        "ContinuousAxis": continuous_axis,
        "DiscreteAxis": discrete_axis,
        "Axis": js.one_of(js.ref("ContinuousAxis"), js.ref("DiscreteAxis")),
        "AxisMapping": axis_mapping,
        "LocationLabel": location_label,
        "Source": source,
        "Instance": instance,
        "Condition": condition,
        "Rule": rule,
        "RangeAxisSubset": range_subset,
        "ValueAxisSubset": value_subset,
        "VariableFont": variable_font,
        "DesignspaceDocument": document,
    }


def designspace_schema() -> dict[str, Any]:
    return js.document(
        "designspace",
        "Designspace document",
        "DesignspaceDocument",
        designspace_defs(),
        description="JSON model of a Designspace 5 document, structured after fontTools.designspaceLib descriptors.",
    )
