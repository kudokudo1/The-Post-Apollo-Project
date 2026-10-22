#!/usr/bin/env node
"use strict";
// Execute the production B9 calendar policy; no QML runtime is needed.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const file=fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubCalendarPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const policy=vm.createContext({});
vm.runInContext(file,policy,{filename:"ApolloHubCalendarPolicy.js"});
const instant=(y,m,d)=>new Date(y,m-1,d,12,30).getTime();
const calendar=(y,m,d,offset=0,first=0)=>
    policy.snapshot(instant(y,m,d),offset,first);

let october=calendar(2026,10,22);
assert.equal(october.state,"ready");
assert.equal(october.source,"local-clock");
assert.equal(october.month,"2026-10");
assert.equal(october.today,"2026-10-22");
assert.equal(october.monthLabel,"October 2026");
assert.equal(october.year,2026);
assert.equal(october.monthNumber,10);
assert.equal(october.daysInMonth,31);
assert.equal(october.weeks,5);
assert.equal(october.cells.length,35);
assert.equal(october.cells[0].date,"2026-09-27"); // Sunday first
assert.equal(october.cells[0].inMonth,false);
assert.equal(october.cells[4].date,"2026-10-01");
assert.equal(october.cells[4].inMonth,true);
assert.equal(october.cells[0].column,0);
assert.equal(october.cells[7].row,1);
assert.equal(october.cells[0].weekday,0);
assert.equal(october.cells.filter(x=>x.isToday).length,1);
assert.equal(october.cells.find(x=>x.isToday).date,"2026-10-22");
assert.equal(october.cells.filter(x=>x.inMonth).length,31);
assert.equal(october.weekdayLabels[0],"SUN");
assert.equal(october.weekdayLabels[6],"SAT");
assert.equal(october.eventsState,"not-connected");
assert.equal(october.eventCount,-1);
assert.equal(Object.keys(october).includes("events"),false);

const monday=calendar(2026,10,22,0,1);
assert.equal(monday.weekStartsOn,1);
assert.equal(monday.weekdayLabels[0],"MON");
assert.equal(monday.weekdayLabels[6],"SUN");
assert.equal(monday.cells[0].date,"2026-09-28");
assert.equal(monday.cells[0].weekday,1);
assert.equal(monday.cells.filter(x=>x.isToday).length,1);

const before=calendar(2026,1,2,-1);
assert.equal(before.month,"2025-12");
assert.equal(before.today,"2026-01-02");
// Today may be a trailing adjacent-month cell; that cell is not inMonth.
assert.equal(before.cells.some(x=>x.isToday),true);
assert.equal(before.cells.find(x=>x.isToday).date,"2026-01-02");
assert.equal(before.cells.find(x=>x.isToday).inMonth,false);
const next=calendar(2026,12,31,1);
assert.equal(next.month,"2027-01");
assert.equal(next.today,"2026-12-31");
assert.equal(next.cells.filter(x=>x.inMonth).length,31);
assert.equal(calendar(2026,5,10,-120).month,"2016-05");
assert.equal(calendar(2026,5,10,120).month,"2036-05");

const febLeap=calendar(2024,2,29);
assert.equal(febLeap.daysInMonth,29);
assert.equal(febLeap.cells.filter(x=>x.inMonth).length,29);
assert.equal(febLeap.cells.filter(x=>x.isToday).length,1);
assert.equal(calendar(2000,2,20).daysInMonth,29);
assert.equal(calendar(1900,2,20).daysInMonth,28);
assert.equal(calendar(2025,2,20).daysInMonth,28);
const four=calendar(2021,2,1,0,1);
assert.equal(four.weeks,4);
assert.equal(four.cells.length,28);
assert.equal(four.cells[0].date,"2021-02-01");
const six=calendar(2020,8,3);
assert.equal(six.weeks,6);
assert.equal(six.cells.length,42);
assert.equal(six.cells[0].date,"2020-07-26");
assert.equal(six.cells[41].date,"2020-09-05");
for(const output of [october,monday,before,next,febLeap,four,six]){
    assert.equal(output.weekdayLabels.length,7);
    assert.equal(output.cells.length,output.weeks*7);
    assert.equal(output.eventCount,-1);
    assert.equal(output.eventsState,"not-connected");
    assert.equal(output.cells.filter(x=>x.inMonth).length,output.daysInMonth);
    const dates=output.cells.map(x=>x.date);
    assert.equal(new Set(dates).size,dates.length);
}

// Preserve calendar dates across DST in March/November: UTC arithmetic
// is only used for civil-cell increments, never as the user's local date.
for(const date of [[2026,3,8],[2026,11,1],[2024,3,10],[2024,11,3]]){
    const result=calendar(...date);
    const dateKey=String(date[0])+"-"+String(date[1]).padStart(2,"0")
        +"-"+String(date[2]).padStart(2,"0");
    assert.equal(result.today,dateKey);
    assert.equal(result.cells.filter(x=>x.isToday).length,1);
    for(let i=1;i<result.cells.length;i++){
        const previous=Date.parse(result.cells[i-1].date+"T00:00:00Z");
        const current=Date.parse(result.cells[i].date+"T00:00:00Z");
        assert.equal(current-previous,86400000);
    }
}

for(const invalid of [
    [null,0,0],["",0,0],["2026",0,0],[undefined,0,0],
    [NaN,0,0],[Infinity,0,0],[0,0,0],
    [instant(2026,10,22),121,0],[instant(2026,10,22),-121,0],
    [instant(2026,10,22),1.2,0],[instant(2026,10,22),"1",0],
    [instant(2026,10,22),0,2],[instant(2026,10,22),0,"0"],
    [instant(1800,10,22),0,0],[instant(2200,10,22),0,0],
]){
    const output=policy.snapshot(...invalid);
    assert.equal(output.state,"unavailable",String(invalid));
    assert.equal(output.cells.length,0);
    assert.equal(output.eventsState,"not-connected");
    assert.equal(output.eventCount,-1);
}
assert.equal(calendar(2026,1,2,0,0).cells.some(x=>x.isToday),true);
console.log("ApolloHub B9 local calendar civil-grid and DST policy tests passed");
