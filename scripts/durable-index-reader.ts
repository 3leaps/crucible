// Independent logical reader for contract: durable-index/v0.
//
// Contract compliance tooling only (PDR-0006 Rule 2c). It is written from the
// standard's text, not from the repository's Python checker, and shares no code
// with it. It reads the authored fixtures and reports whether its own results
// agree with their expected outcomes. A disagreement is a finding against the
// fixture, the standard or one of the checkers; it is resolved by the contract
// text. This is not a reference implementation or a library.
//
// Validation interpreter: Node.js >= 22.6 with built-in type stripping (PDR-0006
// Rule 2c); conformance is judged on Node.js. Standard-library `node:` modules
// only, no install step. Type annotations are documentation: Node.js strips
// them and continuous integration runs no type checker. Bun may run the same
// source as a developer convenience, but its result is not conformance evidence.
//
// Usage: node --experimental-strip-types scripts/durable-index-reader.ts

import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const VECTORS = join(ROOT, "schemas/durable-index/v0/vectors");

type Scope = { namespace: string; prefix: string };
type JsonObject = Record<string, unknown>;
type Binding = { id: string; ref: string; sha256: string; byte_length: number };
type NumericToken = { [numericToken]: true; value: number; integral: boolean };

const utf8 = new TextEncoder();
// Binary64 alone cannot distinguish a rounded decimal fraction from an integer.
// Preserve that property on each parsed object independently of its JS value.
const numericIntegrality = new WeakMap<object, Map<string, boolean>>();
const numericToken = Symbol("numeric token");
function exactInteger(object: JsonObject, key: string): boolean {
  return Number.isSafeInteger(object[key]) && numericIntegrality.get(object)?.get(key) !== false;
}
function clone<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  const result: JsonObject = Array.isArray(value) ? [] : {};
  for (const key of Object.keys(value)) result[key] = clone((value as JsonObject)[key]);
  const facts = numericIntegrality.get(value);
  if (facts) numericIntegrality.set(result, new Map(facts));
  return result;
}
function overlay(base: JsonObject, replacement: JsonObject): JsonObject {
  const result = clone(base);
  const facts = new Map(numericIntegrality.get(result));
  const replacementFacts = numericIntegrality.get(replacement);
  for (const key of Object.keys(replacement)) {
    result[key] = clone(replacement[key]);
    facts.delete(key);
    const fact = replacementFacts?.get(key);
    if (fact !== undefined) facts.set(key, fact);
  }
  numericIntegrality.set(result, facts);
  return result;
}
function readJson(path: string): JsonObject {
  return strictJSON(readFileSync(path));
}
function readJsonFromText(text: string): JsonObject {
  return strictJSON(utf8.encode(text));
}

// Unsigned UTF-8 byte order (I2). JavaScript string comparison uses UTF-16 code
// units, which disagrees with UTF-8 byte order for supplementary characters, so
// compare encoded bytes.
function compareBytes(a: Uint8Array, b: Uint8Array): number {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return a.length - b.length;
}

function compareScopes(a: Scope, b: Scope): number {
  return (
    compareBytes(utf8.encode(a.namespace), utf8.encode(b.namespace)) ||
    compareBytes(utf8.encode(a.prefix), utf8.encode(b.prefix))
  );
}

function startsWithBytes(value: Uint8Array, prefix: Uint8Array): boolean {
  if (prefix.length > value.length) return false;
  for (let i = 0; i < prefix.length; i++) {
    if (value[i] !== prefix[i]) return false;
  }
  return true;
}

// A row belongs to a scope when its namespace is equal and its key begins with
// the prefix by exact UTF-8 bytes. No cleanup, trimming or normalization (I2).
function contains(scope: Scope, namespace: string, key: string): boolean {
  return (
    scope.namespace === namespace && startsWithBytes(utf8.encode(key), utf8.encode(scope.prefix))
  );
}

// One scope covers another when they share a namespace and the other's prefix
// starts with this one's.
function covers(outer: Scope, inner: Scope): boolean {
  return contains(outer, inner.namespace, inner.prefix);
}

// Sorted, duplicate-free and prefix-minimal (I2). Individual prefixes are never
// rewritten.
function canonical(scopes: Scope[]): Scope[] {
  const sorted = [...scopes].sort(compareScopes);
  const out: Scope[] = [];
  for (const scope of sorted) {
    if (!out.some((kept) => covers(kept, scope))) out.push(scope);
  }
  return out;
}

function u32(n: number): Uint8Array {
  const b = new Uint8Array(4);
  new DataView(b.buffer).setUint32(0, n, false);
  return b;
}

function framed(text: string): Uint8Array[] {
  const bytes = utf8.encode(text);
  return [u32(bytes.length), bytes];
}

// The semantic plan digest input (I2): domain tag and zero byte, framed set id,
// four-byte scope count, then each canonical scope's framed namespace and prefix.
function planBytes(setId: string, scopes: Scope[]): Uint8Array {
  const parts: Uint8Array[] = [
    utf8.encode("durable-index/v0/plan"),
    new Uint8Array([0]),
    ...framed(setId),
    u32(scopes.length),
  ];
  for (const scope of scopes) parts.push(...framed(scope.namespace), ...framed(scope.prefix));
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}

const hex = (b: Uint8Array) => Buffer.from(b).toString("hex");
const sha256 = (b: Uint8Array) => createHash("sha256").update(b).digest("hex");

// Scope loss (I5): every old prefix must be covered by some new prefix in its
// namespace. Counts are irrelevant.
function loses(previous: Scope[], next: Scope[]): boolean {
  return previous.some((old) => !next.some((n) => covers(n, old)));
}

type Result = { file: string; agree: boolean; detail?: string };

function same(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b))
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((v, i) => same(v, b[i]))
    );
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") return false;
  const left = a as Record<string, unknown>,
    right = b as Record<string, unknown>;
  const keys = Object.keys(left);
  return (
    keys.length === Object.keys(right).length &&
    keys.every((k) => Object.hasOwn(right, k) && same(left[k], right[k]))
  );
}

function checkPlan(file: string): Result {
  const v = readJson(join(VECTORS, "plans", file));
  const canon = canonical(v.input);
  if (!same(canon, v.canonical)) return { file, agree: false, detail: "canonical" };
  const bytes = planBytes(v.set_id, canon);
  if (hex(bytes) !== v.bytes_hex) return { file, agree: false, detail: "bytes_hex" };
  if (sha256(bytes) !== v.sha256) return { file, agree: false, detail: "sha256" };
  for (const [i, c] of (v.comparisons ?? []).entries()) {
    if (loses(canon, canonical(c.next)) !== c.loss) {
      return { file, agree: false, detail: `comparison ${i}` };
    }
  }
  for (const [i, m] of (v.membership ?? []).entries()) {
    if (contains(m.scope, m.namespace, m.key) !== m.contains) {
      return { file, agree: false, detail: `membership ${i}` };
    }
  }
  return { file: `plans/${file}`, agree: true };
}

// ---------------------------------------------------------------------------
// Transitions (I4 rows and lineage, I5 successors, I6 enrichment)

// Erasable syntax only (PDR-0006 Rule 2c): Node.js type stripping removes
// annotations but refuses syntax that emits code, such as this constructor
// parameter property written the long way.
class Refusal extends Error {
  reason: string;
  constructor(reason: string) {
    super(reason);
    this.reason = reason;
  }
}

function refuse(condition: unknown, reason: string): asserts condition {
  if (!condition) throw new Refusal(reason);
}

type Stamp = { snapshot_id: string; at: string };
type Revision = { kind: string; value: string } | null;
type Attribute = {
  name: string;
  value: string | null;
  operation: string;
  observed_at: string;
  against_revision: { kind: string; value: string };
};
type Row = {
  namespace: string;
  key: string;
  revision: Revision;
  size_bytes: number;
  last_modified: string | null;
  storage_class: string | null;
  first_seen: Stamp;
  last_seen: Stamp;
  last_changed: Stamp;
  deleted: Stamp | null;
  enrichments: Attribute[];
};

const SOURCE_FIELDS = [
  "namespace",
  "key",
  "revision",
  "size_bytes",
  "last_modified",
  "storage_class",
] as const;
const MAX_TEXT_BYTES = 4096;
const MAX_SIZE = 2 ** 53 - 1;

// Fixed-width UTC text: exactly nine fraction digits, real Gregorian dates,
// years 0001-9999, seconds 00-59 (I4). Fixed width makes text order equal time
// order, so instants compare as strings without losing nanoseconds.
const INSTANT = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.\d{9}Z$/;

function checkInstant(value: unknown): string {
  refuse(typeof value === "string", "invalid_instant");
  const m = INSTANT.exec(value);
  refuse(m, "invalid_instant");
  const [y, mo, d, h, mi, s] = m.slice(1).map(Number);
  refuse(y >= 1 && mo >= 1 && mo <= 12 && h <= 23 && mi <= 59 && s <= 59, "invalid_instant");
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1];
  refuse(d >= 1 && d <= days, "invalid_instant");
  return value;
}

function compareRows(a: { namespace: string; key: string }, b: { namespace: string; key: string }) {
  return (
    compareBytes(utf8.encode(a.namespace), utf8.encode(b.namespace)) ||
    compareBytes(utf8.encode(a.key), utf8.encode(b.key))
  );
}

const rowId = (r: { namespace: string; key: string }) => JSON.stringify([r.namespace, r.key]);

function checkScalar(value: string) {
  for (let i = 0; i < value.length; i++) {
    const n = value.charCodeAt(i);
    if (n >= 0xd800 && n <= 0xdbff) {
      const next = value.charCodeAt(++i);
      refuse(next >= 0xdc00 && next <= 0xdfff, "invalid_unicode");
    } else refuse(n < 0xdc00 || n > 0xdfff, "invalid_unicode");
  }
}
function checkText(value: string) {
  checkScalar(value);
  refuse(utf8.encode(value).length <= MAX_TEXT_BYTES, "capacity");
}

const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const KIND = /^[a-z][a-z0-9._-]{0,63}$/;
const ATTRIBUTE_NAME = /^[a-z][a-z0-9._-]{0,127}$/;
function closed(value: unknown, fields: string[]): value is JsonObject {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).length === fields.length &&
    fields.every((f) => Object.hasOwn(value, f))
  );
}
function checkRevision(value: unknown) {
  refuse(
    closed(value, ["kind", "value"]) &&
      typeof value.kind === "string" &&
      KIND.test(value.kind) &&
      typeof value.value === "string" &&
      value.value.length > 0 &&
      Array.from(value.value).length <= 4096,
    "invalid_shape",
  );
  checkScalar(value.value);
}
function checkStamp(value: unknown) {
  refuse(
    closed(value, ["snapshot_id", "at"]) &&
      typeof value.snapshot_id === "string" &&
      ID.test(value.snapshot_id),
    "invalid_shape",
  );
  checkInstant(value.at);
}
function checkAttribute(value: unknown) {
  refuse(
    closed(value, ["name", "value", "operation", "observed_at", "against_revision"]) &&
      typeof value.name === "string" &&
      ATTRIBUTE_NAME.test(value.name) &&
      (value.value === null ||
        (typeof value.value === "string" && Array.from(value.value).length <= 65536)) &&
      typeof value.operation === "string" &&
      ID.test(value.operation),
    "invalid_shape",
  );
  if (typeof value.value === "string") {
    // Attribute values have a larger character ceiling than keys.
    for (const c of value.value) {
      const n = c.codePointAt(0);
      refuse(n !== undefined && (n < 0xd800 || n > 0xdfff), "invalid_unicode");
    }
  }
  checkRevision(value.against_revision);
  checkInstant(value.observed_at);
}

function checkSource(o: Record<string, unknown>) {
  refuse(
    typeof o.namespace === "string" &&
      ID.test(o.namespace) &&
      typeof o.key === "string" &&
      o.key.length > 0 &&
      (o.storage_class === null ||
        (typeof o.storage_class === "string" && Array.from(o.storage_class).length <= 4096)),
    "invalid_shape",
  );
  if (o.revision !== null) checkRevision(o.revision);
  if (typeof o.storage_class === "string") checkScalar(o.storage_class);
  checkText(o.namespace as string);
  checkText(o.key as string);
  const size = o.size_bytes;
  refuse(
    exactInteger(o, "size_bytes") && (size as number) >= 0 && (size as number) <= MAX_SIZE,
    "invalid_shape",
  );
  if (o.last_modified !== null) checkInstant(o.last_modified);
}

// Enrichments on a row: unique names, sorted by UTF-8 bytes, each bound to the
// row's non-null revision, and only on an active row (I6). A repeated name on a
// row is an ordering fault: names must be strictly increasing.
function checkEnrichments(row: Row) {
  refuse(Array.isArray(row.enrichments) && row.enrichments.length <= 256, "invalid_shape");
  for (const attribute of row.enrichments) checkAttribute(attribute);
  const names = row.enrichments.map((e) => e.name);
  for (let i = 1; i < names.length; i++) {
    refuse(compareBytes(utf8.encode(names[i - 1]), utf8.encode(names[i])) < 0, "enrichment_order");
  }
  for (const e of row.enrichments) {
    checkInstant(e.observed_at);
    refuse(row.deleted === null, "enrichment_target");
    refuse(row.revision !== null && same(e.against_revision, row.revision), "enrichment_revision");
  }
}

// Internal consistency of one row's lineage (I4).
function checkLineage(row: Row) {
  for (const s of [row.first_seen, row.last_seen, row.last_changed]) checkStamp(s);
  if (row.deleted !== null) checkStamp(row.deleted);
  refuse(
    row.first_seen.at <= row.last_seen.at && row.first_seen.at <= row.last_changed.at,
    "lineage_order",
  );
  if (row.deleted) {
    refuse(row.deleted.at >= row.last_seen.at, "lineage_order");
    refuse(same(row.deleted, row.last_changed), "lineage_order");
  }
}

const ROW_FIELDS = [
  ...SOURCE_FIELDS,
  "first_seen",
  "last_seen",
  "last_changed",
  "deleted",
  "enrichments",
];

// Rows are closed objects: exactly the row fields, nothing more (I4).
function checkRowShape(row: Row) {
  refuse(row !== null && typeof row === "object" && !Array.isArray(row), "invalid_shape");
  const keys = Object.keys(row);
  refuse(
    keys.length === ROW_FIELDS.length && ROW_FIELDS.every((f) => keys.includes(f)),
    "invalid_shape",
  );
}

function sourceChanged(row: Row, obs: Record<string, unknown>): boolean {
  return SOURCE_FIELDS.slice(2).some((f) => !same(row[f], obs[f]));
}

type Ack = {
  parent_sha256: string;
  plan_digest: string;
  acknowledged_by: string;
  acknowledged_at: string;
} | null;

type Transition = {
  mode: "baseline" | "observe" | "enrich";
  set_id: string;
  snapshot_id: string;
  generation: number;
  observation_at: string | null;
  discovery_complete: boolean;
  parent: null | {
    publication_sha256: string;
    set_id: string;
    snapshot_id: string;
    generation: number;
    scopes: Scope[];
    rows: Row[];
    ancestor_snapshot_ids?: string[];
  };
  admitted_parent_sha256: string | null;
  scopes: Scope[];
  acknowledgment: Ack;
  observations: Record<string, unknown>[];
  absence_authority: Scope[];
  enrichments: { namespace: string; key: string; attribute: Attribute }[];
};

type Outcome = {
  rows: Row[];
  admission: string;
  retained_unobserved_rows: number;
};

function transition(t: Transition): Outcome {
  refuse(exactInteger(t, "generation"), "invalid_shape");
  if (t.parent) refuse(exactInteger(t.parent, "generation"), "invalid_shape");
  // Plan scopes are bounded in UTF-8 bytes (I2) before any use of them.
  for (const scope of t.scopes) {
    checkText(scope.namespace);
    checkText(scope.prefix);
  }
  // Plan identity (I2): the wire plan must already be canonical; readers refuse
  // noncanonical lists rather than repair them.
  refuse(same(t.scopes, canonical(t.scopes)), "noncanonical_plan");

  if (t.mode === "baseline") {
    refuse(
      t.parent === null && t.generation === 0 && t.acknowledgment === null,
      "invalid_baseline",
    );
  } else {
    refuse(t.parent !== null, "parent_unavailable");
  }
  const parent = t.parent;
  const parentRows = parent ? parent.rows : [];

  if (parent) {
    // A successor naming its own snapshot as parent reuses that snapshot; an
    // ancestor further back that repeats it is a cycle (I5).
    refuse(parent.snapshot_id !== t.snapshot_id, "snapshot_reuse");
    refuse(!(parent.ancestor_snapshot_ids ?? []).includes(t.snapshot_id), "parent_cycle");
    refuse(parent.set_id === t.set_id, "set_mismatch");
    refuse(t.generation === parent.generation + 1, "generation_mismatch");
    refuse(t.admitted_parent_sha256 === parent.publication_sha256, "stale_parent");
  }

  // Inherited rows: strictly ordered, unique, and individually valid (I4).
  for (const row of parentRows) {
    checkRowShape(row);
    checkSource(row);
    checkLineage(row);
    checkEnrichments(row);
  }
  for (let i = 1; i < parentRows.length; i++) {
    const c = compareRows(parentRows[i - 1], parentRows[i]);
    refuse(c !== 0, "duplicate_key_row");
    refuse(c < 0, "row_order");
  }
  const seenTimes = new Map<string, string>();
  for (const row of parentRows) {
    for (const s of [row.first_seen, row.last_seen, row.last_changed, row.deleted]) {
      if (!s) continue;
      refuse(s.snapshot_id !== t.snapshot_id, "fabricated_freshness");
      const prior = seenTimes.get(s.snapshot_id);
      refuse(prior === undefined || prior === s.at, "stamp_conflict");
      seenTimes.set(s.snapshot_id, s.at);
    }
  }

  if (t.mode === "enrich") {
    refuse(parent !== null, "parent_unavailable");
    return enrich(t, parent, parentRows);
  }

  // Observation successor or baseline.
  refuse(t.discovery_complete, "discovery_failed");
  const at = checkInstant(t.observation_at);
  const now: Stamp = { snapshot_id: t.snapshot_id, at };
  for (const row of parentRows) {
    for (const s of [row.first_seen, row.last_seen, row.last_changed, row.deleted]) {
      if (s) refuse(s.at <= at, "clock_reversal");
    }
  }
  for (const scope of t.absence_authority) {
    refuse(
      t.scopes.some((p) => covers(p, scope)),
      "coverage_outside_plan",
    );
  }

  const observed = new Map<string, Record<string, unknown>>();
  for (const obs of t.observations) {
    refuse(
      Object.keys(obs).length === SOURCE_FIELDS.length && SOURCE_FIELDS.every((f) => f in obs),
      "observation_fields",
    );
    checkSource(obs);
    refuse(
      t.scopes.some((s) => contains(s, obs.namespace as string, obs.key as string)),
      "observation_outside_plan",
    );
    const id = rowId(obs as Row);
    refuse(!observed.has(id), "duplicate_observation");
    observed.set(id, obs);
  }

  // Admission (I5 steps 3-4).
  let admission: string;
  if (t.mode === "baseline") {
    admission = "baseline_not_compared";
  } else if (parent !== null && loses(parent.scopes, t.scopes)) {
    const ack = t.acknowledgment;
    refuse(ack !== null, "scope_loss");
    refuse(
      ack.parent_sha256 === parent.publication_sha256 &&
        ack.plan_digest === sha256(planBytes(t.set_id, t.scopes)),
      "acknowledgment_mismatch",
    );
    refuse(
      typeof ack.acknowledged_by === "string" && ID.test(ack.acknowledged_by),
      "acknowledgment_actor",
    );
    checkInstant(ack.acknowledged_at);
    admission = "loss_acknowledged";
  } else {
    refuse(t.acknowledgment === null, "unexpected_acknowledgment");
    admission = "no_loss";
  }

  const byId = new Map(parentRows.map((r) => [rowId(r), r]));
  const out: Row[] = [];
  const ids = new Set([...byId.keys(), ...observed.keys()]);
  for (const id of ids) {
    const prior = byId.get(id);
    const obs = observed.get(id);
    if (obs) {
      if (!prior) {
        out.push({
          ...(Object.fromEntries(SOURCE_FIELDS.map((f) => [f, obs[f]])) as Pick<
            Row,
            (typeof SOURCE_FIELDS)[number]
          >),
          first_seen: now,
          last_seen: now,
          last_changed: now,
          deleted: null,
          enrichments: [],
        });
        continue;
      }
      const reappeared = prior.deleted !== null;
      const changed = reappeared || sourceChanged(prior, obs);
      const revisionKept = obs.revision !== null && same(obs.revision, prior.revision);
      out.push({
        ...prior,
        ...(Object.fromEntries(SOURCE_FIELDS.map((f) => [f, obs[f]])) as object),
        last_seen: now,
        last_changed: changed ? now : prior.last_changed,
        deleted: null,
        enrichments: revisionKept && !reappeared ? prior.enrichments : [],
      } as Row);
      continue;
    }
    // Not observed: the row is inherited from the parent. Tombstone it only
    // under absence authority; otherwise retain it unchanged.
    if (prior === undefined) continue;
    const authorized = t.absence_authority.some((s) => contains(s, prior.namespace, prior.key));
    if (authorized && prior.deleted === null) {
      out.push({ ...prior, last_changed: now, deleted: now, enrichments: [] });
    } else {
      out.push(prior);
    }
  }

  applyEnrichments(out, t.enrichments);
  out.sort(compareRows);
  return {
    rows: out,
    admission,
    retained_unobserved_rows: out.filter((r) => r.last_seen.snapshot_id !== t.snapshot_id).length,
  };
}

// Apply attribute updates to active rows whose current revision they match.
function applyEnrichments(rows: Row[], updates: Transition["enrichments"]) {
  const byId = new Map(rows.map((r) => [rowId(r), r]));
  // One update per row/attribute; a repeat is refused, never last-write-wins (I6).
  for (const update of updates) checkAttribute(update.attribute);
  const targets = updates.map((u) => JSON.stringify([u.namespace, u.key, u.attribute.name]));
  refuse(new Set(targets).size === targets.length, "duplicate_enrichment");
  for (const u of updates) {
    const row = byId.get(rowId(u));
    refuse(row !== undefined && row.deleted === null, "enrichment_target");
    refuse(
      row.revision !== null && same(u.attribute.against_revision, row.revision),
      "enrichment_revision",
    );
    checkInstant(u.attribute.observed_at);
    const existing = row.enrichments.find((e) => e.name === u.attribute.name);
    if (existing) refuse(u.attribute.observed_at >= existing.observed_at, "stale_enrichment");
    row.enrichments = [
      ...row.enrichments.filter((e) => e.name !== u.attribute.name),
      { ...u.attribute },
    ].sort((a, b) => compareBytes(utf8.encode(a.name), utf8.encode(b.name)));
  }
  for (const row of rows) checkEnrichments(row);
}

// An enrich successor changes only enrichments (I6).
function enrich(
  t: Transition,
  parent: NonNullable<Transition["parent"]>,
  parentRows: Row[],
): Outcome {
  refuse(
    t.observation_at === null && t.observations.length === 0 && t.absence_authority.length === 0,
    "enrichment_observation",
  );
  refuse(same(t.scopes, parent.scopes) && t.acknowledgment === null, "enrichment_scope_change");
  const rows = parentRows.map((r) => ({
    ...r,
    enrichments: [...r.enrichments],
  }));
  applyEnrichments(rows, t.enrichments);
  return {
    rows,
    admission: "inherited",
    retained_unobserved_rows: rows.length,
  };
}

function evaluate(t: Transition): Outcome | { refusal: string } {
  try {
    return transition(clone(t));
  } catch (e) {
    if (e instanceof Refusal) return { refusal: e.reason };
    throw e;
  }
}

const SCHEMAS = join(ROOT, "schemas/durable-index/v0");

// A strict recursive descent parser detects duplicate names before object creation,
// validates scalar Unicode, and limits nesting before the engine sees the input.
function strictJSON(bytes: Uint8Array): unknown {
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw new Refusal("invalid_unicode");
  }
  let pos = 0;
  const ws = () => {
    while (/[\x20\t\r\n]/.test(text[pos] ?? "\0")) pos++;
  };
  const string = (): string => {
    const start = pos++;
    while (pos < text.length) {
      const c = text[pos++];
      if (c === '"') {
        let value: string;
        try {
          value = JSON.parse(text.slice(start, pos));
        } catch {
          throw new Refusal("invalid_json");
        }
        for (let i = 0; i < value.length; i++) {
          const n = value.charCodeAt(i);
          if (n >= 0xd800 && n <= 0xdbff) {
            const next = value.charCodeAt(++i);
            refuse(next >= 0xdc00 && next <= 0xdfff, "invalid_unicode");
          } else refuse(n < 0xdc00 || n > 0xdfff, "invalid_unicode");
        }
        return value;
      }
      if (c === "\\") {
        pos++;
      }
    }
    throw new Refusal("invalid_json");
  };
  const value = (depth: number): unknown => {
    ws();
    const c = text[pos];
    if (c === '"') return string();
    if (c === "{" || c === "[") {
      refuse(depth < 256, "invalid_json");
      pos++;
      ws();
      const object = c === "{";
      const end = object ? "}" : "]";
      const out: JsonObject = object ? Object.create(null) : [];
      const keys = new Set<string>();
      const assign = (key: string, item: unknown) => {
        if (item && typeof item === "object" && numericToken in item) {
          out[key] = (item as NumericToken).value;
          let facts = numericIntegrality.get(out);
          if (!facts) {
            facts = new Map();
            numericIntegrality.set(out, facts);
          }
          facts.set(key, (item as NumericToken).integral);
        } else out[key] = item;
      };
      if (text[pos] === end) {
        pos++;
        return out;
      }
      while (true) {
        if (object) {
          refuse(text[pos] === '"', "invalid_json");
          const key = string();
          refuse(!keys.has(key), "duplicate_key");
          keys.add(key);
          ws();
          refuse(text[pos++] === ":", "invalid_json");
          assign(key, value(depth + 1));
        } else assign(String(out.length), value(depth + 1));
        ws();
        if (text[pos] === end) {
          pos++;
          return out;
        }
        refuse(text[pos++] === ",", "invalid_json");
        ws();
      }
    }
    const match = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(
      text.slice(pos),
    );
    refuse(match, "invalid_json");
    pos += match[0].length;
    const parsed = JSON.parse(match[0]);
    refuse(typeof parsed !== "number" || Number.isFinite(parsed), "invalid_json");
    if (typeof parsed === "number") {
      const [coefficient, exponentText] = match[0].toLowerCase().split("e");
      const parts = coefficient.replace(/^-/, "").split(".");
      const digits = parts.join("");
      const scale = (parts[1]?.length ?? 0) - Number(exponentText ?? 0);
      const trailing = digits.length - digits.replace(/0+$/, "").length;
      const integral = /^0+$/.test(digits) || scale <= 0 || trailing >= scale;
      return { [numericToken]: true, value: parsed, integral };
    }
    return parsed;
  };
  const result = value(0);
  ws();
  refuse(pos === text.length, "invalid_json");
  if (result && typeof result === "object" && numericToken in result)
    return (result as NumericToken).value;
  return result;
}

function readRows(members: Row[][]): { row_count: number } {
  let previous: Row | undefined;
  let count = 0;
  const times = new Map<string, string>();
  for (const member of members)
    for (const row of member) {
      checkRowShape(row);
      checkSource(row);
      checkLineage(row);
      checkEnrichments(row);
      if (previous) {
        const order = compareRows(previous, row);
        refuse(order !== 0, "duplicate_key_row");
        refuse(order < 0, "row_order");
      }
      for (const stamp of [row.first_seen, row.last_seen, row.last_changed, row.deleted]) {
        if (!stamp) continue;
        const known = times.get(stamp.snapshot_id);
        refuse(known === undefined || known === stamp.at, "stamp_conflict");
        times.set(stamp.snapshot_id, stamp.at);
      }
      previous = row;
      count++;
    }
  return { row_count: count };
}

function bound(pin: Binding, store: Record<string, string>, parse = true): JsonObject {
  refuse(exactInteger(pin, "byte_length"), "invalid_shape");
  const raw = store[pin.ref];
  refuse(raw !== undefined, "binding_unavailable");
  const bytes = utf8.encode(raw);
  refuse(bytes.length === pin.byte_length && sha256(bytes) === pin.sha256, "binding_integrity");
  return parse ? strictJSON(bytes) : raw;
}

function checkMetadataProfile(metadata: JsonObject) {
  refuse(
    metadata.kind === "index_metadata" &&
      metadata.row_profile === "object-inventory/v0" &&
      metadata.encoding_profile === "parquet-inventory/v0" &&
      Array.isArray(metadata.capabilities) &&
      metadata.capabilities.includes("contract: durable-index/v0"),
    "graph_profile",
  );
}

function bindings(input: JsonObject): unknown {
  const m = input.metadata;
  checkMetadataProfile(m);
  const store = input.store;
  refuse(
    exactInteger(m, "generation") &&
      exactInteger(m, "effective_scope_count") &&
      exactInteger(m, "retained_unobserved_rows"),
    "invalid_shape",
  );
  if (m.mode === "enrich") {
    const parent = input.inherited_from.metadata;
    refuse(
      same(m.plan, parent.plan) &&
        same(m.coverage, parent.coverage) &&
        m.plan_digest === parent.plan_digest &&
        m.effective_scope_count === parent.effective_scope_count,
      "coverage_inheritance",
    );
    return { absence_authority: [] };
  }
  const plan = bound(m.plan, store);
  refuse(
    plan.set_id === m.selection.namespace_id &&
      m.plan.id === plan.set_id &&
      plan.kind === "index_plan" &&
      plan.scope_profile === "unicode-prefix/v0" &&
      plan.capabilities?.includes("contract: durable-index/v0"),
    "plan_identity",
  );
  refuse(plan.scopes.length <= 65536, "capacity");
  for (const scope of plan.scopes) {
    checkText(scope.namespace);
    checkText(scope.prefix);
  }
  refuse(same(plan.scopes, canonical(plan.scopes)), "noncanonical_plan");
  refuse(m.effective_scope_count === plan.scopes.length, "scope_count");
  refuse(m.plan_digest === sha256(planBytes(plan.set_id, plan.scopes)), "plan_digest");
  refuse(m.coverage.length === plan.scopes.length, "coverage_count");
  refuse(
    new Set(m.coverage.map((p: Binding) => p.ref)).size === m.coverage.length,
    "binding_alias",
  );
  refuse(
    new Set(m.coverage.map((p: Binding) => p.id)).size === m.coverage.length,
    "coverage_identity",
  );
  const observedIds = new Set<string>();
  for (const observation of input.observations) {
    refuse(closed(observation, [...SOURCE_FIELDS]), "observation_fields");
    checkSource(observation);
    refuse(
      plan.scopes.some((scope: Scope) => contains(scope, observation.namespace, observation.key)),
      "observation_outside_plan",
    );
    const id = rowId(observation);
    refuse(!observedIds.has(id), "duplicate_observation");
    observedIds.add(id);
  }
  const authority: Scope[] = [];
  const selection = m.selection;
  const uri =
    "snapshot:" +
    sha256(
      utf8.encode(
        `segmented-snapshot/v0/subject\0${selection.namespace_id}\0${selection.snapshot_id}`,
      ),
    );
  for (let i = 0; i < plan.scopes.length; i++) {
    const pin = m.coverage[i],
      scope = plan.scopes[i],
      att = bound(pin, store);
    refuse(pin.id === att.attestation_id, "coverage_identity");
    const claim = att.claims[0];
    const wireScope = {
      partition: { namespace: scope.namespace },
      ...(scope.prefix ? { prefix: scope.prefix } : {}),
    };
    refuse(
      att.claims.length === 1 && att.supersedes === undefined && same(claim.scope, wireScope),
      "coverage_scope",
    );
    refuse(
      att.subject.artifact_id === selection.artifact_id &&
        att.subject.grain_id === input.grain_id &&
        att.subject.subject_uri === uri,
      "coverage_subject",
    );
    refuse(
      att.emitter.relation === "producer" && att.emitter.run_id === selection.snapshot_id,
      "coverage_emitter",
    );
    refuse(att.as_of === m.observation_at, "coverage_time");
    const count = input.observations.filter((o: Row) => contains(scope, o.namespace, o.key)).length;
    const volume = claim.volume;
    refuse(
      volume &&
        volume.unit === "objects" &&
        exactInteger(volume, "observed") &&
        volume.observed === count &&
        (volume.expected === undefined ||
          (exactInteger(volume, "expected") && volume.expected >= count)),
      "coverage_volume",
    );
    const gaps = att.gaps ?? [];
    for (const gap of gaps) {
      const gs = gap.scope;
      refuse(
        gs &&
          gs.partition?.namespace === scope.namespace &&
          typeof (gs.prefix ?? "") === "string" &&
          covers(scope, { namespace: gs.partition.namespace, prefix: gs.prefix ?? "" }),
        "coverage_gap",
      );
    }
    refuse(att.coverage_state !== "complete" || gaps.length === 0, "coverage_complete_gap");
    if (
      att.coverage_state === "complete" &&
      claim.basis === "confirmed" &&
      ["enumerated", "reconciled"].includes(claim.method)
    ) {
      const observed = new Set(input.observations.map(rowId));
      refuse(
        input.enumerated.every(
          (e: Row) => !contains(scope, e.namespace, e.key) || observed.has(rowId(e)),
        ),
        "enumerated_key_omitted",
      );
      authority.push(scope);
    }
  }
  return { absence_authority: authority };
}

function metadataAck(metadata: JsonObject): Ack {
  const ack = metadata.loss_acknowledgment;
  if (ack === null) return null;
  refuse(ack && metadata.parent && same(ack.parent, metadata.parent), "acknowledgment_mismatch");
  return {
    parent_sha256: ack.parent.publication.sha256,
    plan_digest: ack.plan_sha256,
    acknowledged_by: ack.acknowledged_by,
    acknowledged_at: ack.acknowledged_at,
  };
}

function boundTransition(input: JsonObject): unknown {
  const evidence = input.evidence,
    t = clone(input.transition),
    m = evidence.metadata;
  const plan = bound(m.plan, evidence.store);
  const authority = bindings(evidence) as { absence_authority: Scope[] };
  refuse(
    m.mode === t.mode &&
      m.generation === t.generation &&
      m.selection.namespace_id === t.set_id &&
      m.selection.snapshot_id === t.snapshot_id &&
      m.observation_at === t.observation_at &&
      same(metadataAck(m), t.acknowledgment) &&
      same(plan.scopes, t.scopes) &&
      same(evidence.observations, t.observations) &&
      (t.parent === null
        ? m.parent === null
        : m.parent !== null &&
          m.parent.selection.namespace_id === t.parent.set_id &&
          m.parent.selection.snapshot_id === t.parent.snapshot_id &&
          m.parent.publication.sha256 === t.parent.publication_sha256),
    "metadata_transition",
  );
  t.absence_authority = authority.absence_authority;
  const out = transition(t);
  refuse(
    m.admission === out.admission && m.retained_unobserved_rows === out.retained_unobserved_rows,
    "metadata_transition",
  );
  return out;
}

function cutover(input: JsonObject): unknown {
  const r = input.record;
  refuse(r !== null, "cutover_required");
  refuse(input.authorized_actors.includes(r.authorized_by), "cutover_actor");
  refuse(same(r.rollback, r.old.publication), "cutover_rollback");
  const old = bound(r.old.publication, input.store);
  const next = bound(r.new.publication, input.store);
  refuse(
    old.publication_id === r.old.publication.id &&
      next.publication_id === r.new.publication.id &&
      same(old.selection, r.old.selection) &&
      same(next.selection, r.new.selection) &&
      !same(r.old.publication, r.new.publication) &&
      r.old.selection.snapshot_id !== r.new.selection.snapshot_id,
    "cutover_selection",
  );
  const manifest = bound(next.manifest, input.store);
  const metadata = bound(manifest.profile_metadata, input.store);
  refuse(
    same(manifest.selection, r.new.selection) && same(metadata.selection, r.new.selection),
    "cutover_selection",
  );
  refuse(
    metadata.mode === "baseline" &&
      exactInteger(metadata, "generation") &&
      metadata.generation === 0 &&
      metadata.parent === null,
    "cutover_baseline",
  );
  refuse(checkInstant(r.accepted_at) >= checkInstant(metadata.observation_at), "cutover_time");
  return { cutover: "explicit_baseline" };
}

function graph(input: JsonObject): JsonObject {
  refuse(input.projection === "logical-only/v0", "graph_profile");
  const store = input.store;
  const seen = new Set<string>();
  const snapshotIds = new Set<string>();
  const visit = (pin: Binding, depth: number): JsonObject => {
    refuse(depth < 64, "capacity");
    refuse(!seen.has(pin.sha256), "parent_cycle");
    seen.add(pin.sha256);
    let metadataBytes = 0;
    const refs = new Set<string>();
    const fetch = (p: Binding, member = false, parse = true): JsonObject => {
      refuse(p && typeof p.ref === "string", "graph_dependency");
      if (!member && !refs.has(p.ref)) {
        metadataBytes += p.byte_length;
        refs.add(p.ref);
      }
      return bound(p, store, parse);
    };
    const pub = fetch(pin);
    refuse(!snapshotIds.has(pub.selection.snapshot_id), "parent_cycle");
    snapshotIds.add(pub.selection.snapshot_id);
    refuse(pub.publication_id === pin.id, "graph_identity");
    refuse(
      pub.state === "committed" &&
        pub.kind === "snapshot_publication" &&
        pub.capabilities.includes("contract: segmented-snapshot/v0") &&
        pub.capabilities.includes("contract: durable-index/v0"),
      "graph_publication",
    );
    const manifest = fetch(pub.manifest),
      profile = fetch(pub.profile),
      descriptor = fetch(pub.descriptor);
    refuse(
      same(pub.selection, manifest.selection) &&
        pub.manifest.id === pub.selection.snapshot_id &&
        pub.descriptor.id === pub.selection.artifact_id,
      "graph_identity",
    );
    refuse(
      manifest.kind === "snapshot_manifest" &&
        Array.isArray(manifest.capabilities) &&
        manifest.capabilities.includes("contract: segmented-snapshot/v0") &&
        manifest.capabilities.includes("contract: durable-index/v0") &&
        profile.profile_id === "example.index-logical/v0" &&
        pub.profile.id === profile.profile_id &&
        same(pub.profile, manifest.profile) &&
        profile.operations.includes("full_verify") &&
        manifest.count_relation === "equal" &&
        manifest.physical_order === "manifest_order",
      "graph_profile",
    );
    fetch(profile.semantic_spec, false, false);
    refuse(
      profile.semantic_spec.id === profile.profile_id &&
        profile.semantic_spec.sha256 ===
          sha256(readFileSync(join(SCHEMAS, "fixtures/logical-profile.md"))) &&
        same(profile.capabilities, ["contract: segmented-snapshot/v0"]) &&
        profile.kind === "snapshot_profile" &&
        same(profile.operations, ["full_verify"]) &&
        same(profile.count_relations, ["equal"]) &&
        same(profile.physical_orders, ["manifest_order"]) &&
        profile.empty_snapshots === true &&
        profile.streaming === "unsupported" &&
        profile.durability_claim === "none" &&
        profile.retention === "unsupported",
      "graph_profile",
    );
    refuse(["complete", "partial"].includes(descriptor.lifecycle), "graph_publication");
    refuse(manifest.profile_metadata, "graph_dependency");
    const metadata = fetch(manifest.profile_metadata);
    checkMetadataProfile(metadata);
    refuse(
      same(metadata.selection, pub.selection) &&
        manifest.profile_metadata.id === pub.selection.snapshot_id,
      "graph_identity",
    );
    refuse(
      !manifest.members.some((m: Binding) => m.ref === manifest.profile_metadata.ref),
      "binding_alias",
    );
    refuse(
      exactInteger(profile.limits, "max_members") &&
        exactInteger(profile.limits, "max_metadata_bytes") &&
        exactInteger(profile.limits, "max_member_bytes") &&
        profile.limits.max_members <= 16 &&
        profile.limits.max_metadata_bytes <= 1048576 &&
        profile.limits.max_member_bytes <= 1048576 &&
        manifest.members.length <= profile.limits.max_members,
      "capacity",
    );
    refuse(
      new Set(manifest.members.map((m: Binding) => m.id)).size === manifest.members.length &&
        new Set(manifest.members.map((m: Binding) => m.ref)).size === manifest.members.length,
      "graph_members",
    );
    const schema = fetch(manifest.row_schema);
    refuse(
      manifest.row_schema.schema_id === "contract:durable-index/v0/index-row.schema.json" &&
        schema.$id === manifest.row_schema.schema_id &&
        manifest.row_schema.sha256 === sha256(readFileSync(join(SCHEMAS, "index-row.schema.json"))),
      "graph_row_schema",
    );
    const catalog = fetch(manifest.field_catalog);
    refuse(
      catalog.id === manifest.field_catalog.id &&
        catalog.grain === manifest.grain_id &&
        Array.isArray(catalog.fields) &&
        catalog.fields.length === ROW_FIELDS.length &&
        (catalog.withheld_fields === undefined ||
          (Array.isArray(catalog.withheld_fields) && catalog.withheld_fields.length === 0)) &&
        (catalog.withheld_field_count === undefined ||
          (exactInteger(catalog, "withheld_field_count") && catalog.withheld_field_count === 0)) &&
        new Set(catalog.fields.map((f: JsonObject) => f.name)).size === catalog.fields.length &&
        ROW_FIELDS.every((f, i) =>
          catalog.fields.some(
            (x: JsonObject) =>
              x.name === f &&
              x.required === true &&
              x.type ===
                [
                  "string",
                  "string",
                  "object",
                  "integer",
                  "datetime",
                  "string",
                  "object",
                  "object",
                  "object",
                  "object",
                  "array",
                ][i],
          ),
        ),
      "graph_catalog",
    );
    if (descriptor.field_catalogs !== undefined) {
      refuse(Array.isArray(descriptor.field_catalogs), "graph_catalog");
      const embedded = descriptor.field_catalogs.filter((c: JsonObject) => c.id === catalog.id);
      refuse(
        embedded.length <= 1 && embedded.every((c: JsonObject) => same(c, catalog)),
        "graph_catalog",
      );
    }
    const grain = descriptor.grains.find((g: JsonObject) => g.id === manifest.grain_id);
    const rep = descriptor.representations.find(
      (r: JsonObject) => r.id === manifest.representation_id,
    );
    refuse(
      grain &&
        rep &&
        descriptor.artifact_id === pub.selection.artifact_id &&
        descriptor.capabilities.includes("contract: data-artifact/v0") &&
        descriptor.producer.profile === profile.profile_id &&
        grain.kind === "record_stream" &&
        grain.record_kind === "object-inventory/v0" &&
        rep.grain === manifest.grain_id &&
        rep.role === "audit_stream" &&
        rep.format === "ndjson" &&
        rep.profile === profile.profile_id &&
        rep.uri === pub.manifest.ref &&
        rep.read_path?.physical_ordering === "manifest_order" &&
        rep.read_path?.sidecar_required === true &&
        typeof rep.read_path?.sharded === "boolean" &&
        typeof rep.read_path?.range_readable === "boolean" &&
        rep.read_path?.appendable === false &&
        same(rep.read_path?.scan_capabilities, []) &&
        rep.read_path?.read_path_granularity === "artifact" &&
        rep.read_path?.gateable_unit_granularity === "artifact" &&
        rep.protection_enforceable_granularity === "artifact" &&
        grain.field_catalog_ref === manifest.field_catalog.id &&
        rep.field_catalog_ref === manifest.field_catalog.id,
      "graph_descriptor",
    );
    refuse(descriptor.protection?.default_action === "block_export", "graph_descriptor");
    refuse(!input.request_export, "protected_export");
    fetch(metadata.plan);
    for (const coverage of metadata.coverage) fetch(coverage);
    refuse(metadataBytes <= profile.limits.max_metadata_bytes, "capacity");
    const members: Row[][] = [];
    for (const member of manifest.members) {
      refuse(
        exactInteger(member, "byte_length") &&
          member.byte_length <= profile.limits.max_member_bytes,
        "capacity",
      );
      const raw = store[member.ref];
      refuse(raw !== undefined, "binding_unavailable");
      const bytes = utf8.encode(raw);
      refuse(
        bytes.length === member.byte_length && sha256(bytes) === member.sha256,
        "binding_integrity",
      );
      const lines = raw.split("\n");
      refuse(lines.pop() === "", "invalid_json");
      const rows = lines.map((line: string) => strictJSON(utf8.encode(line)) as Row);
      refuse(exactInteger(member, "row_count") && rows.length === member.row_count, "graph_count");
      members.push(rows);
    }
    const count = readRows(members).row_count;
    refuse(
      exactInteger(manifest, "physical_row_count") &&
        exactInteger(grain, "row_count") &&
        exactInteger(rep, "row_count") &&
        count === manifest.physical_row_count &&
        count === grain.row_count &&
        count === rep.row_count,
      "graph_count",
    );
    let parent: JsonObject | null = null;
    if (metadata.parent) {
      parent = visit(metadata.parent.publication, depth + 1);
      refuse(same(metadata.parent.selection, parent.selection), "graph_identity");
    }
    const evidence = input.source_evidence[pub.selection.snapshot_id];
    refuse(evidence, "graph_evidence");
    const bindingInput = {
      metadata,
      store,
      grain_id: manifest.grain_id,
      observations: evidence.observations,
      enumerated: evidence.enumerated,
      inherited_from: parent ? { metadata: parent.metadata } : null,
    };
    const expectedUri =
      "snapshot:" +
      sha256(
        utf8.encode(
          `segmented-snapshot/v0/subject\0${pub.selection.namespace_id}\0${pub.selection.snapshot_id}`,
        ),
      );
    refuse(manifest.coverage_subject_uri === expectedUri, "coverage_subject");
    const authority = bindings(bindingInput) as { absence_authority: Scope[] };
    const plan = bound(metadata.plan, store);
    const t: Transition = {
      mode: metadata.mode,
      set_id: metadata.selection.namespace_id,
      snapshot_id: metadata.selection.snapshot_id,
      generation: metadata.generation,
      observation_at: metadata.observation_at,
      discovery_complete: evidence.discovery_complete,
      parent: parent
        ? {
            publication_sha256: metadata.parent.publication.sha256,
            set_id: parent.selection.namespace_id,
            snapshot_id: parent.selection.snapshot_id,
            generation: parent.metadata.generation,
            scopes: parent.scopes,
            rows: parent.rows,
          }
        : null,
      admitted_parent_sha256: evidence.admitted_parent_sha256,
      scopes: plan.scopes,
      acknowledgment: metadataAck(metadata),
      observations: evidence.observations,
      absence_authority: authority.absence_authority,
      enrichments: evidence.enrichments,
    };
    const out = transition(t);
    const rows = members.flat();
    refuse(
      same(rows, out.rows) &&
        metadata.admission === out.admission &&
        metadata.retained_unobserved_rows === out.retained_unobserved_rows,
      "graph_transition",
    );
    const classes = ["public", "internal", "controlled", "restricted", "unknown"];
    const classifications = [
      descriptor.protection.default_export_class,
      ...catalog.fields.map((f: JsonObject) => f.sensitivity),
      ...(parent ? [parent.classification] : []),
    ];
    refuse(
      classifications.every((c: string) => classes.includes(c)),
      "graph_catalog",
    );
    const classification =
      classes[Math.max(...classifications.map((c: string) => classes.indexOf(c)))];
    return { rows, metadata, selection: pub.selection, scopes: plan.scopes, classification };
  };
  const result = visit(input.publication, 0);
  return {
    rows: result.rows,
    retained_unobserved_rows: result.metadata.retained_unobserved_rows,
    generation: result.metadata.generation,
    protection: { action: "block_export", class: result.classification },
    evidence_scope: "logical_projection",
  };
}

function independentOutcome(runner: string, input: JsonObject): unknown {
  try {
    if (runner === "parsing") {
      strictJSON(Buffer.from(input.hex, "hex"));
      return { valid: true };
    }
    if (runner === "rows") return readRows(input.members);
    if (runner === "bindings") return bindings(input);
    if (runner === "cutover") return cutover(input);
    if (runner === "graphs") return graph(input);
    if (runner === "cutover_graphs") {
      const receipt = cutover(input) as { cutover: string };
      refuse(
        same(input.record.old.publication, input.old_graph.publication) &&
          same(input.record.new.publication, input.new_graph.publication),
        "cutover_selection",
      );
      graph(input.old_graph);
      graph(input.new_graph);
      return { ...receipt, evidence_scope: "logical_projection" };
    }
    if (runner === "bound_transitions") return boundTransition(input);
    throw new Error(`unsupported runner ${runner}`);
  } catch (e) {
    if (e instanceof Refusal) return { refusal: e.reason };
    throw e;
  }
}

function checkIndependent(path: string): Result {
  const c = readJson(join(SCHEMAS, path));
  const base = c.baseline ? readJson(join(SCHEMAS, c.baseline)) : c;
  const input = overlay(base.input, c.replace ?? {});
  if (input.store) {
    Object.assign(input.store, c.store_overlay ?? {});
    for (const ref of c.omit_refs ?? []) delete input.store[ref];
  }
  const got = independentOutcome(c.runner, input);
  return same(got, c.expected)
    ? { file: path, agree: true }
    : { file: path, agree: false, detail: describe(got, c.expected) };
}

function checkTransitionVector(file: string): Result {
  const v = readJson(join(VECTORS, "transitions", file));
  const got = evaluate(v.input);
  return same(got, v.expected)
    ? { file: `transitions/${file}`, agree: true }
    : {
        file: `transitions/${file}`,
        agree: false,
        detail: describe(got, v.expected),
      };
}

function checkTransitionReject(dir: string): Result {
  const c = readJson(join(SCHEMAS, "rejects/semantic", dir, "case.json"));
  const base = readJson(join(SCHEMAS, c.baseline));
  const got = evaluate(overlay(base.input, c.replace));
  return same(got, c.expected)
    ? { file: dir, agree: true }
    : { file: dir, agree: false, detail: describe(got, c.expected) };
}

function describe(got: unknown, want: unknown): string {
  const g = (got as { refusal?: string }).refusal ?? "accept";
  const w = (want as { refusal?: string }).refusal ?? "accept";
  return g === w ? "rows or counts differ" : `got ${g}, want ${w}`;
}

// Disagreements this reader keeps on purpose, each an open finding against the
// standard or a fixture, never resolved by copying the other checker. Each entry
// must name a current fixture and still disagree exactly as recorded: an entry
// that agrees, disagrees differently or matches no fixture fails the run, so a
// fix or a renamed fixture is noticed rather than silently absorbed. Every entry
// must be resolved before the next tagged release (PDR-0006 Rule 2c), so this
// table is empty at tag.
const KNOWN_DISAGREEMENTS: Record<string, string> = {};

const usedDisagreements = new Set<string>();

function report(label: string, results: Result[]): number {
  let failures = 0;
  let known = 0;
  for (const r of results) {
    const expected = KNOWN_DISAGREEMENTS[r.file];
    if (expected !== undefined) usedDisagreements.add(r.file);
    if (expected === undefined) {
      if (!r.agree) {
        console.error(`[!!] ${label} disagree: ${r.file} (${r.detail})`);
        failures++;
      }
    } else if (r.agree || r.detail !== expected) {
      console.error(
        `[!!] ${label} known disagreement changed: ${r.file} (${r.detail ?? "now agrees"})`,
      );
      failures++;
    } else {
      console.log(`[--] ${label} known disagreement: ${r.file} (${r.detail})`);
      known++;
    }
  }
  const agree = results.filter((r) => r.agree).length;
  console.log(`  ${label}: ${agree}/${results.length} agree, ${known} known disagreement(s)`);
  return failures;
}

// Compare manifest entries with the actual executions, not merely with the
// set of supported runner names. Each logical path must execute exactly once.
function inventoryFaults(listed: string[], executed: Map<string, number>): string[] {
  const faults: string[] = [];
  const counts = new Map<string, number>();
  for (const path of listed) counts.set(path, (counts.get(path) ?? 0) + 1);
  for (const [path, count] of counts) {
    if (count !== 1) faults.push(`listed ${count} times: ${path}`);
    const runs = executed.get(path) ?? 0;
    if (runs !== 1) faults.push(`executed ${runs} times: ${path}`);
  }
  for (const [path, count] of executed) {
    if (!counts.has(path)) faults.push(`unlisted execution (${count}): ${path}`);
  }
  return faults;
}

function main(): number {
  const json = (dir: string) =>
    readdirSync(dir)
      .filter((f) => f.endsWith(".json"))
      .sort();
  const rejectDirs = readdirSync(join(SCHEMAS, "rejects/semantic"))
    .filter((d) => {
      const c = readJson(join(SCHEMAS, "rejects/semantic", d, "case.json"));
      return c.runner === "transitions";
    })
    .sort();
  console.log("durable-index independent reader (logical; not a reference implementation)");
  let failures = 0;
  const cases = readJson(join(SCHEMAS, "cases.json"));
  const executed = new Map<string, number>();
  const record = (path: string, result: Result): Result => {
    executed.set(path, (executed.get(path) ?? 0) + 1);
    return result;
  };
  failures += report(
    "plan vectors",
    json(join(VECTORS, "plans")).map((file) => record(`vectors/plans/${file}`, checkPlan(file))),
  );
  failures += report(
    "transition vectors",
    json(join(VECTORS, "transitions")).map((file) =>
      record(`vectors/transitions/${file}`, checkTransitionVector(file)),
    ),
  );
  failures += report(
    "transition rejects",
    rejectDirs.map((dir) =>
      record(`rejects/semantic/${dir}/case.json`, checkTransitionReject(dir)),
    ),
  );
  for (const runner of [
    "rows",
    "parsing",
    "bindings",
    "cutover",
    "bound_transitions",
    "graphs",
    "cutover_graphs",
  ]) {
    const paths = cases.scenarios.filter((path: string) => {
      const c = readJson(join(SCHEMAS, path));
      return c.runner === runner;
    });
    failures += report(
      runner,
      paths.map((path: string) => record(path, checkIndependent(path))),
    );
  }
  // Mutations of independently accepted inputs must reach the named refusal.
  // These exercise the actual guards, not fixture-supplied expected outputs.
  const fixture = (p: string) => readJson(join(SCHEMAS, p)).input;
  const witnesses: [string, string, JsonObject, string][] = [];
  const rows = fixture("vectors/rows/two-members.json");
  rows.members[1][0] = clone(rows.members[0][0]);
  witnesses.push(["cross-member duplicate", "rows", rows, "duplicate_key_row"]);
  witnesses.push([
    "duplicate JSON name (escaped)",
    "parsing",
    { hex: Buffer.from('{"a":1,"\\u0061":2}').toString("hex") },
    "duplicate_key",
  ]);
  witnesses.push([
    "duplicate JSON name",
    "parsing",
    { hex: Buffer.from('{"a":1,"a":2}').toString("hex") },
    "duplicate_key",
  ]);
  const binding = fixture("vectors/bindings/baseline.json");
  binding.enumerated.push({ namespace: "objects", key: "alpha/.hidden" });
  witnesses.push(["omitted enumerated key", "bindings", binding, "enumerated_key_omitted"]);
  const receipt = fixture("vectors/cutover/explicit-new-set.json");
  receipt.record.rollback.sha256 = "0".repeat(64);
  witnesses.push(["rollback pin", "cutover", receipt, "cutover_rollback"]);
  const bt = fixture("vectors/bound_transitions/baseline.json");
  bt.evidence.metadata.retained_unobserved_rows++;
  witnesses.push(["retained count", "bound_transitions", bt, "metadata_transition"]);
  const projection = fixture("vectors/graphs/baseline.json");
  projection.request_export = true;
  witnesses.push(["protected export", "graphs", projection, "protected_export"]);
  const parent = fixture("vectors/graphs/observe.json");
  parent.source_evidence["snapshot-1"].admitted_parent_sha256 = "0".repeat(64);
  witnesses.push(["stale admission", "graphs", parent, "stale_parent"]);
  for (const [name, runner, input, reason] of witnesses) {
    const got = independentOutcome(runner, input) as { refusal?: string };
    if (got.refusal !== reason) {
      console.error(`[!!] mutation ${name}: got ${got.refusal ?? "accept"}, want ${reason}`);
      failures++;
    }
  }
  const reordered = fixture("vectors/bindings/baseline.json");
  const reorderedPin = reordered.metadata.coverage[0];
  const attestation = readJsonFromText(reordered.store[reorderedPin.ref]);
  const originalScope = attestation.claims[0].scope;
  attestation.claims[0].scope = {
    prefix: originalScope.prefix,
    partition: originalScope.partition,
  };
  const reorderedBytes = JSON.stringify(attestation);
  reordered.store[reorderedPin.ref] = reorderedBytes;
  reorderedPin.byte_length = utf8.encode(reorderedBytes).length;
  reorderedPin.sha256 = sha256(utf8.encode(reorderedBytes));
  const originalBinding = independentOutcome("bindings", fixture("vectors/bindings/baseline.json"));
  if (!same(independentOutcome("bindings", reordered), originalBinding)) {
    console.error("[!!] reordered coverage scope changed authority");
    failures++;
  }
  // Exercise wire acknowledgments through both metadata-bound transitions and
  // complete graphs, with each changed dependency explicitly re-pinned.
  const repin = (store: Record<string, string>, pin: Binding, object: JsonObject) => {
    const bytes = JSON.stringify(object);
    store[pin.ref] = bytes;
    pin.byte_length = utf8.encode(bytes).length;
    pin.sha256 = sha256(utf8.encode(bytes));
  };
  for (const [field, value] of [
    ["row_profile", "unknown/v99"],
    ["encoding_profile", "unknown/v99"],
    ["kind", "unknown"],
    ["capabilities", []],
  ] as [string, unknown][]) {
    const evidence = fixture("vectors/bindings/baseline.json");
    evidence.metadata[field] = value;
    const standalone = independentOutcome("bindings", evidence) as { refusal?: string };
    if (standalone.refusal !== "graph_profile") {
      console.error(`[!!] binding metadata ${field}: got ${standalone.refusal ?? "accept"}`);
      failures++;
    }
    const g = fixture("vectors/graphs/baseline.json");
    const pub = readJsonFromText(g.store[g.publication.ref]);
    const manifest = readJsonFromText(g.store[pub.manifest.ref]);
    const metadata = readJsonFromText(g.store[manifest.profile_metadata.ref]);
    metadata[field] = value;
    repin(g.store, manifest.profile_metadata, metadata);
    repin(g.store, pub.manifest, manifest);
    repin(g.store, g.publication, pub);
    const result = independentOutcome("graphs", g) as { refusal?: string };
    if (result.refusal !== "graph_profile") {
      console.error(`[!!] graph metadata ${field}: got ${result.refusal ?? "accept"}`);
      failures++;
    }
  }
  // Each graph mutation is re-pinned through publication so the intended
  // semantic guard, rather than an integrity mismatch, decides the result.
  for (const change of [
    "manifest capability",
    "manifest kind",
    "profile spec id",
    "catalog withheld",
    "catalog extra",
    "inline catalog",
    "appendable",
  ]) {
    const g = fixture("vectors/graphs/baseline.json");
    const pub = readJsonFromText(g.store[g.publication.ref]);
    const manifest = readJsonFromText(g.store[pub.manifest.ref]);
    let reason = "graph_profile";
    if (change === "manifest capability")
      manifest.capabilities = ["contract: segmented-snapshot/v0"];
    else if (change === "manifest kind") manifest.kind = "wrong";
    else if (change === "profile spec id") {
      const profile = readJsonFromText(g.store[pub.profile.ref]);
      profile.semantic_spec.id = "wrong";
      repin(g.store, pub.profile, profile);
      manifest.profile = clone(pub.profile);
    } else if (change === "catalog withheld" || change === "catalog extra") {
      const catalog = readJsonFromText(g.store[manifest.field_catalog.ref]);
      if (change === "catalog withheld") {
        catalog.withheld_fields = ["secret"];
        catalog.withheld_field_count = 1;
      } else catalog.fields.push({ ...catalog.fields[0], name: "extra" });
      repin(g.store, manifest.field_catalog, catalog);
      reason = "graph_catalog";
    } else {
      const descriptor = readJsonFromText(g.store[pub.descriptor.ref]);
      if (change === "inline catalog") {
        const catalog = readJsonFromText(g.store[manifest.field_catalog.ref]);
        catalog.fields[0].type = "integer";
        descriptor.field_catalogs = [catalog];
        reason = "graph_catalog";
      } else {
        descriptor.representations[0].read_path.appendable = true;
        reason = "graph_descriptor";
      }
      repin(g.store, pub.descriptor, descriptor);
    }
    repin(g.store, pub.manifest, manifest);
    repin(g.store, g.publication, pub);
    const result = independentOutcome("graphs", g) as { refusal?: string };
    if (result.refusal !== reason) {
      console.error(`[!!] ${change}: got ${result.refusal ?? "accept"}`);
      failures++;
    }
  }
  const embeddedGraph = fixture("vectors/graphs/baseline.json");
  const embeddedPub = readJsonFromText(embeddedGraph.store[embeddedGraph.publication.ref]);
  const embeddedManifest = readJsonFromText(embeddedGraph.store[embeddedPub.manifest.ref]);
  const embeddedDescriptor = readJsonFromText(embeddedGraph.store[embeddedPub.descriptor.ref]);
  embeddedDescriptor.field_catalogs = [
    readJsonFromText(embeddedGraph.store[embeddedManifest.field_catalog.ref]),
  ];
  repin(embeddedGraph.store, embeddedPub.descriptor, embeddedDescriptor);
  repin(embeddedGraph.store, embeddedGraph.publication, embeddedPub);
  const embeddedResult = independentOutcome("graphs", embeddedGraph) as { evidence_scope?: string };
  if (embeddedResult.evidence_scope !== "logical_projection") {
    console.error("[!!] matching inline catalog control");
    failures++;
  }
  const superseded = fixture("vectors/bindings/baseline.json");
  const supersededPin = superseded.metadata.coverage[0];
  const supersededAttestation = readJsonFromText(superseded.store[supersededPin.ref]);
  supersededAttestation.supersedes = "previous";
  repin(superseded.store, supersededPin, supersededAttestation);
  const supersededResult = independentOutcome("bindings", superseded) as { refusal?: string };
  if (supersededResult.refusal !== "coverage_scope") {
    console.error("[!!] superseded coverage control");
    failures++;
  }
  const duplicated = fixture("vectors/bindings/baseline.json");
  duplicated.observations.push(clone(duplicated.observations[0]));
  const duplicatedResult = independentOutcome("bindings", duplicated) as { refusal?: string };
  if (duplicatedResult.refusal !== "duplicate_observation") {
    console.error("[!!] duplicate bound observation control");
    failures++;
  }
  const invalidActor = fixture("vectors/transitions/ack-retains-omitted-row.json");
  invalidActor.acknowledgment.acknowledged_by = "invalid actor";
  const invalidActorResult = evaluate(invalidActor) as { refusal?: string };
  if (invalidActorResult.refusal !== "acknowledgment_actor") {
    console.error("[!!] acknowledgment actor control");
    failures++;
  }
  const enrichAuthority = fixture("vectors/transitions/enrichment-only.json");
  enrichAuthority.absence_authority = clone(enrichAuthority.scopes);
  const enrichAuthorityResult = evaluate(enrichAuthority) as { refusal?: string };
  if (enrichAuthorityResult.refusal !== "enrichment_observation") {
    console.error("[!!] enrichment authority control");
    failures++;
  }

  const loss = fixture("vectors/transitions/ack-retains-omitted-row.json");
  const boundLoss = fixture("vectors/bound_transitions/observe.json");
  boundLoss.transition = clone(loss);
  const bm = boundLoss.evidence.metadata;
  const bp = readJsonFromText(boundLoss.evidence.store[bm.plan.ref]);
  bp.scopes = clone(loss.scopes);
  repin(boundLoss.evidence.store, bm.plan, bp);
  bm.plan_digest = loss.acknowledgment.plan_digest;
  bm.effective_scope_count = 1;
  bm.coverage = bm.coverage.slice(0, 1);
  bm.admission = "loss_acknowledged";
  bm.loss_acknowledgment = {
    parent: clone(bm.parent),
    plan_sha256: bm.plan_digest,
    acknowledged_by: loss.acknowledgment.acknowledged_by,
    acknowledged_at: loss.acknowledgment.acknowledged_at,
  };
  const expectedLoss = readJson(
    join(SCHEMAS, "vectors/transitions/ack-retains-omitted-row.json"),
  ).expected;
  if (!same(independentOutcome("bound_transitions", boundLoss), expectedLoss)) {
    console.error("[!!] bound loss acknowledgment control");
    failures++;
  }
  const badAck = clone(boundLoss);
  badAck.evidence.metadata.loss_acknowledgment.parent.selection.snapshot_id = "wrong-parent";
  const ackResult = independentOutcome("bound_transitions", badAck) as { refusal?: string };
  if (ackResult.refusal !== "acknowledgment_mismatch") {
    console.error("[!!] acknowledgment parent control");
    failures++;
  }

  const graphLoss = fixture("vectors/graphs/observe.json");
  const glPub = readJsonFromText(graphLoss.store[graphLoss.publication.ref]);
  const glManifest = readJsonFromText(graphLoss.store[glPub.manifest.ref]);
  const glMeta = readJsonFromText(graphLoss.store[glManifest.profile_metadata.ref]);
  const glPlan = readJsonFromText(graphLoss.store[glMeta.plan.ref]);
  glPlan.scopes = clone(loss.scopes);
  glMeta.plan.ref = "artifact:loss-control-plan";
  repin(graphLoss.store, glMeta.plan, glPlan);
  glMeta.plan_digest = loss.acknowledgment.plan_digest;
  glMeta.effective_scope_count = 1;
  glMeta.coverage = glMeta.coverage.slice(0, 1);
  glMeta.admission = "loss_acknowledged";
  glMeta.loss_acknowledgment = {
    parent: clone(glMeta.parent),
    plan_sha256: glMeta.plan_digest,
    acknowledged_by: loss.acknowledgment.acknowledged_by,
    acknowledged_at: loss.acknowledgment.acknowledged_at,
  };
  const beta = graphLoss.store["artifact:g0-member-1"];
  const betaPin = glManifest.members[1];
  graphLoss.store[betaPin.ref] = beta;
  betaPin.byte_length = utf8.encode(beta).length;
  betaPin.sha256 = sha256(utf8.encode(beta));
  repin(graphLoss.store, glManifest.profile_metadata, glMeta);
  repin(graphLoss.store, glPub.manifest, glManifest);
  repin(graphLoss.store, graphLoss.publication, glPub);
  const graphLossResult = independentOutcome("graphs", graphLoss) as JsonObject;
  if (!same(graphLossResult.rows, expectedLoss.rows)) {
    console.error("[!!] graph loss acknowledgment control");
    failures++;
  }

  const badRows: [string, unknown][] = [
    ["empty key", ""],
    ["invalid namespace", "bad namespace"],
    ["numeric storage class", 1],
    ["empty revision", {}],
    ["null first stamp", null],
    ["null enrichments", null],
  ];
  for (const [name, value] of badRows) {
    const input = fixture("vectors/rows/two-members.json");
    const field = (
      {
        "empty key": "key",
        "invalid namespace": "namespace",
        "numeric storage class": "storage_class",
        "empty revision": "revision",
        "null first stamp": "first_seen",
        "null enrichments": "enrichments",
      } as Record<string, string>
    )[name];
    input.members[0][0][field] = value;
    const result = independentOutcome("rows", input) as { refusal?: string };
    if (result.refusal !== "invalid_shape") {
      console.error(`[!!] ${name}: got ${result.refusal ?? "accept"}`);
      failures++;
    }
  }
  const partialGraph = fixture("vectors/graphs/baseline.json");
  const partialPub = readJsonFromText(partialGraph.store[partialGraph.publication.ref]);
  const partialDescriptor = readJsonFromText(partialGraph.store[partialPub.descriptor.ref]);
  partialDescriptor.lifecycle = "partial";
  repin(partialGraph.store, partialPub.descriptor, partialDescriptor);
  repin(partialGraph.store, partialGraph.publication, partialPub);
  const partialResult = independentOutcome("graphs", partialGraph) as JsonObject;
  const baselineExpected = readJson(join(SCHEMAS, "vectors/graphs/baseline.json")).expected;
  if (!same(partialResult, baselineExpected)) {
    console.error("[!!] partial descriptor control");
    failures++;
  }

  for (const change of [
    "profile streaming",
    "profile spec",
    "producer profile",
    "read path",
    "catalog type",
  ]) {
    const g = fixture("vectors/graphs/baseline.json");
    const pub = readJsonFromText(g.store[g.publication.ref]);
    const manifest = readJsonFromText(g.store[pub.manifest.ref]);
    let reason = "graph_profile";
    if (change === "profile streaming" || change === "profile spec") {
      const profile = readJsonFromText(g.store[pub.profile.ref]);
      if (change === "profile streaming") profile.streaming = "supported";
      else {
        const spec = profile.semantic_spec;
        g.store[spec.ref] += "changed";
        spec.byte_length = utf8.encode(g.store[spec.ref]).length;
        spec.sha256 = sha256(utf8.encode(g.store[spec.ref]));
      }
      repin(g.store, pub.profile, profile);
      manifest.profile = clone(pub.profile);
      repin(g.store, pub.manifest, manifest);
    } else if (change === "catalog type") {
      const catalog = readJsonFromText(g.store[manifest.field_catalog.ref]);
      catalog.fields[0].type = "integer";
      repin(g.store, manifest.field_catalog, catalog);
      repin(g.store, pub.manifest, manifest);
      reason = "graph_catalog";
    } else {
      const descriptor = readJsonFromText(g.store[pub.descriptor.ref]);
      if (change === "producer profile") descriptor.producer.profile = "unknown";
      else descriptor.representations[0].read_path.physical_ordering = "unknown";
      repin(g.store, pub.descriptor, descriptor);
      reason = "graph_descriptor";
    }
    repin(g.store, g.publication, pub);
    const got = independentOutcome("graphs", g) as { refusal?: string };
    if (got.refusal !== reason) {
      console.error(`[!!] ${change}: got ${got.refusal ?? "accept"}`);
      failures++;
    }
  }

  const repeated = fixture("vectors/graphs/observe.json");
  const currentPub = readJsonFromText(repeated.store[repeated.publication.ref]);
  const currentManifest = readJsonFromText(repeated.store[currentPub.manifest.ref]);
  const currentMeta = readJsonFromText(repeated.store[currentManifest.profile_metadata.ref]);
  const olderPub = readJsonFromText(repeated.store[currentMeta.parent.publication.ref]);
  olderPub.selection.snapshot_id = currentPub.selection.snapshot_id;
  repin(repeated.store, currentMeta.parent.publication, olderPub);
  repin(repeated.store, currentManifest.profile_metadata, currentMeta);
  repin(repeated.store, currentPub.manifest, currentManifest);
  repin(repeated.store, repeated.publication, currentPub);
  const repeatedResult = independentOutcome("graphs", repeated) as { refusal?: string };
  if (repeatedResult.refusal !== "parent_cycle") {
    console.error("[!!] repeated snapshot ancestry control");
    failures++;
  }

  // JSON permits finite fractions, including values rounded by binary64. The
  // integer predicate must instead use the exact token, even after cloning.
  const source = fixture("vectors/rows/two-members.json").members[0][0];
  const encoded = JSON.stringify(source);
  for (const [literal, integral] of [
    ["1.0000000000000001", false],
    ["9007199254740990.5", false],
    ["1e-400", false],
    ["100e-2", true],
    ["1.000e0", true],
    ["0e-400", true],
    ["9007199254740991", true],
  ] as [string, boolean][]) {
    const raw = encoded.replace('"size_bytes":12', `"size_bytes":${literal}`);
    const row = clone(strictJSON(utf8.encode(raw))) as Row;
    let accepted = true;
    try {
      checkSource(row);
    } catch (e) {
      if (e instanceof Refusal && e.reason === "invalid_shape") accepted = false;
      else throw e;
    }
    if (accepted !== integral) {
      console.error(`[!!] numeric integer control ${literal}: got ${accepted}`);
      failures++;
    }
    // The same token is always legal JSON independently of the integer field.
    strictJSON(utf8.encode(literal));
  }
  const decimalVolume = fixture("vectors/bindings/baseline.json");
  const coveragePin = decimalVolume.metadata.coverage[0];
  const alteredCoverage = decimalVolume.store[coveragePin.ref].replace(
    '"observed": 1',
    '"observed": 1.0000000000000001',
  );
  decimalVolume.store[coveragePin.ref] = alteredCoverage;
  coveragePin.byte_length = utf8.encode(alteredCoverage).length;
  coveragePin.sha256 = sha256(utf8.encode(alteredCoverage));
  const volumeResult = independentOutcome("bindings", decimalVolume) as { refusal?: string };
  if (volumeResult.refusal !== "coverage_volume") {
    console.error(`[!!] numeric coverage control: got ${volumeResult.refusal ?? "accept"}`);
    failures++;
  }
  const decimalTransition = strictJSON(utf8.encode('{"generation":0.00000000000000000001}'));
  const transitionInput = overlay(
    fixture("vectors/transitions/empty-baseline.json"),
    decimalTransition,
  );
  const transitionResult = evaluate(transitionInput) as { refusal?: string };
  if (transitionResult.refusal !== "invalid_shape") {
    console.error(`[!!] numeric generation control: got ${transitionResult.refusal ?? "accept"}`);
    failures++;
  }
  console.log(`  mutation witnesses: ${witnesses.length}; numeric controls: 9`);
  const listed = [...cases.plans, ...cases.transitions, ...cases.scenarios];
  for (const fault of inventoryFaults(listed, executed)) {
    console.error(`[!!] logical inventory: ${fault}`);
    failures++;
  }
  // A supported transitions runner at a new location must not be silently
  // skipped merely because the directory scanners did not dispatch it.
  const hypothetical = "control/new-transition-case.json";
  const omitted = inventoryFaults([...listed, hypothetical], executed);
  if (!omitted.includes(`executed 0 times: ${hypothetical}`)) {
    console.error("[!!] inventory did not detect an unexecuted scenario");
    failures++;
  }
  const repeatedExecutions = new Map(executed);
  repeatedExecutions.set(hypothetical, 2);
  if (
    !inventoryFaults([...listed, hypothetical], repeatedExecutions).includes(
      `executed 2 times: ${hypothetical}`,
    )
  ) {
    console.error("[!!] inventory did not detect a duplicate execution");
    failures++;
  }
  // Every scenario must select a supported runner, and plan/transition files must
  // be listed. This prevents a newly accepted fixture from silently going unused.
  const supported = new Set([
    "transitions",
    "rows",
    "parsing",
    "bindings",
    "cutover",
    "bound_transitions",
    "graphs",
    "cutover_graphs",
  ]);
  for (const path of cases.scenarios) {
    const c = readJson(join(SCHEMAS, path));
    if (!supported.has(c.runner)) {
      console.error(`[!!] unsupported scenario runner: ${path}`);
      failures++;
    }
  }
  const scenarioSet = new Set(cases.scenarios);
  for (const dir of readdirSync(join(SCHEMAS, "rejects/semantic"))) {
    const path = `rejects/semantic/${dir}/case.json`;
    if (!scenarioSet.has(path)) {
      console.error(`[!!] unlisted semantic case: ${path}`);
      failures++;
    }
  }
  for (const kind of ["bindings", "rows", "parsing", "cutover", "bound_transitions", "graphs"]) {
    for (const file of json(join(VECTORS, kind))) {
      const path = `vectors/${kind}/${file}`;
      if (!scenarioSet.has(path)) {
        console.error(`[!!] unlisted scenario: ${path}`);
        failures++;
      }
    }
  }
  for (const kind of ["plans", "transitions"]) {
    const listed = new Set(
      [...cases[kind], ...cases.scenarios].filter((p: string) => p.startsWith(`vectors/${kind}/`)),
    );
    for (const file of json(join(VECTORS, kind))) {
      if (!listed.has(`vectors/${kind}/${file}`)) {
        console.error(`[!!] unlisted ${kind} fixture: ${file}`);
        failures++;
      }
    }
    for (const path of listed) {
      if (!json(join(VECTORS, kind)).includes(path.split("/").pop())) {
        console.error(`[!!] missing ${kind} fixture: ${path}`);
        failures++;
      }
    }
  }
  for (const entry of Object.keys(KNOWN_DISAGREEMENTS)) {
    if (!usedDisagreements.has(entry)) {
      console.error(`[!!] known disagreement matches no current fixture: ${entry}`);
      failures++;
    }
  }
  return failures === 0 ? 0 : 1;
}

process.exitCode = main();
