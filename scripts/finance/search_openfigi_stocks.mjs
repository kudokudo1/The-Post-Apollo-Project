// Finance Market M17: explicit, no-key worldwide equity identity search.
// OpenFIGI v3 returns FIGI/ticker/exchange metadata, NOT prices or entitlements.
// Read-only POST on explicit operator action, no persistence or background work.
import {pathToFileURL} from "node:url";

export const ENDPOINT="https://api.openfigi.com/v3/search";
const MAX_BODY=256000;
const PAGE_LIMIT=100;
const QUERY_MAX=80;
const CURSOR_MAX=512;
const FIGI=/^BBG[A-Z0-9]{9}$/;
function fail(code){throw new Error(code);}
export function validateSearch(query,cursor="") {
  if(typeof query!=="string" || typeof cursor!=="string")fail("invalid-query");
  const text=query.trim().replace(/\s+/gu," ");
  if(text.length<2 || text.length>QUERY_MAX
      || text.split(" ").length>12 || /[\x00-\x1f\x7f]/u.test(text))
    fail("invalid-query");
  if(cursor.length>CURSOR_MAX
      || (cursor!=="" && !/^[A-Za-z0-9._+=/-]+$/.test(cursor)))
    fail("invalid-cursor");
  return {query:text,cursor};
}
function short(value,max) {
  return typeof value==="string" && value.length>0
      && value.length<=max && !/[\x00-\x1f\x7f]/.test(value)
    ? value : null;
}
export function normalizeResponse(raw,query,cursor,retrievedAt) {
  if(!raw || typeof raw!=="object" || Array.isArray(raw)
      || !Array.isArray(raw.data) || raw.data.length>PAGE_LIMIT
      || raw.error!==undefined && raw.error!==null
      || raw.next!==undefined && (typeof raw.next!=="string"
          || raw.next.length===0 || raw.next.length>CURSOR_MAX
          || !/^[A-Za-z0-9._+=/-]+$/.test(raw.next)))
    fail("invalid-provider-data");
  const items=[],seen=new Set();
  for(const row of raw.data) {
    if(!row || row.marketSector!=="Equity"
        || /option|warrant|future|index|fund|etf|etn|right|forward|swap|bond|certificate/i
          .test(String(row.securityType2||"")+" "+String(row.securityType||"")))
      continue;
    const figi=short(row.figi,12), ticker=short(row.ticker,60);
    const name=short(row.name,180), exchCode=short(row.exchCode,32);
    const securityType=short(row.securityType2,80)
      || short(row.securityType,80) || "EQUITY";
    if(!figi || !FIGI.test(figi) || !ticker || !name || !exchCode
        || seen.has(figi))continue;
    seen.add(figi);
    items.push({figi,ticker,name,exchCode,securityType});
  }
  return {schemaVersion:1,source:"openfigi-v3",readOnly:true,
    query,cursor,next:raw.next||"",retrievedAt,
    priceLinked:false,items};
}
export async function searchStocks(query,cursor="",fetcher=fetch,
    now=()=>new Date().toISOString()) {
  const valid=validateSearch(query,cursor);
  const request={query:valid.query,marketSecDes:"Equity"};
  if(valid.cursor)request.start=valid.cursor;
  let response;
  try{
    response=await fetcher(ENDPOINT,{method:"POST",redirect:"error",
      headers:{"Content-Type":"application/json","Accept":"application/json"},
      body:JSON.stringify(request),signal:AbortSignal.timeout(12000)});
  }catch{fail("provider-unavailable");}
  if(response.status===429)fail("rate-limited");
  if(!response.ok)fail("provider-unavailable");
  const lenHeader=response.headers?.get?.("content-length");
  if(lenHeader!==null && lenHeader!==undefined
      && Number.isFinite(Number(lenHeader)) && Number(lenHeader)>MAX_BODY)
    fail("provider-response-too-large");
  let body;
  try{body=await response.text();}catch{fail("provider-unavailable");}
  if(body.length>MAX_BODY)fail("provider-response-too-large");
  let json;
  try{json=JSON.parse(body);}catch{fail("invalid-provider-data");}
  return normalizeResponse(json,valid.query,valid.cursor,now());
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href){
  try{
    const result=await searchStocks(process.argv[2],process.argv[3]||"");
    process.stdout.write("FINANCE_STOCK_SEARCH "+JSON.stringify(result)+"\n");
  }catch(error){
    const known=new Set(["invalid-query","invalid-cursor","invalid-provider-data",
      "provider-unavailable","provider-response-too-large","rate-limited"]);
    const code=known.has(error?.message)?error.message:"search-failed";
    process.stdout.write("FINANCE_STOCK_SEARCH_ERROR "+code+"\n");
    process.exitCode=1;
  }
}
