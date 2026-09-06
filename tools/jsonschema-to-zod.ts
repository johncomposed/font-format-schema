/**
 * JSON Schema (2020-12 subset) -> Zod v4 source code.
 *
 * Scope: exactly the keyword subset emitted by `src/fontschema/schema/*.py`.
 * Every `$defs` entry becomes a standalone `export const Name = z...` plus an
 * inferred `export type Name`. Definitions that take part in a reference cycle
 * are emitted with an explicit `z.ZodType<T.Name>` annotation (types imported
 * from the json-schema-to-typescript output) and referenced through `z.lazy`.
 *
 * Unsupported keywords throw, so a generator change cannot silently produce a
 * weaker validator.
 */

export type JsonSchema = {
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
  type?: string | string[];
  enum?: unknown[];
  const?: unknown;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  additionalProperties?: boolean | JsonSchema;
  propertyNames?: JsonSchema;
  items?: JsonSchema | false;
  prefixItems?: JsonSchema[];
  minItems?: number;
  maxItems?: number;
  uniqueItems?: boolean;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  multipleOf?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;
  anyOf?: JsonSchema[];
  oneOf?: JsonSchema[];
  allOf?: JsonSchema[];
  default?: unknown;
  description?: string;
  title?: string;
  $schema?: string;
  $id?: string;
  [key: `x-${string}`]: unknown;
};

const KNOWN_KEYWORDS = new Set([
  "$ref", "$defs", "type", "enum", "const", "properties", "required", "additionalProperties", "propertyNames",
  "items", "prefixItems", "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum",
  "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "pattern", "format", "anyOf", "oneOf", "allOf",
  "default", "description", "title", "$schema", "$id",
]);

export interface EmitOptions {
  /** Module specifier for the TypeScript types of this schema (used for cyclic defs). */
  typesModule?: string;
  /** Header comment lines. */
  banner?: string[];
}

const refName = (ref: string): string => {
  const m = /^#\/\$defs\/([^/]+)$/.exec(ref);
  if (!m) throw new Error(`unsupported $ref ${ref}`);
  return m[1]!;
};

const ident = (name: string): string => (/^[A-Za-z_$][\w$]*$/.test(name) ? name : name.replace(/[^\w$]/g, "_"));

const str = (s: string): string => JSON.stringify(s);

/** Collect the $defs each definition refers to (directly). */
function collectRefs(schema: JsonSchema, out: Set<string>): void {
  if (schema.$ref) out.add(refName(schema.$ref));
  for (const key of ["properties", "$defs"] as const) {
    const map = schema[key];
    if (map) for (const v of Object.values(map)) collectRefs(v, out);
  }
  for (const key of ["anyOf", "oneOf", "allOf", "prefixItems"] as const) {
    const list = schema[key];
    if (list) for (const v of list) collectRefs(v, out);
  }
  if (schema.items) collectRefs(schema.items, out);
  if (typeof schema.additionalProperties === "object") collectRefs(schema.additionalProperties, out);
  if (schema.propertyNames) collectRefs(schema.propertyNames, out);
}

/** Tarjan SCC; returns components in reverse topological order (dependencies first). */
function stronglyConnected(nodes: string[], edges: Map<string, Set<string>>): string[][] {
  let index = 0;
  const stack: string[] = [];
  const onStack = new Set<string>();
  const indices = new Map<string, number>();
  const low = new Map<string, number>();
  const result: string[][] = [];
  const visit = (v: string): void => {
    indices.set(v, index);
    low.set(v, index);
    index++;
    stack.push(v);
    onStack.add(v);
    for (const w of edges.get(v) ?? []) {
      if (!indices.has(w)) {
        visit(w);
        low.set(v, Math.min(low.get(v)!, low.get(w)!));
      } else if (onStack.has(w)) {
        low.set(v, Math.min(low.get(v)!, indices.get(w)!));
      }
    }
    if (low.get(v) === indices.get(v)) {
      const component: string[] = [];
      let w: string;
      do {
        w = stack.pop()!;
        onStack.delete(w);
        component.push(w);
      } while (w !== v);
      result.push(component);
    }
  };
  for (const n of nodes) if (!indices.has(n)) visit(n);
  return result;
}

export function emitZodModule(doc: JsonSchema, options: EmitOptions = {}): string {
  const defs = doc.$defs ?? {};
  const names = Object.keys(defs);
  const edges = new Map<string, Set<string>>();
  for (const name of names) {
    const refs = new Set<string>();
    collectRefs(defs[name]!, refs);
    edges.set(name, refs);
  }
  const components = stronglyConnected(names, edges);
  const cyclic = new Set<string>();
  for (const component of components) {
    if (component.length > 1 || edges.get(component[0]!)!.has(component[0]!)) {
      for (const n of component) cyclic.add(n);
    }
  }
  const order = components.flat();
  const emitted = new Set<string>();

  const refExpr = (name: string): string => {
    if (!(name in defs)) throw new Error(`unknown definition ${name}`);
    const id = ident(name);
    // Forward or cyclic reference: defer evaluation.
    return emitted.has(name) && !cyclic.has(name) ? id : `z.lazy(() => ${id})`;
  };

  const emit = (schema: JsonSchema, path: string): string => {
    for (const key of Object.keys(schema)) {
      if (!KNOWN_KEYWORDS.has(key) && !key.startsWith("x-")) {
        throw new Error(`${path}: unsupported JSON Schema keyword ${key}`);
      }
    }
    let expr = emitCore(schema, path);
    if (schema.default !== undefined) expr += `.default(${JSON.stringify(schema.default)})`;
    if (schema.description) expr += `.describe(${str(schema.description)})`;
    return expr;
  };

  const emitObject = (schema: JsonSchema, path: string): string => {
    const props = schema.properties ?? {};
    const required = new Set(schema.required ?? []);
    const additional = schema.additionalProperties;
    const entries = Object.entries(props).map(([key, sub]) => {
      let value = emit(sub, `${path}.${key}`);
      if (!required.has(key) && sub.default === undefined) value += ".optional()";
      return `  ${/^[A-Za-z_$][\w$]*$/.test(key) ? key : str(key)}: ${value},`;
    });
    const body = entries.length ? `{\n${entries.join("\n")}\n}` : "{}";
    let expr: string;
    if (Object.keys(props).length === 0 && typeof additional === "object") {
      expr = `z.record(z.string(), ${emit(additional, `${path}.additionalProperties`)})`;
    } else if (additional === false) {
      expr = `z.strictObject(${body})`;
    } else if (additional === true || additional === undefined) {
      expr = `z.looseObject(${body})`;
    } else {
      expr = `z.object(${body}).catchall(${emit(additional, `${path}.additionalProperties`)})`;
    }
    // `anyOf: [{required: [a]}, {required: [b]}]` => at least one of the keys present.
    if (schema.anyOf && schema.anyOf.every((s) => Object.keys(s).length === 1 && Array.isArray(s.required))) {
      const alternatives = schema.anyOf.map((s) => `[${s.required!.map(str).join(", ")}]`);
      expr += `.refine((v) => [${alternatives.join(", ")}].some((keys) => keys.every((k) => (v as Record<string, unknown>)[k] !== undefined)), { message: ${str(
        `one of ${schema.anyOf.map((s) => s.required!.join("+")).join(" | ")} is required`,
      )} })`;
    } else if (schema.anyOf) {
      throw new Error(`${path}: anyOf on an object with properties is only supported for required-alternatives`);
    }
    return expr;
  };

  const emitCore = (schema: JsonSchema, path: string): string => {
    if (schema.$ref) return refExpr(refName(schema.$ref));
    if (schema.const !== undefined) return `z.literal(${JSON.stringify(schema.const)})`;
    if (schema.enum) {
      if (schema.enum.every((v) => typeof v === "string")) return `z.enum([${schema.enum.map((v) => str(v as string)).join(", ")}])`;
      return `z.union([${schema.enum.map((v) => `z.literal(${JSON.stringify(v)})`).join(", ")}])`;
    }
    if (schema.allOf) return schema.allOf.map((s, i) => emit(s, `${path}.allOf[${i}]`)).reduce((a, b) => `z.intersection(${a}, ${b})`);
    const union = schema.anyOf ?? schema.oneOf;
    if (union && !schema.properties) return `z.union([${union.map((s, i) => emit(s, `${path}.union[${i}]`)).join(", ")}])`;

    const types = schema.type === undefined ? [] : Array.isArray(schema.type) ? schema.type : [schema.type];
    if (types.length === 0) {
      if (schema.properties || schema.additionalProperties !== undefined) return emitObject(schema, path);
      return "z.unknown()";
    }
    const nullable = types.includes("null");
    const base = types.filter((t) => t !== "null");
    if (base.length > 1) {
      const parts = base.map((t) => emitCore({ ...schema, type: t }, path));
      const expr = `z.union([${parts.join(", ")}])`;
      return nullable ? `${expr}.nullable()` : expr;
    }
    let expr: string;
    switch (base[0]) {
      case undefined:
        return "z.null()";
      case "string": {
        expr = "z.string()";
        if (schema.minLength !== undefined) expr += `.min(${schema.minLength})`;
        if (schema.maxLength !== undefined) expr += `.max(${schema.maxLength})`;
        if (schema.pattern !== undefined) expr += `.regex(new RegExp(${str(schema.pattern)}))`;
        break;
      }
      case "number":
      case "integer": {
        expr = base[0] === "integer" ? "z.int()" : "z.number()";
        if (schema.minimum !== undefined) expr += `.min(${schema.minimum})`;
        if (schema.maximum !== undefined) expr += `.max(${schema.maximum})`;
        if (schema.exclusiveMinimum !== undefined) expr += `.gt(${schema.exclusiveMinimum})`;
        if (schema.exclusiveMaximum !== undefined) expr += `.lt(${schema.exclusiveMaximum})`;
        if (schema.multipleOf !== undefined) expr += `.multipleOf(${schema.multipleOf})`;
        break;
      }
      case "boolean":
        expr = "z.boolean()";
        break;
      case "array": {
        if (schema.prefixItems) {
          if (schema.items !== false && schema.items !== undefined) throw new Error(`${path}: prefixItems with open items is unsupported`);
          expr = `z.tuple([${schema.prefixItems.map((s, i) => emit(s, `${path}[${i}]`)).join(", ")}])`;
        } else {
          const items = schema.items === undefined || schema.items === false ? "z.unknown()" : emit(schema.items, `${path}[]`);
          expr = `z.array(${items})`;
          if (schema.minItems !== undefined) expr += `.min(${schema.minItems})`;
          if (schema.maxItems !== undefined) expr += `.max(${schema.maxItems})`;
          if (schema.uniqueItems) expr += `.refine((a) => new Set(a.map((x) => JSON.stringify(x))).size === a.length, { message: "items must be unique" })`;
        }
        break;
      }
      case "object":
        expr = emitObject(schema, path);
        break;
      default:
        throw new Error(`${path}: unsupported type ${base[0]}`);
    }
    return nullable ? `${expr}.nullable()` : expr;
  };

  const lines: string[] = [];
  for (const line of options.banner ?? []) lines.push(`// ${line}`);
  lines.push(`import { z } from "zod";`);
  if (cyclic.size && options.typesModule) lines.push(`import type * as T from ${str(options.typesModule)};`);
  lines.push("");
  for (const name of order) {
    const id = ident(name);
    const expr = emit(defs[name]!, name);
    if (cyclic.has(name)) {
      const annotation = options.typesModule ? `z.ZodType<T.${id}>` : "z.ZodType<any>";
      lines.push(`export const ${id}: ${annotation} = ${expr};`);
      lines.push(options.typesModule ? `export type ${id} = T.${id};` : `export type ${id} = z.infer<typeof ${id}>;`);
    } else {
      lines.push(`export const ${id} = ${expr};`);
      lines.push(`export type ${id} = z.infer<typeof ${id}>;`);
    }
    lines.push("");
    emitted.add(name);
  }
  if (doc.$ref) {
    lines.push(`/** Root schema (${doc.title ?? doc.$id ?? "root"}). */`);
    lines.push(`export default ${ident(refName(doc.$ref))};`);
  }
  return lines.join("\n") + "\n";
}
