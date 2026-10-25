// M10: local Market Hub read-through for a bounded EOD price range.
// Same absent-only fallback as M8; never bypass an active failing hub.
import {pathToFileURL} from "node:url";
import {SYMBOLS} from "./read_sec_price_context.mjs";
import {loadPriceRange,validateRange,MAX_RANGE_BARS,dayNumber}
  from "./read_market_price_range.mjs";

const HOST="127.0.0.1",PORT=48731,MAX_BODY=192000;
const ERRORS=new Set(["invalid-range","invalid-selection","unknown-provider",
  "provider-busy","provider-key-required","demo-not-authorized",
  "provider-unavailable","provider-response-too-large","provider-invalid",
  "invalid-price-data","invalid-provider-snapshot","token-unreadable",
  "token-permissions","token-invalid","provider-failed"]);
function fail(code){const error=new Error(code);error.code=code;return error;}
function refused(error){
  return error?.cause?.code==="ECONNREFUSED" || error?.code==="ECONNREFUSED";
}
async function boundedJson(response){
  const len=Number(response.headers?.get?.("content-length"));
  if(Number.isFinite(len)&&len>MAX_BODY)throw fail("hub-invalid-response");
  let text;
  try{text=await response.text();}catch{throw fail("hub-unhealthy");}
  if(text.length>MAX_BODY)throw fail("hub-invalid-response");
  try{return JSON.parse(text);}catch{throw fail("hub-invalid-response");}
}
function validateResult(x,cik,from,to) {
  if(!x || x.schemaVersion!==1 || x.source!=="eodhd-eod" || x.readOnly!==true
      || x.cik!==cik || x.symbol!==SYMBOLS[cik]
      || x.from!==from || x.to!==to
      || !["CLOSE","ADJUSTED CLOSE"].includes(x.priceBasis)
      || typeof x.retrievedAt!=="string" || !Number.isFinite(Date.parse(x.retrievedAt))
      || !Array.isArray(x.bars) || x.bars.length>MAX_RANGE_BARS
      || !x.bars.every((v,i)=>v&&dayNumber(v.date)!==null&&v.date>=from
        &&v.date<=to&&Number.isFinite(v.price)&&v.price>0
        &&(i===0||x.bars[i-1].date<v.date))
      || (x.first===null)!==(x.bars.length===0)
      || (x.last===null)!==(x.bars.length===0)
      || (x.first && (x.first.date!==x.bars[0].date
          || x.first.price!==x.bars[0].price))
      || (x.last && (x.last.date!==x.bars[x.bars.length-1].date
          || x.last.price!==x.bars[x.bars.length-1].price))
      || (x.changePct!==null && !Number.isFinite(x.changePct))
      || (x.bars.length<2 && x.changePct!==null))
    throw fail("hub-invalid-response");
  return x;
}
function validateHub(x) {
  const h=x?.hub;
  if(!h || h.provider!=="eodhd"
      || !["FETCHED","CACHED","SHARED"].includes(h.state)
      || !Number.isFinite(Date.parse(h.cachedAt))
      || !Number.isFinite(Date.parse(h.servedAt))
      || !Number.isFinite(Date.parse(h.expiresAt))
      || !Number.isSafeInteger(h.ageSeconds) || h.ageSeconds<0
      || Date.parse(h.expiresAt)<=Date.parse(h.cachedAt))
    throw fail("hub-invalid-response");
  return {via:"HUB",state:h.state,cachedAt:h.cachedAt,
    servedAt:h.servedAt,expiresAt:h.expiresAt,ageSeconds:h.ageSeconds};
}
export async function readOptionalRange(cik,from,to,{
  fetcher=fetch,directReader=loadPriceRange,port=PORT,
  now=()=>new Date().toISOString()
}={}) {
  validateRange(cik,from,to,now().slice(0,10));
  if(!Number.isInteger(port)||port<1024||port>65535)throw fail("invalid-range");
  const base="http://"+HOST+":"+port;
  const headers={"X-Post-Apollo-Client":"financew",
    "Accept":"application/json","Connection":"close"};
  let health;
  try {
    const r=await fetcher(base+"/v1/health",{
      method:"GET",redirect:"error",headers,signal:AbortSignal.timeout(900)
    });
    if(!r.ok)throw fail("hub-unhealthy");
    health=await boundedJson(r);
  }catch(error){
    if(!refused(error))
      throw fail(error?.code==="hub-invalid-response"?"hub-invalid-response":"hub-unhealthy");
    const data=validateResult(await directReader(cik,from,to),cik,from,to);
    return {...data,delivery:{via:"DIRECT",state:"DIRECT",
      servedAt:now(),cachedAt:null,expiresAt:null,ageSeconds:null}};
  }
  if(!health || health.schemaVersion!==1
      || health.service!=="post-apollo-market-hub"
      || health.readOnly!==true || health.backgroundPolling!==false
      || !Array.isArray(health.providerIds)
      || !health.providerIds.includes("eodhd"))
    throw fail("hub-unhealthy");
  let r;
  try{
    r=await fetcher(base+"/v1/price-range?cik="+cik+"&from="+from+"&to="+to,{
      method:"GET",redirect:"error",headers,signal:AbortSignal.timeout(14000)
    });
  }catch{throw fail("hub-unhealthy");}
  const data=await boundedJson(r);
  if(!r.ok)throw fail(ERRORS.has(data?.error)?data.error:"hub-unhealthy");
  return {...validateResult(data,cik,from,to),delivery:validateHub(data)};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  try{
    const rawPort=process.env.POST_APOLLO_MARKET_HUB_PORT;
    const port=rawPort===undefined?PORT:Number(rawPort);
    const result=await readOptionalRange(process.argv[2],process.argv[3],process.argv[4],{port});
    process.stdout.write("FINANCE_STOCK_RANGE "+JSON.stringify(result)+"\n");
  }catch(error){
    const code=ERRORS.has(error?.code||error?.message)
      ?(error.code||error.message)
      :["hub-unhealthy","hub-invalid-response"].includes(error?.code)
        ?error.code:"provider-failed";
    process.stdout.write("FINANCE_STOCK_RANGE_ERROR "+code+"\n");
    process.exitCode=1;
  }
}
