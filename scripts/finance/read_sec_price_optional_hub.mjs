// Finance SEC M8: optional M7 loopback hub, direct EODHD fallback only when
// the local hub is absent. Nothing runs until PRICE CONTEXT invokes this CLI.
// Do not retry upstream or bypass an active hub reporting provider failures.
import { pathToFileURL } from "node:url";
import { loadPrices, SYMBOLS } from "./read_sec_price_context.mjs";

const LOCAL_HOST = "127.0.0.1";
const DEFAULT_PORT = 48731;
const MAX_BYTES = 128000;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const PROVIDER_ERRORS = new Set([
  "invalid-selection", "unknown-provider", "provider-busy",
  "provider-key-required", "demo-not-authorized", "provider-unavailable",
  "provider-response-too-large", "provider-invalid", "invalid-price-data",
  "invalid-provider-snapshot", "token-unreadable", "token-permissions",
  "token-invalid", "provider-failed"
]);

function failure(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}
function validDay(value) {
  if (typeof value !== "string" || !DAY.test(value)) return false;
  const date = Date.parse(value + "T00:00:00.000Z");
  return Number.isFinite(date) && new Date(date).toISOString().slice(0,10) === value;
}
export function validPort(value) {
  return Number.isInteger(value) && value >= 1024 && value <= 65535;
}
export function connectionRefused(error) {
  // Only an absent loopback listener allows transparent direct fallback.
  // A reachable but slow, invalid or unauthorized service is not "absent".
  return error?.cause?.code === "ECONNREFUSED"
    || error?.code === "ECONNREFUSED";
}
async function readJson(response) {
  const length = Number(response.headers?.get?.("content-length"));
  if (Number.isFinite(length) && length > MAX_BYTES)
    throw failure("hub-invalid-response");
  let body;
  try { body = await response.text(); }
  catch { throw failure("hub-unhealthy"); }
  if (body.length > MAX_BYTES) throw failure("hub-invalid-response");
  try { return JSON.parse(body); }
  catch { throw failure("hub-invalid-response"); }
}
function validatePrice(snapshot, cik, filingDate) {
  if (!snapshot || snapshot.schemaVersion !== 1 || snapshot.readOnly !== true
      || snapshot.source !== "eodhd-eod"
      || snapshot.cik !== cik || snapshot.symbol !== SYMBOLS[cik]
      || snapshot.filingDate !== filingDate
      || !validDay(snapshot.filingDate)
      || !["CLOSE","ADJUSTED CLOSE"].includes(snapshot.priceBasis)
      || !Array.isArray(snapshot.bars) || snapshot.bars.length > 32
      || snapshot.bars.length === 0 || typeof snapshot.retrievedAt !== "string"
      || !Number.isFinite(Date.parse(snapshot.retrievedAt))
      || (snapshot.changePct !== null && (!Number.isFinite(snapshot.changePct)
          || Math.abs(snapshot.changePct) > 1e7)))
    throw failure("hub-invalid-response");
  let last = "";
  for (const bar of snapshot.bars) {
    if (!bar || !validDay(bar.date) || bar.date <= last
        || !Number.isFinite(bar.price) || bar.price <= 0)
      throw failure("hub-invalid-response");
    last = bar.date;
  }
  for (const pair of [snapshot.previous,snapshot.filingDay,snapshot.next]) {
    if (pair === null) continue;
    if (!pair || !validDay(pair.date) || !Number.isFinite(pair.price)
        || pair.price <= 0
        || !snapshot.bars.some(b => b.date === pair.date && b.price === pair.price))
      throw failure("hub-invalid-response");
  }
  if (snapshot.previous && snapshot.previous.date >= filingDate
      || snapshot.next && snapshot.next.date <= filingDate
      || snapshot.filingDay && snapshot.filingDay.date !== filingDate)
    throw failure("hub-invalid-response");
  return snapshot;
}
function verifyHubData(data) {
  const x = data?.hub;
  if (!x || x.provider !== "eodhd"
      || !["FETCHED","CACHED","SHARED"].includes(x.state)
      || !Number.isFinite(Date.parse(x.cachedAt))
      || !Number.isFinite(Date.parse(x.expiresAt))
      || !Number.isFinite(Date.parse(x.servedAt))
      || !Number.isSafeInteger(x.ageSeconds) || x.ageSeconds < 0
      || Date.parse(x.expiresAt) <= Date.parse(x.cachedAt))
    throw failure("hub-invalid-response");
  return {
    via:"HUB", state:x.state, servedAt:x.servedAt,
    cachedAt:x.cachedAt, expiresAt:x.expiresAt,
    ageSeconds:x.ageSeconds
  };
}

/** One explicit request. Inject fetcher/directReader in fake-only tests. */
export async function readOptionalPrice(cik, filingDate, {
  fetcher = fetch, directReader = loadPrices, port = DEFAULT_PORT,
  now = () => new Date().toISOString()
} = {}) {
  const today = now().slice(0,10);
  if (!Object.hasOwn(SYMBOLS,cik) || !validDay(filingDate)
      || !validDay(today) || filingDate < "2000-01-01"
      || filingDate > today || !validPort(port))
    throw failure("invalid-selection");
  const base = "http://" + LOCAL_HOST + ":" + port;
  // Avoid stale pooled sockets after the operator manually stops the hub.
  // A new health probe then yields ECONNREFUSED, the sole direct-fallback gate.
  const headers = {"X-Post-Apollo-Client":"financew",
    "Accept":"application/json", "Connection":"close"};
  let health;
  try {
    const res = await fetcher(base + "/v1/health", {
      method:"GET", redirect:"error", headers, signal:AbortSignal.timeout(900)
    });
    if (!res.ok) throw failure("hub-unhealthy");
    health = await readJson(res);
  } catch (error) {
    if (!connectionRefused(error)) {
      throw failure(error?.code === "hub-invalid-response"
        ? "hub-invalid-response" : "hub-unhealthy");
    }
    const direct = validatePrice(await directReader(cik,filingDate),cik,filingDate);
    return {
      ...direct,delivery:{via:"DIRECT",state:"DIRECT",
        servedAt:now(),cachedAt:null,expiresAt:null,ageSeconds:null}
    };
  }
  if (!health || health.schemaVersion !== 1
      || health.service !== "post-apollo-market-hub"
      || health.readOnly !== true || health.backgroundPolling !== false
      || !Array.isArray(health.providerIds) || !health.providerIds.includes("eodhd"))
    throw failure("hub-unhealthy");
  const url = base + "/v1/price-context?cik=" + cik + "&date=" + filingDate;
  let response;
  try {
    response = await fetcher(url,{
      method:"GET",redirect:"error",headers,signal:AbortSignal.timeout(14000)
    });
  } catch {
    throw failure("hub-unhealthy"); // Never cause a second upstream request.
  }
  const body = await readJson(response);
  if (!response.ok) {
    const code = body?.error;
    throw failure(PROVIDER_ERRORS.has(code) ? code : "hub-unhealthy");
  }
  const data = validatePrice(body,cik,filingDate);
  return {...data,delivery:verifyHubData(data)};
}

// Preserve the legacy stdout protocol consumed by Quickshell.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const rawPort = process.env.POST_APOLLO_MARKET_HUB_PORT;
    const port = rawPort === undefined ? DEFAULT_PORT : Number(rawPort);
    const result = await readOptionalPrice(process.argv[2],process.argv[3],{port});
    process.stdout.write("FINANCE_SEC_PRICE " + JSON.stringify(result) + "\n");
  } catch (error) {
    const code = PROVIDER_ERRORS.has(error?.code || error?.message)
      ? (error.code || error.message)
      : ["hub-unhealthy","hub-invalid-response","invalid-selection"].includes(error?.code)
      ? error.code : "provider-failed";
    process.stdout.write("FINANCE_SEC_PRICE_ERROR " + code + "\n");
    process.exitCode = 1;
  }
}
