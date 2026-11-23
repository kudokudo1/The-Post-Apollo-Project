#!/usr/bin/env node
// M21: reads only fictional/disposable quota data. No market provider calls.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";

const read=file=>readFileSync(new URL(file,import.meta.url),"utf8");
const python=read("../../scripts/finance/market_quota_status.py");
const m20=read("../../scripts/finance/market_shared_quota.py");
const service=read("../../services/finance/FinanceMarketQuotaStatusService.qml");
const pane=read("../../widgets/FinanceMarketQuotaStatusPane.qml");
const stocks=read("../../widgets/FinanceStockHistoryPane.qml");
const eod=read("../../services/finance/FinanceGlobalPriceService.qml");
const alpha=read("../../services/finance/FinanceAlphaVantageFreeService.qml");

for(const string of [
  "sqlite3.connect(\":memory:\")",
  "conn.deserialize(data)",
  "fcntl.lockf(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)",
  'getattr(os, "O_NOATIME", 0)',
  "os.O_RDONLY | os.O_NOFOLLOW",
  "if sibling_exists():",
  "data[18] != 1 or data[19] != 1",
  "quota_attempts WHERE utc_day=?",
  "row" // Included in the existing row validation documentation/code.
])assert.ok(python.includes(string),string);
assert.ok(!python.includes("os.mkdir("));
assert.ok(!python.includes('sqlite3.connect(str(path)'));
assert.ok(!python.includes('from market_shared_quota import reserve'));
assert.ok(!python.includes("PRAGMA journal_mode=WAL"));
assert.ok(!python.includes("UPDATE quota_attempts"));
assert.ok(!python.includes("DELETE FROM quota_attempts"));
assert.ok(!python.includes("CREATE TABLE"));
assert.ok(!python.includes("INSERT INTO"));
assert.ok(!python.includes("requests.get("));
assert.ok(!python.includes("urlopen("));
assert.ok(!python.includes("api_token"));
assert.ok(!python.includes("fetch("));
assert.ok(m20.includes("BEGIN IMMEDIATE"));
assert.ok(m20.includes('DB_NAME = "global-free-provider-attempts-v1.sqlite3"'));
assert.ok(python.includes('from market_shared_quota import LIMITS, SCOPE, DB_NAME'));

assert.ok(service.includes('Quickshell.shellPath("scripts/finance/market_quota_status.py")'));
assert.ok(service.includes('function refresh() {'));
assert.ok(service.includes('else refresh();')); // local-only first open read
assert.ok(service.includes('onMonitoringChanged: {'));
assert.ok(service.includes('if (!monitoring) clear();'));
assert.ok(service.includes('if (!monitoring || reader.running || loading) return false;'));
assert.ok(service.includes('data.noProviderCalls!==true'));
assert.ok(service.includes('data.notAccountBalance!==true'));
assert.ok(service.includes('data.ledgerState'));
assert.ok(service.includes('row.reserved===null'));
assert.ok(service.includes('"eodhd",20'));
assert.ok(service.includes('"alpha-vantage",25'));
assert.ok(service.includes('data.providers.length!==2'));
assert.ok(service.includes('state="unavailable"'));
assert.equal((service.match(/reader.exec\(\[/g)||[]).length,1);
assert.ok(!service.includes("market_shared_quota.py"));
assert.ok(!service.includes('"reserve"'));
assert.ok(!service.includes("read_global_eodhd_history.mjs"));
assert.ok(!service.includes("read_alpha_vantage_free.mjs"));

assert.ok(pane.includes('label: "BACK TO STOCKS"'));
assert.ok(pane.includes('"REFRESH LOCAL STATUS"'));
assert.ok(pane.includes('"LOCAL RESERVED UNKNOWN"'));
assert.ok(pane.includes('"NO USAGE CONCLUSION // NO ZERO ASSUMED"'));
assert.ok(pane.includes('"NOT ACCOUNT BALANCE'));
assert.ok(pane.includes('NO API CALLS'));
assert.ok(pane.includes('NO QUOTA RESET'));
assert.ok(pane.includes('FinanceServices.FinanceMarketQuotaStatusService'));
assert.ok(!pane.includes("Process {"));
assert.ok(stocks.includes('label: "QUOTA STATUS"'));
assert.ok(stocks.includes('FinanceMarketQuotaStatusPane {'));
assert.ok(stocks.includes('onExitRequested: stocks.quotaOpen = false'));
assert.ok(stocks.includes('stocks.discoveryOpen = false;'));
assert.ok(stocks.includes('stocks.quotaOpen = false;'));
assert.ok(eod.includes("sharedQuota=data.localQuota;"));
assert.ok(alpha.includes("sharedQuota=data.localQuota;"));
for(const file of [service,pane,stocks])for(const forbidden of [
  "financeWrite.submit(","financeFundingWrite.submit(","Qt.openUrlExternally",
  "writeFile(","setInterval(","market_shared_quota.py",
  "https://eodhd.com/api/","https://www.alphavantage.co/query"
])assert.ok(!file.includes(forbidden),"forbidden code in new status seam: "+forbidden);

const cmd=fileURLToPath(new URL("./test_market_quota_status.py",import.meta.url));
const output=execFileSync("/usr/bin/env",["python3",cmd],{
  encoding:"utf8",timeout:22000,maxBuffer:100000
});
assert.match(output,/Finance M21 no-write quota inspection.*PASS/);
console.log("Finance M21 read-only quota status, unknown-state refusal, provider isolation and native-source contracts: PASS");
