// FinanceW Research M1: pure, read-only-friendly investigation model.
// No network requests, financial actions, or filesystem writes.
// Callers may persist validated JSON only behind a separately reviewed store.
export const SCHEMA_VERSION = 1;
const MAX_INVESTIGATIONS = 50;
const MAX_EVIDENCE = 40;
const MAX_TEXT = 2000;
const SOURCES = new Set(["sec-edgar-submissions", "finance-demo-scrapy", "manual"]);
const isObject = x => x !== null && typeof x === "object" && !Array.isArray(x);
const validText = (x, max = MAX_TEXT) => typeof x === "string" && x.length > 0 && x.length <= max && x.trim() === x;
const validDate = x => typeof x === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(x) && Number.isFinite(Date.parse(x));
const validId = x => typeof x === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(x);
function validUrl(x, source) {
  if (typeof x !== "string" || x.length > 1000) return false;
  try {
    const u = new URL(x);
    if (u.protocol !== "https:" || u.username || u.password || u.hash) return false;
    if (source === "sec-edgar-submissions") return u.hostname === "www.sec.gov" && u.pathname.startsWith("/Archives/edgar/data/");
    if (source === "finance-demo-scrapy") return u.hostname === "quotes.toscrape.com";
    return true;
  } catch { return false; }
}
export function validEvidence(item) {
  return isObject(item) && validId(item.id) && SOURCES.has(item.source)
    && validText(item.title, 160) && validText(item.summary)
    && validUrl(item.url, item.source) && validDate(item.observedAt)
    && (item.source !== "manual" || item.reviewed === false || item.reviewed === true)
    && Object.keys(item).every(k => ["id","source","title","summary","url","observedAt","reviewed"].includes(k));
}
export function validInvestigation(item) {
  return isObject(item) && item.schemaVersion === SCHEMA_VERSION && validId(item.id)
    && validText(item.title, 160) && validText(item.question, 1000)
    && validDate(item.createdAt) && validDate(item.updatedAt)
    && Array.isArray(item.evidence) && item.evidence.length <= MAX_EVIDENCE
    && item.evidence.every(validEvidence)
    && new Set(item.evidence.map(e => e.id)).size === item.evidence.length
    && Object.keys(item).every(k => ["schemaVersion","id","title","question","createdAt","updatedAt","evidence"].includes(k));
}
export function validateCollection(items) {
  return Array.isArray(items) && items.length <= MAX_INVESTIGATIONS
    && items.every(validInvestigation)
    && new Set(items.map(x => x.id)).size === items.length;
}
function assertCollection(items) {
  if (!validateCollection(items)) throw new TypeError("invalid research collection");
}
function assertTimestamp(timestamp) {
  if (!validDate(timestamp)) throw new TypeError("invalid UTC timestamp");
}
export function createInvestigation(items, {id, title, question, timestamp}) {
  assertCollection(items);
  assertTimestamp(timestamp);
  const item = {schemaVersion: SCHEMA_VERSION, id, title, question,
    createdAt: timestamp, updatedAt: timestamp, evidence: []};
  if (!validInvestigation(item) || items.length >= MAX_INVESTIGATIONS || items.some(x => x.id === id))
    throw new TypeError("invalid or duplicate investigation");
  return [...items, item];
}
export function attachEvidence(items, investigationId, evidence, timestamp) {
  assertCollection(items);
  assertTimestamp(timestamp);
  if (!validEvidence(evidence)) throw new TypeError("invalid evidence");
  const index = items.findIndex(x => x.id === investigationId);
  if (index < 0) throw new RangeError("investigation not found");
  const item = items[index];
  if (item.evidence.length >= MAX_EVIDENCE || item.evidence.some(x => x.id === evidence.id))
    throw new TypeError("duplicate evidence or evidence limit");
  const next = [...items];
  next[index] = {...item, updatedAt: timestamp, evidence: [...item.evidence, {...evidence}]};
  return next;
}
export function removeEvidence(items, investigationId, evidenceId, timestamp) {
  assertCollection(items);
  assertTimestamp(timestamp);
  const index = items.findIndex(x => x.id === investigationId);
  if (index < 0) throw new RangeError("investigation not found");
  const item = items[index];
  if (!item.evidence.some(e => e.id === evidenceId)) throw new RangeError("evidence not found");
  const next = [...items];
  next[index] = {...item, updatedAt: timestamp, evidence: item.evidence.filter(e => e.id !== evidenceId)};
  return next;
}
export function parseCollection(json) {
  if (typeof json !== "string" || json.length > 500000) throw new TypeError("invalid research JSON");
  const items = JSON.parse(json);
  assertCollection(items);
  return items;
}
