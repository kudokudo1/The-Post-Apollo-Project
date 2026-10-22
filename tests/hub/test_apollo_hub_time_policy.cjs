#!/usr/bin/env node
"use strict";
// Execute the production Hub Time formatter, respecting the process TZ.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const js = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubTimePolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p = vm.createContext({});
vm.runInContext(js,p,{filename:"ApolloHubTimePolicy.js"});

const local = (y,m,d,h=0,minute=0,second=0) =>
    new Date(y,m-1,d,h,minute,second).getTime();
const at = local(2026,10,22,13,4,5);
const t24 = p.snapshot(at,true);
assert.equal(t24.state,"ready");
assert.equal(t24.source,"local-clock");
assert.equal(t24.is24Hour,true);
assert.equal(t24.time24,"13:04:05");
assert.equal(t24.time12,"01:04:05 PM");
assert.equal(t24.displayTime,"13:04:05");
assert.equal(t24.hour24,13);
assert.equal(t24.hour12,1);
assert.equal(t24.minute,4);
assert.equal(t24.second,5);
assert.equal(t24.meridiem,"PM");
assert.equal(t24.localDate,"2026-10-22");
assert.equal(t24.dateLabel,"Thu, 22 Oct 2026");
assert.equal(t24.weekday,"Thu");
assert.equal(t24.month,10);
assert.equal(t24.day,22);
assert.equal(t24.year,2026);
assert.equal(t24.utcOffsetMinutes,-new Date(at).getTimezoneOffset());
assert.match(t24.utcOffsetLabel,/^UTC[+-]\d\d:\d\d$/);

const t12=p.snapshot(at,false);
assert.equal(t12.is24Hour,false);
assert.equal(t12.displayTime,"01:04:05 PM");
assert.equal(t12.time24,t24.time24);
assert.equal(t12.localDate,t24.localDate);
assert.equal(p.snapshot(local(2026,10,22,0,0,0),false).time12,"12:00:00 AM");
assert.equal(p.snapshot(local(2026,10,22,12,0,0),false).time12,"12:00:00 PM");
assert.equal(p.snapshot(local(2026,10,22,23,59,59),false).time12,"11:59:59 PM");
assert.equal(p.snapshot(local(2026,10,22,23,59,59),true).time24,"23:59:59");

const before=p.snapshot(local(2026,12,31,23,59,59),true);
const after=p.snapshot(local(2027,1,1,0,0,0),true);
assert.equal(before.localDate,"2026-12-31");
assert.equal(after.localDate,"2027-01-01");
assert.equal(after.time24,"00:00:00");
assert.equal(after.weekday,"Fri");
assert.equal(p.snapshot(local(2024,2,29,6,7,8),true).localDate,"2024-02-29");

// The zero Unix timestamp is legitimate even if local date is 1969-12-31.
assert.equal(p.snapshot(0,true).state,"ready");
assert.equal(p.snapshot(-1000,true).state,"ready");
assert.equal(p.snapshot(local(1900,2,2),true).state,"ready");
assert.equal(p.snapshot(local(2100,12,31),true).state,"ready");

for(const bad of [null,undefined,"", "0", false, true, {}, [],
                   NaN,Infinity,-Infinity]){
    assert.equal(p.snapshot(bad,true).state,"unavailable",String(bad));
    assert.equal(p.snapshot(bad,true).displayTime,"--:--:--");
}
assert.equal(p.snapshot(at,1).state,"unavailable");
assert.equal(p.snapshot(at,"24").state,"unavailable");
assert.equal(p.snapshot(at,null).state,"unavailable");
assert.equal(p.snapshot(1e20,true).state,"unavailable");
assert.equal(p.snapshot(local(2200,1,1),true).state,"unavailable");
assert.equal(p.snapshot(local(1800,1,1),true).state,"unavailable");

// Domain offset tests cover DST and non-hour-offset civil zones.
if (process.env.TZ === "America/New_York") {
    assert.equal(p.snapshot(local(2026,1,22,12),true).utcOffsetMinutes,-300);
    assert.equal(p.snapshot(local(2026,7,22,12),true).utcOffsetMinutes,-240);
    assert.equal(p.snapshot(local(2026,7,22,12),true).utcOffsetLabel,"UTC-04:00");
    const pre=p.snapshot(Date.UTC(2026,2,8,6,59,59),true);
    const post=p.snapshot(Date.UTC(2026,2,8,7,0,0),true);
    assert.equal(pre.localDate,post.localDate);
    assert.equal(pre.time24,"01:59:59");
    assert.equal(post.time24,"03:00:00");
    assert.equal(pre.utcOffsetMinutes,-300);
    assert.equal(post.utcOffsetMinutes,-240);
    // Fall-back hour repeats, but the UTC offset disambiguates it.
    const fallOne=p.snapshot(Date.UTC(2026,10,1,5,30,0),true);
    const fallTwo=p.snapshot(Date.UTC(2026,10,1,6,30,0),true);
    assert.equal(fallOne.time24,"01:30:00");
    assert.equal(fallTwo.time24,"01:30:00");
    assert.equal(fallOne.utcOffsetMinutes,-240);
    assert.equal(fallTwo.utcOffsetMinutes,-300);
}
if (process.env.TZ === "UTC") {
    assert.equal(t24.utcOffsetMinutes,0);
    assert.equal(t24.utcOffsetLabel,"UTC+00:00");
}
if (process.env.TZ === "Asia/Kathmandu") {
    assert.equal(t24.utcOffsetMinutes,345);
    assert.equal(t24.utcOffsetLabel,"UTC+05:45");
}
if (process.env.TZ === "Pacific/Chatham") {
    assert.equal(t24.utcOffsetMinutes,825);
    assert.equal(t24.utcOffsetLabel,"UTC+13:45");
}

// Snapshot carries no mutable Date instance, timers, IANA guesses, or actions.
const serialized=JSON.stringify(t24);
for(const forbidden of ["setTime", "execute", "process", "timer",
                         "calendarEvent", "timezoneId", "notification"])
    assert.equal(serialized.includes(forbidden),false,forbidden);

console.log("ApolloHub B10 local time, 12/24h, UTC-offset and DST policy passed (TZ="+
            (process.env.TZ||"system")+")");
