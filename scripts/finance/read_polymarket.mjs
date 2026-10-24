// FinanceW Market M1: bounded, read-only public Polymarket market snapshot.
// One Gamma GET per manual/on-entry refresh. No trading or account endpoints.
import { pathToFileURL } from "node:url";

const API = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=80";
const MAX_MARKETS = 24;

function finite(value, max = 1e15) {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" || typeof value === "string" ? Number(value) : NaN;
  return Number.isFinite(n) && n >= 0 && n <= max ? n : null;
}

function stringArray(value) {
  let parsed = value;
  if (typeof parsed === "string") {
    try { parsed = JSON.parse(parsed); } catch { return []; }
  }
  return Array.isArray(parsed) && parsed.length <= 20 ? parsed : [];
}

export function normalizeMarket(raw) {
  if (!raw || typeof raw !== "object" || raw.active !== true || raw.closed === true) return null;
  const labels = stringArray(raw.outcomes);
  const prices = stringArray(raw.outcomePrices);
  if (labels.length !== prices.length || labels.length !== 2) return null;
  const yes = labels.findIndex(x => typeof x === "string" && x.toLowerCase() === "yes");
  const no = labels.findIndex(x => typeof x === "string" && x.toLowerCase() === "no");
  if (yes === -1 || no === -1) return null;
  const yesPrice = finite(prices[yes], 1), noPrice = finite(prices[no], 1);
  if (yesPrice === null || noPrice === null) return null;
  const id = typeof raw.id === "string" || typeof raw.id === "number" ? String(raw.id) : "";
  const question = typeof raw.question === "string" ? raw.question.trim().slice(0, 180) : "";
  if (!/^[0-9]{1,24}$/.test(id) || !question) return null;
  const vol = finite(raw.volume24hr) ?? finite(raw.volume24hrClob);
  const liquidity = finite(raw.liquidityNum) ?? finite(raw.liquidity);
  const change = raw.oneDayPriceChange == null ? NaN : Number(raw.oneDayPriceChange);
  return {
    id,
    question,
    yesPct: Math.round(yesPrice * 1000) / 10,
    noPct: Math.round(noPrice * 1000) / 10,
    volume24h: vol === null ? null : Math.round(vol),
    liquidity: liquidity === null ? null : Math.round(liquidity),
    change24hPct: Number.isFinite(change) && Math.abs(change) <= 1
      ? Math.round(change * 1000) / 10 : null
  };
}

export function normalizePayload(payload, timestamp) {
  if (!Array.isArray(payload) || payload.length > 1000) throw new Error("invalid-feed");
  const seen = new Set();
  const markets = [];
  for (const item of payload) {
    const m = normalizeMarket(item);
    if (m && !seen.has(m.id)) {
      seen.add(m.id);
      markets.push(m);
    }
  }
  markets.sort((a,b) => (b.volume24h ?? -1) - (a.volume24h ?? -1));
  return {
    schemaVersion: 1,
    source: "polymarket-gamma",
    readOnly: true,
    retrievedAt: timestamp,
    markets: markets.slice(0, MAX_MARKETS),
    sampleSize: payload.length
  };
}

export async function loadMarkets(fetcher = fetch) {
  const response = await fetcher(API, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(10000)
  });
  if (!response.ok) throw new Error("upstream-unavailable");
  return normalizePayload(await response.json(), new Date().toISOString());
}

// Importing this file for deterministic fixture tests never makes a network request.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const result = await loadMarkets();
    process.stdout.write("FINANCE_MARKET_SNAPSHOT " + JSON.stringify(result) + "\n");
  } catch {
    process.stdout.write("FINANCE_MARKET_ERROR public-feed-unavailable\n");
    process.exitCode = 1;
  }
}
