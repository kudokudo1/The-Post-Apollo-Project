// Finance Market M19: explicit Alpha Vantage free-key global equity search/EOD.
// Separate from EODHD, FIGI identities, market Hub, accounts, and all writers.
// Free endpoints only: SYMBOL_SEARCH and TIME_SERIES_DAILY outputsize=compact.
import {homedir} from "node:os";
import {join} from "node:path";
import {pathToFileURL} from "node:url";
import {loadOptionalToken} from "./read_sec_price_context.mjs";
import {dayNumber} from "./read_market_price_range.mjs";

export const ALPHA_TOKEN_FILE=join(homedir(),".local","share",
  "post-apollo","finance-market","alpha-vantage-token.txt");
export const ALPHA_FREE_LIMIT=25;
const MAX_BODY=192000;
const TICKER=/^[A-Z0-9][A-Z0-9_.-]{0,29}$/;
const SYMBOL=/^[A-Z0-9][A-Z0-9_.-]{0,44}$/;
const CURRENCY=/^[A-Z]{3}$/;
const MAX_BARS=100;
const MAX_RANGE_DAYS=180;
const fail=(code)=>{throw new Error(code);};
function safe(value,max) {
  return typeof value==="string" && value.length>0
    && value.length<=max && !/[\x00-\x1f\x7f]/.test(value) ? value : null;
}
export function validTicker(value) {
  if(typeof value!=="string" || !TICKER.test(value)
      || value!==value.toUpperCase() || value.includes(".."))
    fail("invalid-ticker");
  return value;
}
export function validSymbol(value) {
  if(typeof value!=="string" || !SYMBOL.test(value)
      || value!==value.toUpperCase() || value.includes(".."))
    fail("invalid-symbol");
  return value;
}
export function validRange(from,to,today) {
  const a=dayNumber(from),b=dayNumber(to),c=dayNumber(today);
  if(a===null || b===null || c===null || from<"2000-01-01"
      || a>b || b>c || b-a>MAX_RANGE_DAYS)
    fail("invalid-range");
  return {from,to};
}
function parseLimit(raw) {
  if(!raw || typeof raw!=="object" || Array.isArray(raw))
    fail("provider-invalid");
  if(typeof raw.Note==="string" || typeof raw.Information==="string")
    fail("provider-rate-or-entitlement");
  if(typeof raw["Error Message"]==="string")
    fail("provider-symbol-unavailable");
  return raw;
}
async function request(params,fetcher=fetch,
    tokenLoader=loadOptionalToken) {
  let token=await tokenLoader(ALPHA_TOKEN_FILE);
  if(!token)fail("provider-key-required");
  const qs=new URLSearchParams({...params,apikey:token,datatype:"json"});
  let response;
  try{
    response=await fetcher("https://www.alphavantage.co/query?"+qs,{
      method:"GET",redirect:"error",headers:{Accept:"application/json"},
      signal:AbortSignal.timeout(12000)
    });
  }catch{fail("provider-unavailable");}
  if(response?.status===429)fail("provider-rate-or-entitlement");
  if(response?.status===401)fail("provider-key-invalid");
  if(response?.status===402 || response?.status===403)
    fail("provider-not-entitled");
  if(!response || response.ok!==true)fail("provider-unavailable");
  const length=response.headers?.get?.("content-length");
  if(length!==null && length!==undefined
      && Number.isFinite(Number(length)) && Number(length)>MAX_BODY)
    fail("provider-response-too-large");
  let body;
  try{body=await response.text();}catch{fail("provider-unavailable");}
  if(body.length>MAX_BODY)fail("provider-response-too-large");
  let raw;
  try{raw=JSON.parse(body);}catch{fail("provider-invalid");}
  return parseLimit(raw);
}
export function normalizeMatches(raw,ticker,retrievedAt) {
  validTicker(ticker);
  const response=parseLimit(raw);
  if(!Array.isArray(response.bestMatches) || response.bestMatches.length>25)
    fail("provider-invalid");
  const rows=[],seen=new Set();
  for(const item of response.bestMatches) {
    if(!item || !safe(item["1. symbol"],45)
      || !safe(item["2. name"],160)
      || !safe(item["3. type"],70)
      || !safe(item["4. region"],80)
      || !CURRENCY.test(item["8. currency"]||""))
      continue;
    const symbol=item["1. symbol"],type=item["3. type"];
    if(!SYMBOL.test(symbol) || symbol.includes("..")
      || !(symbol===ticker || symbol.startsWith(ticker+"."))
      || /etf|fund|index|bond|option|warrant|future|etn|forex|crypto/i.test(type)
      || !/equity|stock|share/i.test(type) || seen.has(symbol))
      continue;
    seen.add(symbol);
    rows.push({symbol,name:item["2. name"],type,region:item["4. region"],
      currency:item["8. currency"],matchedOpenFigi:false});
  }
  return {schemaVersion:1,source:"alpha-vantage-symbol-search",readOnly:true,
    queryTicker:ticker,retrievedAt,priceLinked:false,items:rows};
}
export async function searchAlpha(ticker,fetcher=fetch,
    tokenLoader=loadOptionalToken,now=()=>new Date().toISOString()) {
  validTicker(ticker);
  const raw=await request({function:"SYMBOL_SEARCH",keywords:ticker},
    fetcher,tokenLoader);
  return normalizeMatches(raw,ticker,now());
}
function closePrice(x) {
  if(typeof x!=="number" && typeof x!=="string")return null;
  if(x===null || x==="")return null;
  const n=Number(x);
  return Number.isFinite(n) && n>0 && n<10000000 ? n : null;
}
export function normalizeDaily(raw,symbol,currency,from,to,retrievedAt) {
  validSymbol(symbol);
  if(!CURRENCY.test(currency))fail("invalid-currency");
  validRange(from,to,to);
  const response=parseLimit(raw);
  const meta=response["Meta Data"],series=response["Time Series (Daily)"];
  if(!meta || typeof meta!=="object"
      || meta["2. Symbol"]!==symbol
      || !series || typeof series!=="object" || Array.isArray(series))
    fail("provider-invalid");
  const days=Object.keys(series);
  if(days.length===0 || days.length>MAX_BARS)
    fail("provider-invalid");
  const rows=[];
  for(const date of days) {
    if(dayNumber(date)===null || date>to && dayNumber(date)===null)
      fail("provider-invalid");
    const item=series[date],price=closePrice(item?.["4. close"]);
    if(price===null)fail("provider-invalid");
    if(date>=from && date<=to)rows.push({date,price});
  }
  rows.sort((a,b)=>a.date.localeCompare(b.date));
  const allSorted=days.sort();
  const oldest=allSorted[0],latest=allSorted[allSorted.length-1];
  const first=rows.length?{...rows[0]}:null;
  const last=rows.length?{...rows[rows.length-1]}:null;
  const changePct=first && last && rows.length>=2
    ? Math.round((last.price/first.price-1)*10000)/100 : null;
  return {schemaVersion:1,source:"alpha-vantage-daily-compact",readOnly:true,
    symbol,currency,from,to,retrievedAt,priceBasis:"CLOSE",
    currencySource:"alpha-vantage-symbol-search",identityVerified:false,
    compactMaxBars:MAX_BARS,returnedBars:days.length,
    compactMayBeTruncated:days.length===MAX_BARS && oldest>from,
    oldestAvailable:oldest,latestAvailable:latest,
    first,last,changePct,bars:rows};
}
export async function loadAlphaDaily(symbol,currency,from,to,
    fetcher=fetch,tokenLoader=loadOptionalToken,
    today=new Date().toISOString().slice(0,10),
    now=()=>new Date().toISOString()) {
  validSymbol(symbol);
  if(!CURRENCY.test(currency))fail("invalid-currency");
  validRange(from,to,today);
  const raw=await request({function:"TIME_SERIES_DAILY",
    symbol,outputsize:"compact"},fetcher,tokenLoader);
  return normalizeDaily(raw,symbol,currency,from,to,now());
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const args=process.argv.slice(2);
    const result=args[0]==="lookup" && args.length===2
      ? await searchAlpha(args[1])
      : args[0]==="history" && args.length===5
      ? await loadAlphaDaily(args[1],args[2],args[3],args[4])
      : fail("invalid-command");
    process.stdout.write("FINANCE_ALPHA_FREE "+JSON.stringify(result)+"\n");
  }catch(error) {
    const allowed=new Set(["invalid-ticker","invalid-symbol","invalid-currency",
      "invalid-range","invalid-command","provider-key-required",
      "provider-key-invalid","provider-not-entitled","provider-unavailable",
      "provider-rate-or-entitlement","provider-symbol-unavailable",
      "provider-response-too-large","provider-invalid","token-unreadable",
      "token-permissions","token-invalid"]);
    const code=allowed.has(error?.message)?error.message:"provider-failed";
    process.stdout.write("FINANCE_ALPHA_FREE_ERROR "+code+"\n");
    process.exitCode=1;
  }
}
