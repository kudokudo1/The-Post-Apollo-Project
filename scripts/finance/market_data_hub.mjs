// FinanceW M7: in-memory read-through hub for approved historical market feeds.
// Provider-neutral contract; EODHD is the ONLY wired provider in this milestone.
// Nothing is fetched at module import, no disk writes and no background polling.
import { loadPrices, SYMBOLS } from "./read_sec_price_context.mjs";

const DEFAULT_TTL_RECENT_MS = 15 * 60 * 1000;
const DEFAULT_TTL_HISTORICAL_MS = 24 * 60 * 60 * 1000;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const MAX_SLOTS = 64;
const MAX_CONCURRENT = 2;

function validDate(value) {
  if (typeof value !== "string" || !DAY.test(value)) return false;
  const millis = Date.parse(value + "T00:00:00.000Z");
  return Number.isFinite(millis) && new Date(millis).toISOString().slice(0, 10) === value;
}
function fail(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}
function sanitizeError(error) {
  const known = [
    "invalid-selection", "unknown-provider", "provider-busy",
    "provider-key-required", "demo-not-authorized", "provider-unavailable",
    "provider-response-too-large", "provider-invalid", "invalid-price-data",
    "token-unreadable", "token-permissions", "token-invalid",
    "provider-failed", "invalid-provider-snapshot"
  ];
  return fail(known.includes(error?.code || error?.message)
    ? (error.code || error.message) : "provider-failed");
}
function clone(value) {
  // Never return references to cached objects that callers can mutate.
  return JSON.parse(JSON.stringify(value));
}
function ensureSnapshot(result, cik, filingDate) {
  if (!result || result.schemaVersion !== 1 || result.readOnly !== true
      || result.cik !== cik || result.filingDate !== filingDate
      || result.source !== "eodhd-eod" || result.symbol !== SYMBOLS[cik]
      || !["CLOSE","ADJUSTED CLOSE"].includes(result.priceBasis)
      || !Array.isArray(result.bars) || result.bars.length > 32
      || !result.bars.every(p => p && validDate(p.date)
        && Number.isFinite(p.price) && p.price > 0)
      || (result.changePct !== null && !Number.isFinite(result.changePct)))
    throw fail("invalid-provider-snapshot");
  for (const pair of [result.previous, result.filingDay, result.next]) {
    if (pair === null) continue;
    if (!pair || !validDate(pair.date)
        || !Number.isFinite(pair.price) || pair.price <= 0)
      throw fail("invalid-provider-snapshot");
  }
  if (result.previous && result.previous.date >= filingDate
      || result.next && result.next.date <= filingDate
      || result.filingDay && result.filingDay.date !== filingDate)
    throw fail("invalid-provider-snapshot");
  return clone(result);
}

/**
 * Adapter contract: async (cik, filingDate) => validated normalized snapshot.
 * Future provider additions require explicit source/license review, not a
 * caller-provided URL. Adapters run ONLY on explicit getPriceContext calls.
 */
export function createMarketDataHub({
  adapters = { eodhd: (cik, filingDate) => loadPrices(cik, filingDate) },
  now = () => Date.now(),
  maxEntries = MAX_SLOTS,
  maxConcurrent = MAX_CONCURRENT
} = {}) {
  if (!adapters || typeof adapters.eodhd !== "function"
      || Object.keys(adapters).some(key => key !== "eodhd")
      || !Number.isInteger(maxEntries) || maxEntries < 1 || maxEntries > MAX_SLOTS
      || !Number.isInteger(maxConcurrent) || maxConcurrent < 1
      || maxConcurrent > MAX_CONCURRENT)
    throw fail("invalid-selection");
  const cache = new Map();
  const inFlight = new Map();

  const health = () => ({
    schemaVersion: 1, service: "post-apollo-market-hub", readOnly: true,
    providerIds: ["eodhd"], cacheEntries: cache.size,
    inFlight: inFlight.size, backgroundPolling: false,
    scope: "local pilot; not a licensed multi-user distribution service"
  });

  async function getPriceContext({cik, filingDate, provider = "eodhd"} = {}) {
    if (provider !== "eodhd") throw fail("unknown-provider");
    const today = new Date(now()).toISOString().slice(0, 10);
    if (!Object.hasOwn(SYMBOLS, cik) || !validDate(filingDate)
        || filingDate < "2000-01-01" || filingDate > today)
      throw fail("invalid-selection");
    const key = provider + "|" + cik + "|" + filingDate;
    const stamp = now();
    const saved = cache.get(key);
    if (saved && saved.expiresAt > stamp) {
      // Touch LRU order.
      cache.delete(key);
      cache.set(key, saved);
      return {
        ...clone(saved.snapshot),
        hub: {provider, state:"CACHED", cachedAt:saved.cachedAt,
          expiresAt:new Date(saved.expiresAt).toISOString(),
          servedAt:new Date(stamp).toISOString(),
          ageSeconds:Math.floor((stamp - Date.parse(saved.cachedAt))/1000)}
      };
    }
    cache.delete(key);
    if (inFlight.has(key)) {
      await inFlight.get(key);
      // Exactly one real provider call; the second caller reads its result.
      const shared = cache.get(key);
      if (!shared) throw fail("provider-failed");
      return {
        ...clone(shared.snapshot),
        hub: {provider, state:"SHARED", cachedAt:shared.cachedAt,
          expiresAt:new Date(shared.expiresAt).toISOString(),
          servedAt:new Date(now()).toISOString(), ageSeconds:0}
      };
    }
    if (inFlight.size >= maxConcurrent) throw fail("provider-busy");
    const task = (async () => {
      let normalized;
      try {
        normalized = ensureSnapshot(await adapters[provider](cik, filingDate), cik, filingDate);
      } catch (error) {
        throw sanitizeError(error);
      }
      const captured = now();
      const ageMs = captured - Date.parse(filingDate + "T00:00:00.000Z");
      const ttl = ageMs < 7 * 86400000 ? DEFAULT_TTL_RECENT_MS : DEFAULT_TTL_HISTORICAL_MS;
      const entry = {
        snapshot: normalized,
        cachedAt: new Date(captured).toISOString(), expiresAt: captured + ttl
      };
      cache.set(key, entry);
      while (cache.size > maxEntries) cache.delete(cache.keys().next().value);
      return entry;
    })();
    inFlight.set(key, task);
    try {
      const entry = await task;
      return {
        ...clone(entry.snapshot),
        hub: {provider, state:"FETCHED", cachedAt:entry.cachedAt,
          expiresAt:new Date(entry.expiresAt).toISOString(),
          servedAt:new Date(now()).toISOString(), ageSeconds:0}
      };
    } finally {
      inFlight.delete(key);
    }
  }

  return {getPriceContext, health};
}
