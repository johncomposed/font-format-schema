// Generated from fontTools otData.py. Semantic structure metadata, not an exact TTX DOM.
// fontTools 4.63.0

export interface AxisIndicesList {
  /** fontTools type: TupleList */
  Item: unknown;
}

export interface AxisRecord {
  /** A tag identifying the axis of design variation | fontTools type: Tag */
  AxisTag: string;
  /** The name ID for entries in the "name" table that provide a display string for this axis | fontTools type: NameID */
  AxisNameID: number;
  /** A value that applications can use to determine primary sorting of face names, or for ordering of descriptors when composing family or face names | fontTools type: uint16 */
  AxisOrdering: number;
  /** Extra bytes.  Set to empty array. | fontTools type: uint8 */
  MoreBytes?: number[];
}

export interface AxisRecordArray {
  /** Axis records | fontTools type: AxisRecord */
  Axis: AxisRecord[];
}

export interface AxisSegmentMap {
  /** The number of correspondence pairs for this axis | fontTools type: uint16 */
  PositionMapCount: number;
  /** The array of axis value map records for this axis | fontTools type: AxisValueMap */
  AxisValueMap: AxisValueMap[];
}

export interface AxisValueArray {
  /** Axis values | fontTools type: Offset */
  AxisValue: unknown[];
}

export interface AxisValueMap {
  /** A normalized coordinate value obtained using default normalization | fontTools type: F2Dot14 */
  FromCoordinate: number;
  /** The modified, normalized coordinate value | fontTools type: F2Dot14 */
  ToCoordinate: number;
}

export interface ConditionList {
  /** Number of condition tables in the ConditionTable array | fontTools type: uint32 */
  ConditionCount: number;
  /** Array of offset to condition tables, from the beginning of the ConditionList table. | fontTools type: LOffset */
  ConditionTable: unknown[];
}

export interface ConditionSet {
  /** Number of condition tables in the ConditionTable array | fontTools type: uint16 */
  ConditionCount: number;
  /** Array of offset to condition tables, from the beginning of the ConditionSet table. | fontTools type: LOffset */
  ConditionTable: unknown[];
}

export interface DeltaSetIndexMapFormat0 {
  /** Format of the DeltaSetIndexMap = 0 | fontTools type: uint8 */
  Format: number;
  /** fontTools type: uint8 */
  EntryFormat: number;
  /** fontTools type: uint16 */
  MappingCount: number;
  /** Array of compressed data | fontTools type: VarIdxMapValue */
  mapping: unknown;
}

export interface DeltaSetIndexMapFormat1 {
  /** Format of the DeltaSetIndexMap = 1 | fontTools type: uint8 */
  Format: number;
  /** fontTools type: uint8 */
  EntryFormat: number;
  /** fontTools type: uint32 */
  MappingCount: number;
  /** Array of compressed data | fontTools type: VarIdxMapValue */
  mapping: unknown;
}

export interface FeatureVariationRecord {
  /** Offset to a ConditionSet table, from beginning of the FeatureVariations table. | fontTools type: LOffset */
  ConditionSet: unknown;
  /** Offset to a FeatureTableSubstitution table, from beginning of the FeatureVariations table | fontTools type: LOffset */
  FeatureTableSubstitution: unknown;
}

export interface FeatureVariations {
  /** Version of the table-initially set to 0x00010000 | fontTools type: Version */
  Version: number;
  /** Number of records in the FeatureVariationRecord array | fontTools type: uint32 */
  FeatureVariationCount: number;
  /** Array of FeatureVariationRecord | fontTools type: struct */
  FeatureVariationRecord: unknown[];
}

export interface HVAR {
  /** Version of the HVAR table-initially = 0x00010000 | fontTools type: Version */
  Version: number;
  /** fontTools type: LOffset */
  VarStore: unknown;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  AdvWidthMap: VarIdxMap;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  LsbMap: VarIdxMap;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  RsbMap: VarIdxMap;
}

export interface MVAR {
  /** Version of the MVAR table-initially = 0x00010000 | fontTools type: Version */
  Version: number;
  /** Set to 0 | fontTools type: uint16 */
  Reserved: number;
  /** fontTools type: uint16 */
  ValueRecordSize: number;
  /** fontTools type: uint16 */
  ValueRecordCount: number;
  /** fontTools type: Offset */
  VarStore: unknown;
  /** fontTools type: MetricsValueRecord */
  ValueRecord: MetricsValueRecord[];
}

export interface MetricsValueRecord {
  /** 4-byte font-wide measure identifier | fontTools type: Tag */
  ValueTag: string;
  /** Combined outer-inner variation index | fontTools type: uint32 */
  VarIdx: number;
  /** Extra bytes.  Set to empty array. | fontTools type: uint8 */
  MoreBytes?: number[];
}

export interface MultiVarData {
  /** Set to 1. | fontTools type: uint8 */
  Format: number;
  /** fontTools type: uint16 */
  VarRegionCount: number;
  /** fontTools type: uint16 */
  VarRegionIndex: number[];
  /** fontTools type: TupleList */
  Item: unknown;
}

export interface MultiVarStore {
  /** Set to 1. | fontTools type: uint16 */
  Format: number;
  /** fontTools type: LOffset */
  SparseVarRegionList: unknown;
  /** fontTools type: uint16 */
  MultiVarDataCount: number;
  /** fontTools type: LOffset */
  MultiVarData: unknown[];
}

export interface STAT {
  /** Version of the table-initially set to 0x00010000, currently 0x00010002. | fontTools type: Version */
  Version: number;
  /** Size in bytes of each design axis record | fontTools type: uint16 */
  DesignAxisRecordSize: number;
  /** Number of design axis records | fontTools type: uint16 */
  DesignAxisCount: number;
  /** Offset in bytes from the beginning of the STAT table to the start of the design axes array | fontTools type: LOffsetTo(AxisRecordArray) */
  DesignAxisRecord: AxisRecordArray;
  /** Number of axis value tables | fontTools type: uint16 */
  AxisValueCount: number;
  /** Offset in bytes from the beginning of the STAT table to the start of the axes value offset array | fontTools type: LOffsetTo(AxisValueArray) */
  AxisValueArray: AxisValueArray;
  /** NameID to use when all style attributes are elided. | fontTools type: NameID */
  ElidedFallbackNameID?: number;
}

export interface SparseVarRegion {
  /** fontTools type: uint16 */
  SparseRegionCount: number;
  /** fontTools type: struct */
  SparseVarRegionAxis: unknown[];
}

export interface SparseVarRegionAxis {
  /** fontTools type: uint16 */
  AxisIndex: number;
  /** fontTools type: F2Dot14 */
  StartCoord: number;
  /** fontTools type: F2Dot14 */
  PeakCoord: number;
  /** fontTools type: F2Dot14 */
  EndCoord: number;
}

export interface SparseVarRegionList {
  /** fontTools type: uint16 */
  RegionCount: number;
  /** fontTools type: LOffsetTo(SparseVarRegion) */
  Region: SparseVarRegion[];
}

export interface VARC {
  /** Version of the HVAR table-initially = 0x00010000 | fontTools type: Version */
  Version: number;
  /** fontTools type: LOffset */
  Coverage: unknown;
  /** (may be NULL) | fontTools type: LOffset */
  MultiVarStore: unknown;
  /** (may be NULL) | fontTools type: LOffset */
  ConditionList: unknown;
  /** (may be NULL) | fontTools type: LOffset */
  AxisIndicesList: unknown;
  /** fontTools type: LOffset */
  VarCompositeGlyphs: unknown;
}

export interface VVAR {
  /** Version of the VVAR table-initially = 0x00010000 | fontTools type: Version */
  Version: number;
  /** fontTools type: LOffset */
  VarStore: unknown;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  AdvHeightMap: VarIdxMap;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  TsbMap: VarIdxMap;
  /** fontTools type: LOffsetTo(VarIdxMap) */
  BsbMap: VarIdxMap;
  /** Vertical origin mapping. | fontTools type: LOffsetTo(VarIdxMap) */
  VOrgMap: VarIdxMap;
}

export interface VarCompositeGlyphs {
  /** fontTools type: VarCompositeGlyphList */
  VarCompositeGlyph: unknown;
}

export interface VarData {
  /** fontTools type: uint16 */
  ItemCount: number;
  /** fontTools type: uint16 */
  NumShorts: number;
  /** fontTools type: uint16 */
  VarRegionCount: number;
  /** fontTools type: uint16 */
  VarRegionIndex: number[];
  /** fontTools type: VarDataValue */
  Item: unknown[];
}

export interface VarIdxMap {
  /** fontTools type: uint16 */
  EntryFormat: number;
  /** fontTools type: uint16 */
  MappingCount: number;
  /** Array of compressed data | fontTools type: VarIdxMapValue */
  mapping: unknown;
}

export interface VarRegion {
  /** fontTools type: struct */
  VarRegionAxis: unknown[];
}

export interface VarRegionAxis {
  /** fontTools type: F2Dot14 */
  StartCoord: number;
  /** fontTools type: F2Dot14 */
  PeakCoord: number;
  /** fontTools type: F2Dot14 */
  EndCoord: number;
}

export interface VarRegionList {
  /** fontTools type: uint16 */
  RegionAxisCount: number;
  /** fontTools type: uint16 */
  RegionCount: number;
  /** fontTools type: VarRegion */
  Region: VarRegion[];
}

export interface VarStore {
  /** Set to 1. | fontTools type: uint16 */
  Format: number;
  /** fontTools type: LOffset */
  VarRegionList: unknown;
  /** fontTools type: uint16 */
  VarDataCount: number;
  /** fontTools type: LOffset */
  VarData: unknown[];
}

export interface avar {
  /** Version of the avar table- 0x00010000 or 0x00020000 | fontTools type: Version */
  Version: number;
  /** Permanently reserved; set to zero | fontTools type: uint16 */
  Reserved: number;
  /** The number of variation axes for this font. This must be the same number as axisCount in the "fvar" table | fontTools type: uint16 */
  AxisCount: number;
  /** The segment maps array — one segment map for each axis, in the order of axes specified in the "fvar" table | fontTools type: AxisSegmentMap */
  AxisSegmentMap: AxisSegmentMap[];
  /** fontTools type: LOffsetTo(DeltaSetIndexMap) */
  VarIdxMap?: unknown;
  /** fontTools type: LOffset */
  VarStore?: unknown;
}

