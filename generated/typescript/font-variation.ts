// Generated. Canonical source-oriented types.

export type AxisTag = string;
export type Location = Record<string, number>;

export interface Axis {
  name: string;
  tag: AxisTag;
  minimum?: number | null;
  default: number;
  maximum?: number | null;
  hidden?: boolean;
  map?: [number, number][];
  values?: number[];
}

export interface DecomposedTransform {
  translateX?: number;
  translateY?: number;
  rotation?: number;
  scaleX?: number;
  scaleY?: number;
  skewX?: number;
  skewY?: number;
  tCenterX?: number;
  tCenterY?: number;
}

export interface VariableComponent {
  base: string;
  location?: Location;
  transformation?: DecomposedTransform;
  resetUnspecifiedAxes?: boolean;
}

export interface AffineTransform {
  xScale: number;
  xyScale: number;
  yxScale: number;
  yScale: number;
  xOffset: number;
  yOffset: number;
}

export interface AffineComponent {
  base: string;
  transform: AffineTransform;
  identifier?: string | null;
}

export interface Anchor {
  name?: string | null;
  x: number;
  y: number;
  identifier?: string | null;
}

export interface NormalizedGlyph {
  name: string;
  layer: string;
  file: string;
  width: number | null;
  components: AffineComponent[];
  anchors: Anchor[];
  variableComponents: VariableComponent[];
  glyphDesignspace?: unknown;
}

export interface UfoNormalized {
  path: string;
  formatVersion: number;
  glyphCount: number;
  glyphs: NormalizedGlyph[];
}

export interface DesignspaceMapping {
  input: Location;
  output: Location;
  description?: string | null;
}

export interface DesignspaceSource {
  name?: string | null;
  filename?: string | null;
  layerName?: string | null;
  familyName?: string | null;
  styleName?: string | null;
  location: Location;
}

export interface DesignspaceInstance {
  name?: string | null;
  filename?: string | null;
  familyName?: string | null;
  styleName?: string | null;
  location: Location;
}

export interface DesignspaceNormalized {
  path: string;
  formatVersion: string;
  axes: Axis[];
  mappings: DesignspaceMapping[];
  sources: DesignspaceSource[];
  instances: DesignspaceInstance[];
  rules: unknown[];
}

export interface XmlAstElement {
  tag: string;
  attributes: Record<string, string>;
  text?: string;
  children: XmlAstElement[];
}
