// Finance M10: bounded date-range daily closing prices for Market STOCKS.
// One EODHD request per explicit read, no writes, no background polling.
import {pathToFileURL} from "node:url";
import {SYMBOLS, loadOptionalToken} from "./read_sec_price_context.mjs";

export const MAX_RANGE_DAYS = 180;
export const MAX_RANGE_BARS = 132;
const MAX_BODY = 192000;
const DAY_MS = 86400000;
const DAY = /^\d{4}-\d{2}-\d{2}$/;
export function dayNumber(value) {
  if (typeof value !== "string" || !DAY.test(value)) return null;
  const at = Date.parse(value + "T00:00:00Z");
  return Number.isFinite(at) && new Date(at).toISOString().slice(0,10) === value
    ? at / DAY_MS : null;
}
export function validateRange(cik, from, to, today) {
  const a=dayNumber(from), b=dayNumber(to), t=dayNumber(today);
  if (!Object.hasOwn(SYMBOLS,cik) || a===null || b===null || t===null
      || from < "2000-01-01" || a > b || b > t || b-a > MAX_RANGE_DAYS)
    throw new Error("invalid-range");
  return {cik,from,to};
}
function price(value) {
  if ((typeof value !== "string" && typeof value !== "number")
      || value === "" || value === null) return null;
  const n=Number(value);
  return Number.isFinite(n) && n > 0 && n < 10000000 ? n : null;
}
export function normalizePriceRange(raw, cik, from, to, retrievedAt) {
  validateRange(cik,from,to,to);
  if (!Array.isArray(raw) || raw.length > MAX_RANGE_BARS)
    throw new Error("invalid-price-data");
  const seen=new Set(), rows=[];
  for (const bar of raw) {
    if (!bar || dayNumber(bar.date) === null || bar.date < from
        || bar.date > to || seen.has(bar.date))
      throw new Error("invalid-price-data");
    seen.add(bar.date);
    const close=price(bar.close), adjusted=price(bar.adjusted_close);
    if (close === null) throw new Error("invalid-price-data");
    rows.push({date:bar.date, close, adjusted});
  }
  rows.sort((a,b)=>a.date.localeCompare(b.date));
  // Preserve one price basis across the entire series; adjusted closes
  // may be recomputed by EODHD as dividends and splits occur.
  const useAdjusted=rows.length>0 && rows.every(x=>x.adjusted !== null);
  const bars=rows.map(x=>({date:x.date,price:useAdjusted?x.adjusted:x.close}));
  const first=bars.length ? {...bars[0]} : null;
  const last=bars.length ? {...bars[bars.length-1]} : null;
  const changePct=first && last && bars.length>=2
    ? Math.round((last.price/first.price-1)*10000)/100 : null;
  return {
    schemaVersion:1,source:"eodhd-eod",readOnly:true,
    cik,symbol:SYMBOLS[cik],from,to,retrievedAt,
    priceBasis:useAdjusted?"ADJUSTED CLOSE":"CLOSE",
    first,last,changePct,bars,
    scope:"Selected trading sessions in an inclusive requested date range"
  };
}
export async function loadPriceRange(cik,from,to, fetcher=fetch,
    tokenLoader=loadOptionalToken, today=new Date().toISOString().slice(0,10)) {
  validateRange(cik,from,to,today);
  const token=await tokenLoader();
  const msftTrial=!token && cik==="0000789019";
  if (!token && cik!=="0000320193" && !msftTrial)
    throw new Error("provider-key-required");
  const params=new URLSearchParams({
    api_token:token||"demo",fmt:"json",from,to,period:"d",order:"a"
  });
  let response;
  try {
    response=await fetcher("https://eodhd.com/api/eod/"+SYMBOLS[cik]+"?"+params,{
      method:"GET",redirect:"error",headers:{Accept:"application/json"},
      signal:AbortSignal.timeout(12000)
    });
  } catch {
    throw new Error("provider-unavailable");
  }
  if (!response.ok) {
    if (msftTrial && (response.status===401 || response.status===403))
      throw new Error("demo-not-authorized");
    throw new Error("provider-unavailable");
  }
  const length=Number(response.headers?.get?.("content-length"));
  if (Number.isFinite(length) && length>MAX_BODY)
    throw new Error("provider-response-too-large");
  let body;
  try {body=await response.text();}
  catch {throw new Error("provider-unavailable");}
  if (body.length>MAX_BODY) throw new Error("provider-response-too-large");
  if (msftTrial && /^(unauthenticated|unauthorized|forbidden|access denied)\s*$/i.test(body.trim()))
    throw new Error("demo-not-authorized");
  let raw;
  try {raw=JSON.parse(body);}
  catch {throw new Error("provider-invalid");}
  return normalizePriceRange(raw,cik,from,to,new Date().toISOString());
}
if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const result=await loadPriceRange(process.argv[2],process.argv[3],process.argv[4]);
    process.stdout.write("FINANCE_STOCK_RANGE "+JSON.stringify(result)+"\n");
  }catch(error){
    const known=new Set(["invalid-range","provider-key-required","demo-not-authorized",
      "provider-unavailable","provider-response-too-large","provider-invalid",
      "invalid-price-data","token-unreadable","token-permissions","token-invalid"]);
    const code=known.has(error?.message)?error.message:"provider-failed";
    process.stdout.write("FINANCE_STOCK_RANGE_ERROR "+code+"\n");
    process.exitCode=1;
  }
}
