#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(path.join(root,
    "widgets/weather/StationTerminalGeometry.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const context = {};
vm.runInNewContext(source, context);
const plain = x => JSON.parse(JSON.stringify(x));

const gapConfig = [
    "output * bg /tmp/night.png fill",
    "gaps inner 8px", "gaps outer 5px", "gaps top 1px"
].join("\n");
const gaps = context.parseSwayTopGaps(gapConfig);
assert.deepEqual(plain(gaps), {inner: 8, top: 1});
assert.deepEqual(plain(context.parseSwayTopGaps(
    "gaps inner 8px\ngaps outer 5px\n")), {inner:8, top:5});
assert.equal(context.parseSwayTopGaps("gaps top 1px"), null);
assert.equal(context.parseSwayTopGaps(null), null);

const outputs = [
    {name:"DP-3",active:true,
     rect:{x:0,y:0,width:2560,height:1440}},
    {name:"HDMI-A-1",active:true,
     rect:{x:2560,y:0,width:1360,height:768}}
];
const workspaces = [
    {output:"DP-3",visible:true,
     rect:{x:13,y:82,width:2534,height:1345}},
    {output:"HDMI-A-1",visible:true,
     rect:{x:2573,y:9,width:1334,height:746}}
];
function offset(name, ws=workspaces, gap=gaps, os=outputs) {
    return context.reservedTopInset(os,ws,name,gap);
}
function target(name,top) {
    return context.position(outputs,name,1000,20,62,160,8,74,824,494,top);
}
assert.equal(offset("DP-3"),73);
assert.equal(offset("HDMI-A-1"),0);
assert.deepEqual(plain(target("DP-3",offset("DP-3"))),
    {x:1708,y:209,width:824,height:494});
assert.deepEqual(plain(target("HDMI-A-1",offset("HDMI-A-1"))),
    {x:3068,y:136,width:824,height:494});
assert.equal(target("DP-3",undefined).y,136);
assert.equal(target("DP-3",-1),null);
assert.equal(target("DP-3",2000),null);
assert.equal(offset("DP-5"),null);
assert.equal(offset("DP-3",[]),null);
assert.equal(offset("DP-3",workspaces,null),null);
assert.equal(offset("DP-3",[{output:"DP-3",visible:true,
    rect:{x:13,y:7,width:2534,height:1345}}]),null);
// Negative output origin must not inherit a primary-monitor reserved inset.
const negativeOutput=[{name:"HDMI-A-1",active:true,
    rect:{x:-1360,y:200,width:1360,height:768}}];
const negativeWorkarea=[{output:"HDMI-A-1",visible:true,
    rect:{x:-1347,y:209,width:1334,height:746}}];
assert.equal(offset("HDMI-A-1",negativeWorkarea,gaps,negativeOutput),0);
assert.deepEqual(plain(context.position(negativeOutput,"HDMI-A-1",
    1000,20,62,160,8,74,824,494,0)),
    {x:-852,y:336,width:824,height:494});

// Contract: preserve exact app-ID scoping and bounded adjustment. No generic
// kitty process targeting, extra animation-frame poller or Weather bay shift.
const terminal=fs.readFileSync(path.join(root,
    "widgets/weather/StationTerminal.qml"),"utf8");
const station=fs.readFileSync(path.join(root,
    "widgets/weather/WeatherStationW.qml"),"utf8");
assert.match(terminal,/get_workspaces/);
assert.match(terminal,/get_config/);
assert.match(terminal,/parseSwayTopGaps/);
assert.match(terminal,/reservedTopInset/);
assert.match(terminal,/terminalBay\.height,\s*topInset/);
assert.match(terminal,/interval:\s*15000/);
assert.match(terminal,/fitResizeRetries\s*<\s*1/);
assert.match(terminal,/!terminalView\.fitCenterAttempted/);
assert.match(terminal,/terminalAppId/);
assert.match(station,/exclusiveZone:\s*0/);
console.log("Weather Station Sway workarea and Kitty geometry: PASS");
