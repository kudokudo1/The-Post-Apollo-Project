// FinanceW SEC M5: bounded end-of-day market context, not a price signal.
// EODHD demo confirmed locally for AAPL.US; documented MSFT support varies.
// MSFT demo is opt-in as a live capability probe, never marked guaranteed.
// NVIDIA remains gated behind an optional private provider token.
import { homedir } from "node:os";
import { join } from "node:path";
import { lstat, readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

export const SYMBOLS = Object.freeze({
  "0000320193": "AAPL.US",
  "0000789019": "MSFT.US",
  "0001045810": "NVDA.US",
});
export const TOKEN_FILE = join(homedir(), ".local", "share", "post-apollo",
  "finance-market", "eodhd-token.txt");
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const MAX_RESPONSE = 128000;
const MAX_BARS = 32;

function validDate(day) {
  if (typeof day !== "string" || !DAY.test(day)) return false;
  const stamp = Date.parse(day + "T00:00:00.000Z");
  return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0, 10) === day;
}
function shift(day, days) {
  return new Date(Date.parse(day + "T00:00:00.000Z") + days * 86400000)
    .toISOString().slice(0,10);
}
function value(v) {
  if (typeof v !== "number" && typeof v !== "string") return null;
  if (v === "" || v === null) return null;
  const n = Number(v);
  return Number.isFinite(n) && n > 0 && n < 1e7 ? n : null;
}
export async function loadOptionalToken(file = TOKEN_FILE) {
  let info;
  try { info = await lstat(file); }
  catch (error) {
    if (error?.code === "ENOENT") return null;
    throw new Error("token-unreadable");
  }
  if (!info.isFile() || info.isSymbolicLink() || (info.mode & 0o077) !== 0
      || info.size < 5 || info.size > 180) throw new Error("token-permissions");
  const token = (await readFile(file, "utf8")).trim();
  if (!/^[A-Za-z0-9_-]{5,160}$/.test(token)) throw new Error("token-invalid");
  return token;
}
export function normalizePrices(raw, cik, date, retrievedAt) {
  if (!SYMBOLS[cik] || !validDate(date) || !Array.isArray(raw)
      || raw.length > 250 || raw.length === 0)
    throw new Error("invalid-price-data");
  const min = shift(date,-10),max=shift(date,14);
  const seen=new Set(), bars=[];
  for (const row of raw) {
    if (!row || !validDate(row.date) || row.date < min || row.date > max
        || seen.has(row.date)) throw new Error("invalid-price-data");
    seen.add(row.date);
    const close=value(row.close),adjusted=value(row.adjusted_close);
    if (close===null) throw new Error("invalid-price-data");
    bars.push({date:row.date,close,adjustedClose:adjusted});
  }
  bars.sort((a,b)=>a.date.localeCompare(b.date));
  if (bars.length > MAX_BARS) throw new Error("invalid-price-data");
  // Compare one consistent basis, never mix adjusted and raw prices.
  const useAdjusted = bars.every(b=>b.adjustedClose !== null);
  const series = bars.map(b=>({date:b.date,price:useAdjusted?b.adjustedClose:b.close}));
  const previous=series.filter(b=>b.date<date).at(-1)??null;
  const filingDay=series.find(b=>b.date===date)??null;
  const next=series.find(b=>b.date>date)??null;
  const changePct=previous&&next
    ? Math.round((next.price/previous.price-1)*10000)/100 : null;
  return {
    schemaVersion:1,source:"eodhd-eod",readOnly:true,symbol:SYMBOLS[cik],cik,
    filingDate:date,retrievedAt,priceBasis:useAdjusted?"ADJUSTED CLOSE":"CLOSE",
    previous,filingDay,next,changePct,
    bars:series,
    scope:"Two daily closing prices around SEC filing date, not an event-effect study"
  };
}
export async function loadPrices(cik, filingDate, fetcher=fetch,
    tokenLoader=loadOptionalToken, today=new Date().toISOString().slice(0,10)) {
  if (!SYMBOLS[cik] || !validDate(filingDate) || !validDate(today)
      || filingDate > today || filingDate < "2000-01-01") throw new Error("invalid-selection");
  const token = await tokenLoader();
  const demoTrial = !token && cik === "0000789019";
  if (!token && cik !== "0000320193" && !demoTrial)
    throw new Error("provider-key-required");
  const from=shift(filingDate,-10);
  const end=shift(filingDate,14);
  const to=end>today?today:end;
  const params=new URLSearchParams({api_token:token||"demo",fmt:"json",from,to,period:"d",order:"a"});
  const response=await fetcher("https://eodhd.com/api/eod/"+SYMBOLS[cik]+"?"+params, {
    method:"GET",redirect:"error",headers:{Accept:"application/json"},
    signal:AbortSignal.timeout(12000)
  });
  if (!response.ok) {
    if (demoTrial && (response.status === 401 || response.status === 403))
      throw new Error("demo-not-authorized");
    throw new Error("provider-unavailable");
  }
  const len=Number(response.headers?.get?.("content-length"));
  if (Number.isFinite(len) && len>MAX_RESPONSE) throw new Error("provider-response-too-large");
  const body=await response.text();
  if (body.length>MAX_RESPONSE) throw new Error("provider-response-too-large");
  if (demoTrial && /^(?:unauthenticated|unauthorized|forbidden|access denied)\s*$/i.test(body.trim()))
    throw new Error("demo-not-authorized");
  let parsed;
  try {parsed=JSON.parse(body);}catch{throw new Error("provider-invalid");}
  return normalizePrices(parsed,cik,filingDate,new Date().toISOString());
}

if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const x=await loadPrices(process.argv[2],process.argv[3]);
    process.stdout.write("FINANCE_SEC_PRICE "+JSON.stringify(x)+"\n");
  } catch(error) {
    const allowed=["invalid-selection","provider-key-required","provider-unavailable",
      "provider-response-too-large","provider-invalid","invalid-price-data",
      "token-unreadable","token-permissions","token-invalid","demo-not-authorized"];
    const code=allowed.includes(error?.message)?error.message:"provider-failed";
    process.stdout.write("FINANCE_SEC_PRICE_ERROR "+code+"\n");
    process.exitCode=1;
  }
}
