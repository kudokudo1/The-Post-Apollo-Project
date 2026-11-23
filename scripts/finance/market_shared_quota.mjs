// M20: local-only quota reservation shared across FinanceW's TWO global
// EODHD/Alpha Vantage readers. This is NOT the provider account balance.
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";

const PYTHON=fileURLToPath(new URL("./market_shared_quota.py",import.meta.url));
const LIMITS=Object.freeze({"eodhd":20,"alpha-vantage":25});
const SCOPE="post-apollo-market-local-v1";
const DAY=/^\d{4}-\d{2}-\d{2}$/;
function fail(code){throw new Error(code);}
export function parseReservation(raw,provider){
  if(!Object.hasOwn(LIMITS,provider))fail("local-quota-unavailable");
  const line=String(raw||"").trim();
  if(line==="FINANCE_LOCAL_QUOTA_ERROR local-quota-exhausted")
    fail("local-quota-exhausted");
  if(!line.startsWith("FINANCE_LOCAL_QUOTA "))fail("local-quota-unavailable");
  let data;
  try{data=JSON.parse(line.slice("FINANCE_LOCAL_QUOTA ".length));}
  catch{fail("local-quota-unavailable");}
  if(!data || data.schemaVersion!==1 || data.scope!==SCOPE
      || data.provider!==provider || !DAY.test(data.utcDay)
      || Number.isNaN(Date.parse(data.utcDay+"T00:00:00Z"))
      || new Date(data.utcDay+"T00:00:00Z").toISOString().slice(0,10)!==data.utcDay
      || data.limit!==LIMITS[provider] || !Number.isInteger(data.reserved)
      || data.reserved<1 || data.reserved>data.limit
      || data.notAccountBalance!==true)fail("local-quota-unavailable");
  return data;
}
export function reserveLocal(provider,runner=execFileSync){
  if(!Object.hasOwn(LIMITS,provider))fail("local-quota-unavailable");
  let output;
  try{
    output=runner("/usr/bin/env",["python3",PYTHON,"reserve",provider],{
      encoding:"utf8",timeout:6000,maxBuffer:2048,windowsHide:true,
      stdio:["ignore","pipe","pipe"]
    });
  }catch(error){
    const message=String(error?.stdout||"").trim();
    if(message==="FINANCE_LOCAL_QUOTA_ERROR local-quota-exhausted")
      fail("local-quota-exhausted");
    fail("local-quota-unavailable");
  }
  return parseReservation(output,provider);
}
export function quotaFetcher(provider,upstream=fetch,reserver=reserveLocal){
  if(!Object.hasOwn(LIMITS,provider))fail("local-quota-unavailable");
  let latest=null;
  return {
    fetcher:async(url,options)=>{
      // Atomic durable reservation happens only after provider key validation
      // and immediately before the external fetch. Provider failure/crash
      // intentionally DOES NOT refund the budget (conservative).
      latest=reserver(provider);
      return upstream(url,options);
    },
    latest:()=>latest
  };
}
