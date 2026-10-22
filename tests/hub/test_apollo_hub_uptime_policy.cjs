#!/usr/bin/env node
"use strict";
// Run the production pure-JS uptime policy with synthetic procfs readings.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubUptimePolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, { filename: "ApolloHubUptimePolicy.js" });

const now = 5000000;
const snap = (raw,stamp=now-1000,clock=now,error=false) =>
    policy.snapshot(raw,stamp,clock,error);

const healthy = snap("93784.25 120000.12\n"); // 1 day, 2 hours, 3 minutes
assert.equal(healthy.state,"ready");
assert.equal(healthy.source,"linux-procfs");
assert.equal(healthy.ready,true);
assert.equal(healthy.approximate,true);
assert.equal(healthy.uptimeSeconds,93785);
assert.equal(healthy.days,1);
assert.equal(healthy.hours,2);
assert.equal(healthy.minutes,3);
assert.equal(healthy.label,"1D 02H 03M");
assert.equal(healthy.ageSeconds,1);
assert.equal(healthy.observedAtMs,now-1000);

assert.equal(snap("0.00 0.00").state,"ready");
assert.equal(snap("0.00 0.00").days,0);
assert.equal(snap("60.0 600.0").minutes,1);
assert.equal(snap("3599.2 1",now).hours,0);
assert.equal(snap("86400 100",now).days,1);
assert.equal(snap("99999999.99 888",now).state,"ready");

// Refreshes are frequent enough that we never infer uptime indefinitely.
assert.equal(snap("93784.25 120000.12",now-150000).state,"ready");
const stale=snap("93784.25 120000.12",now-150001);
assert.equal(stale.state,"stale");
assert.equal(stale.ready,false);
assert.equal(stale.label,"--");
assert.equal(stale.uptimeSeconds,-1);
assert.equal(stale.days,-1);
assert.equal(snap("93784.25 120000.12",now+1).state,"unobserved");
assert.equal(snap("93784.25 120000.12",0).state,"unobserved");
assert.equal(snap("93784.25 120000.12",NaN).state,"unobserved");

const failed=snap("93784.25 120000.12",now-1000,now,true);
assert.equal(failed.state,"error");
assert.equal(failed.ready,false);
assert.equal(failed.label,"--");

for (const bad of ["", "hello", "garbage 1.0", "0", "-1 200",
 "NaN 10", "Infinity 10", "2.5 NaN", "2e5 2",
 "12.1 3.4 trailing", "12.1", null, undefined, {}, [],
 "10000000001 3", "\n"]) {
    const x=snap(bad);
    assert.equal(x.state,"unavailable",String(bad));
    assert.equal(x.uptimeSeconds,-1);
    assert.equal(x.ready,false);
}
assert.equal(policy.parseSeconds("1.23 4.56"),1.23);
assert.equal(policy.parseSeconds("0 0"),0);
assert.equal(policy.parseSeconds("42 3"),42);

// No command, boot identifier, idle-time number, raw /proc content, PID,
// machine identifier or mutable handle is returned to a consumer.
const serialized = JSON.stringify(healthy);
for(const forbidden of ["120000.12","command","process","FileView",
                         "/proc/uptime","setText","reload","pid","secret"])
    assert.equal(serialized.includes(forbidden),false,forbidden);

console.log("ApolloHub B5 Linux uptime policy behavior tests passed");
