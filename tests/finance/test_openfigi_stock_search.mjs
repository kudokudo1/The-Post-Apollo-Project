#!/usr/bin/env node
// M17 fake-only no-account global equity discovery. NO real provider request.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validateSearch,normalizeResponse,searchStocks,ENDPOINT}
  from "../../scripts/finance/search_openfigi_stocks.mjs";

const r=(file)=>readFileSync(new URL(file,import.meta.url),"utf8");
const real=[{
  figi:"BBG000BLNNH6",name:"INTL BUSINESS MACHINES CORP",
  ticker:"IBM",exchCode:"US",marketSector:"Equity",
  securityType:"Common Stock",securityType2:"Common Stock"
},{
  figi:"BBG000B7XTX7",name:"MITSUBISHI",ticker:"8058",exchCode:"JP",
  marketSector:"Equity",securityType2:"Common Stock"
},{
  figi:"BBG0002ZTPD8",name:"IBM CALL OPTION",ticker:"IBM C105",
  exchCode:"US",marketSector:"Equity",securityType2:"Option"
},{
  figi:"BBG000B8XZZ9",name:"ETF",ticker:"ETF1",exchCode:"US",
  marketSector:"Equity",securityType2:"ETF"
}];
const cursor="QW9JSVFEOFMrQ3hDUWtjd01ERTRTMHhhUXpBPSAx.3AG33VCsv54AsUl5fGHehSytWPuWLJxf0t8VL3YXuJh=";
assert.deepEqual(validateSearch(" asml   holding "),{
  query:"asml holding",cursor:""
});
for(const q of ["x","", "a".repeat(81),"a ".repeat(14),
  "\ninvalid","a\u0000b"])
  assert.throws(()=>validateSearch(q),/invalid-query/);
for(const c of ["?bad","a".repeat(513),"abc\n--"])
  assert.throws(()=>validateSearch("sony",c),/invalid-cursor/);
const normalized=normalizeResponse({data:real,next:cursor},
  "ibm","","2026-11-22T15:00:00Z");
assert.equal(normalized.schemaVersion,1);
assert.equal(normalized.source,"openfigi-v3");
assert.equal(normalized.readOnly,true);
assert.equal(normalized.priceLinked,false);
assert.equal(normalized.next,cursor);
assert.equal(normalized.items.length,2); // no option or ETF false-positives
assert.equal(normalized.items[0].figi,"BBG000BLNNH6");
assert.equal(normalized.items[0].ticker,"IBM");
assert.equal(normalized.items[1].ticker,"8058");
assert.equal(normalized.items[1].exchCode,"JP");
assert.equal(normalizeResponse({data:[real[0],real[0]]},
  "ibm","","now").items.length,1);
assert.equal(normalizeResponse({data:[{...real[0],
  figi:"1234"},{...real[0],name:"a\nunsafe"}]},
  "ibm","","now").items.length,0);
for(const bad of [{data:null},{data:[],"next":"bad?"},
  {data:new Array(101).fill(real[0])},{data:[],error:"error"}])
  assert.throws(()=>normalizeResponse(bad,"ibm","","now"),
    /invalid-provider-data/);

let count=0;
const fake=async(url,options)=>{
  count++;
  assert.equal(url,ENDPOINT);
  assert.equal(options.method,"POST");
  assert.equal(options.redirect,"error");
  assert.equal(options.headers["Content-Type"],"application/json");
  assert.equal(options.headers.Accept,"application/json");
  assert.equal(options.headers["X-OPENFIGI-APIKEY"],undefined);
  const body=JSON.parse(options.body);
  assert.equal(body.query,"ibm");
  assert.equal(body.marketSecDes,"Equity");
  if(count===1)assert.equal(body.start,undefined);
  else assert.equal(body.start,cursor);
  return {ok:true,status:200,headers:{get:()=>null},
    text:async()=>JSON.stringify({data:real,next:count===1?cursor:undefined})};
};
const first=await searchStocks("ibm","",fake,()=>"2026-11-22T15:00:00Z");
assert.equal(first.items.length,2);
const second=await searchStocks("ibm",first.next,fake,()=>"2026-11-22T15:05:00Z");
assert.equal(second.next,"");
assert.equal(second.cursor,cursor);
assert.equal(count,2);
await assert.rejects(searchStocks("ibm", "?command",fake),/invalid-cursor/);
assert.equal(count,2); // refusal before network
await assert.rejects(searchStocks("ibm","",async()=>
  ({ok:false,status:429})),/rate-limited/);
await assert.rejects(searchStocks("ibm","",async()=>
  ({ok:false,status:503})),/provider-unavailable/);
await assert.rejects(searchStocks("ibm","",async()=>
  ({ok:true,status:200,headers:{get:()=>300000}})),
  /provider-response-too-large/);
await assert.rejects(searchStocks("ibm","",async()=>
  ({ok:true,status:200,headers:{get:()=>null},
    text:async()=>"not-json"})),/invalid-provider-data/);

const bridge=r("../../services/finance/FinanceStockDiscoveryService.qml");
const searchUi=r("../../widgets/FinanceStockDiscoveryPane.qml");
const historyUi=r("../../widgets/FinanceStockHistoryPane.qml");
const original=r("../../services/finance/FinanceStockHistoryReadService.qml");
assert.ok(bridge.includes('function search(query) {'));
assert.ok(bridge.includes('function nextPage() {'));
assert.ok(bridge.includes('if (!monitoring || loading || reader.running'));
assert.ok(bridge.includes('data.query!==requestedQuery || data.cursor!==requestedCursor'));
assert.ok(bridge.includes('data.priceLinked!==false'));
assert.ok(bridge.includes('if (!monitoring) clear();'));
assert.ok(bridge.includes('Quickshell.shellPath("scripts/finance/search_openfigi_stocks.mjs")'));
assert.equal((bridge.match(/reader.exec\(\[/g)||[]).length,1);
assert.doesNotMatch(bridge,/onMonitoringChanged:[\s\S]*?if\s*\(monitoring\)\s*search\(/);
assert.ok(searchUi.includes('label: "NEXT PAGE"'));
assert.ok(searchUi.includes('label: "SEARCH"'));
assert.ok(searchUi.includes('FinanceServices.FinanceStockDiscoveryService {'));
assert.ok(searchUi.includes('TextInput {'));
assert.ok(searchUi.includes('textFormat: Text.PlainText'));
assert.ok(searchUi.includes('available: discovery.active && !finder.loading'));
assert.ok(historyUi.includes('label: "GLOBAL SEARCH"'));
assert.ok(historyUi.includes('FinanceStockDiscoveryPane {'));
assert.ok(historyUi.includes('onExitRequested: stocks.discoveryOpen = false'));
assert.equal((original.match(/reader.exec\(\[/g)||[]).length,1);
for(const source of [bridge,searchUi,historyUi]) {
  for(const forbidden of ["financeWrite.submit(","financeFundingWrite.submit(",
    "Qt.openUrlExternally","setInterval(","writeFile(","https://clob.polymarket.com/order"])
    assert.ok(!source.includes(forbidden),forbidden);
}
assert.ok(!searchUi.includes("Process {")); // process belongs to the service
console.log("Finance M17 free global identity discovery, provider boundaries, pagination and UI contracts: PASS");
