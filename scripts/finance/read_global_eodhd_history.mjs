// Finance Market M18: selected EODHD listing -> bounded daily historical close.
// No account creation, subscription API, scraping, writes, polling or trading.
// Uses the existing owner-only optional key (free EODHD registration supported).
import {pathToFileURL} from "node:url";
import {loadOptionalToken} from "./read_sec_price_context.mjs";
import {dayNumber} from "./read_market_price_range.mjs";

export const MAX_RANGE_DAYS=180;
export const MAX_RANGE_BARS=132;
const MAX_SEARCH_BYTES=128000;
const MAX_HISTORY_BYTES=192000;
const TICKER=/^[A-Z0-9][A-Z0-9_.-]{0,29}$/;
const EXCHANGE=/^[A-Z][A-Z0-9]{0,11}$/;
const CURRENCY=/^[A-Z]{3}$/;
const ISIN=/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;
const safe=(value,max)=>typeof value==="string" && value.length>0
  && value.length<=max && !/[\x00-\x1f\x7f]/.test(value) ? value : null;
const fail=code=>{throw new Error(code);};
export function validateTicker(raw) {
  if(typeof raw!=="string" || !TICKER.test(raw) || raw!==raw.toUpperCase())
    fail("invalid-ticker");
  return raw;
}
export function validateSymbol(raw) {
  if(typeof raw!=="string" || raw.length>45 || !raw.includes("."))
    fail("invalid-symbol");
  const at=raw.lastIndexOf(".");
  const code=raw.slice(0,at),exchange=raw.slice(at+1);
  validateTicker(code);
  if(!EXCHANGE.test(exchange))fail("invalid-symbol");
  return {code,exchange,symbol:raw};
}
export function validateWindow(from,to,today) {
  const a=dayNumber(from),b=dayNumber(to),now=dayNumber(today);
  if(a===null || b===null || now===null || from<"2000-01-01"
    || a>b || b>now || b-a>MAX_RANGE_DAYS)
    fail("invalid-range");
  return {from,to};
}
function providerError(status) {
  if(status===429)fail("rate-limited");
  if(status===401)fail("provider-key-invalid");
  if(status===403 || status===402)fail("provider-not-entitled");
  fail("provider-unavailable");
}
async function responseJson(response,limit) {
  if(!response || response.ok!==true)providerError(response?.status);
  const size=response.headers?.get?.("content-length");
  if(size!==null && size!==undefined && Number.isFinite(Number(size))
      && Number(size)>limit)fail("provider-response-too-large");
  let body;
  try{body=await response.text();}catch{fail("provider-unavailable");}
  if(body.length>limit)fail("provider-response-too-large");
  try{return JSON.parse(body);}catch{fail("provider-invalid");}
}
function price(value) {
  if((typeof value!=="string" && typeof value!=="number")
      || value==="" || value===null)return null;
  const n=Number(value);
  return Number.isFinite(n) && n>0 && n<10000000 ? n : null;
}
export function normalizeCandidates(raw,ticker,retrievedAt) {
  validateTicker(ticker);
  if(!Array.isArray(raw) || raw.length>25)fail("provider-invalid");
  const items=[],seen=new Set();
  for(const row of raw) {
    if(!row || !safe(row.Code,30) || !safe(row.Exchange,12)
      || !safe(row.Name,160) || !safe(row.Type,80)
      || !safe(row.Country,60) || !CURRENCY.test(row.Currency||""))
      continue;
    const code=row.Code.toUpperCase(),exchange=row.Exchange.toUpperCase();
    if(!TICKER.test(code) || !EXCHANGE.test(exchange)
       || code!==ticker || /etf|etn|fund|index|warrant|option|bond|future|right|swap/i.test(row.Type)
       || !/stock|share|equity/i.test(row.Type))continue;
    const symbol=code+"."+exchange;
    if(seen.has(symbol))continue;
    seen.add(symbol);
    const isin=row.ISIN===null || row.ISIN===undefined ? null
      : (typeof row.ISIN==="string" && ISIN.test(row.ISIN) ? row.ISIN : null);
    items.push({symbol,code,exchange,name:row.Name,type:row.Type,
      country:row.Country,currency:row.Currency,isin});
  }
  return {schemaVersion:1,source:"eodhd-search",readOnly:true,
    queryTicker:ticker,retrievedAt,priceLinked:false,items};
}
export async function findCandidates(ticker,fetcher=fetch,
    tokenLoader=loadOptionalToken,now=()=>new Date().toISOString()) {
  validateTicker(ticker);
  const token=await tokenLoader();
  if(!token)fail("provider-key-required");
  const params=new URLSearchParams({
    api_token:token,fmt:"json",limit:"25",type:"stock"
  });
  let response;
  try{response=await fetcher(
    "https://eodhd.com/api/search/"+encodeURIComponent(ticker)+"?"+params,{
      method:"GET",redirect:"error",headers:{Accept:"application/json"},
      signal:AbortSignal.timeout(12000)
    });
  }catch{fail("provider-unavailable");}
  const raw=await responseJson(response,MAX_SEARCH_BYTES);
  return normalizeCandidates(raw,ticker,now());
}
export function normalizeHistory(raw,symbol,currency,from,to,retrievedAt) {
  validateSymbol(symbol);
  if(!CURRENCY.test(currency))fail("invalid-currency");
  validateWindow(from,to,to);
  if(!Array.isArray(raw) || raw.length>MAX_RANGE_BARS)
    fail("invalid-price-data");
  const rows=[],seen=new Set();
  for(const item of raw) {
    if(!item || dayNumber(item.date)===null || item.date<from
        || item.date>to || seen.has(item.date))
      fail("invalid-price-data");
    seen.add(item.date);
    const close=price(item.close),adjusted=price(item.adjusted_close);
    if(close===null)fail("invalid-price-data");
    rows.push({date:item.date,close,adjusted});
  }
  rows.sort((a,b)=>a.date.localeCompare(b.date));
  const adjusted=rows.length>0 && rows.every(x=>x.adjusted!==null);
  const bars=rows.map(x=>({date:x.date,price:adjusted?x.adjusted:x.close}));
  const first=bars.length ? {...bars[0]} : null;
  const last=bars.length ? {...bars[bars.length-1]} : null;
  const changePct=first && last && bars.length>=2
    ? Math.round((last.price/first.price-1)*10000)/100 : null;
  return {schemaVersion:1,source:"eodhd-eod",readOnly:true,
    symbol,currency,from,to,retrievedAt,
    priceBasis:adjusted?"ADJUSTED CLOSE":"CLOSE",
    first,last,changePct,bars,
    currencySource:"eodhd-search",identityVerified:false,
    scope:"Daily close of explicitly selected EODHD listing; not an OpenFIGI identity match"};
}
export async function readHistory(symbol,currency,from,to,fetcher=fetch,
    tokenLoader=loadOptionalToken,today=new Date().toISOString().slice(0,10),
    now=()=>new Date().toISOString()) {
  validateSymbol(symbol);
  if(!CURRENCY.test(currency))fail("invalid-currency");
  validateWindow(from,to,today);
  const token=await tokenLoader();
  if(!token)fail("provider-key-required");
  const params=new URLSearchParams({
    api_token:token,fmt:"json",from,to,period:"d",order:"a"
  });
  let response;
  try{response=await fetcher(
    "https://eodhd.com/api/eod/"+symbol+"?"+params,{
      method:"GET",redirect:"error",headers:{Accept:"application/json"},
      signal:AbortSignal.timeout(12000)
    });
  }catch{fail("provider-unavailable");}
  const raw=await responseJson(response,MAX_HISTORY_BYTES);
  return normalizeHistory(raw,symbol,currency,from,to,now());
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const args=process.argv.slice(2);
    const result=args[0]==="lookup" && args.length===2
      ? await findCandidates(args[1])
      : args[0]==="history" && args.length===5
      ? await readHistory(args[1],args[2],args[3],args[4])
      : fail("invalid-command");
    process.stdout.write("FINANCE_GLOBAL_EODHD "+JSON.stringify(result)+"\n");
  }catch(error) {
    const known=new Set(["invalid-ticker","invalid-symbol","invalid-currency",
      "invalid-range","invalid-command","provider-key-required",
      "provider-key-invalid","provider-not-entitled","rate-limited",
      "provider-unavailable","provider-response-too-large","provider-invalid",
      "invalid-price-data","token-unreadable","token-permissions","token-invalid"]);
    const reason=known.has(error?.message)?error.message:"provider-failed";
    process.stdout.write("FINANCE_GLOBAL_EODHD_ERROR "+reason+"\n");
    process.exitCode=1;
  }
}
