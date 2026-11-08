#!/usr/bin/env node
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");

const company = read("widgets/CompanyNetworkW.qml");
const coverage = read("widgets/CompanyCoveragePane.qml");
const link = read("widgets/CompanyVectorBridgeLink.qml");
const ctl = read("services/company/CompanyVectorSidecarController.qml");
const pure = read("widgets/CompanyVectorViewportPolicy.js");
const policy = {};
vm.runInNewContext(pure.replace(/^\s*\.pragma library\s*/, ""), policy);

test("M26 does not require M25's Qt plugin for ordinary Company startup", () => {
    assert.match(company, /property bool vectorBridgeOptIn:\s*false/);
    assert.match(link, /property bool bridgeEnabled:\s*false/);
    assert.match(link, /if \(!bridgeEnabled \|\| bridgeObject !== null\)/);
    assert.match(link, /Qt\.createQmlObject\(/);
    assert.match(link, /import PostApollo\.CompanyVector 1\.0/);
    assert.match(link, /status = "OPTIONAL_BRIDGE_UNAVAILABLE"/);
    assert.match(link, /catch \(error\)/);
    assert.doesNotMatch(company, /^\s*import PostApollo\.CompanyVector/m);
    assert.doesNotMatch(link, /^\s*import PostApollo\.CompanyVector/m);
    assert.match(company, /CompanyVectorBridgeLink\s*\{/);
    assert.match(company, /bridgeEnabled:\s*root\.vectorBridgeOptIn/);
    assert.match(link, /Component\.onDestruction: detachBridge\(\)/);
    assert.doesNotMatch(company + coverage + link,
        /(?:^|\n)\s*(?:Process|FileView)\s*\{/);
    assert.doesNotMatch(company + coverage + link,
        /wl_display_connect|wl_display_disconnect|Qt\.openUrlExternally/);
});

test("M26 uses real panel and map rectangles in distinct coordinate frames", () => {
    assert.match(company, /readonly property rect activeVectorFrameInHostRect:/);
    assert.match(company, /companyFrame\.mapToItem\(null,\s*0,\s*0\)/);
    assert.doesNotMatch(company, /companyFrame\.mapToItem\(root,\s*0,\s*0\)/);
    assert.match(company, /companyFrame\.width,\s*companyFrame\.height/);
    assert.match(company, /VectorViewportPolicy\.within\(candidate,\s*root\.width,\s*root\.height\)/);
    assert.match(company, /frameRect:\s*root\.activeVectorFrameInHostRect/);
    assert.match(company, /mapRect:\s*root\.activeVectorViewportRect/);
    assert.match(company, /!root\.menuOpen \|\| !companyFrame\.visible/);
    assert.match(coverage, /column\.x \+ mapRow\.x \+ mapSurface\.x \+ mapCanvas\.x/);
    assert.match(coverage, /mapCanvas\.parent !== mapSurface/);
    assert.match(company, /coverage\.mapToItem\(companyFrame,\s*local\.x,\s*local\.y\)/);
    assert.match(link, /object\.frameRect = frameRect/);
    assert.match(link, /object\.mapRect = mapRect/);

    const host = {x:12,y:9,width:976,height:679};
    const inner = {x:200,y:110,width:650,height:450};
    assert.equal(policy.within(host,1000,700),true);
    assert.equal(policy.within(inner,host.width,host.height),true);
    const actual = {x:host.x+inner.x,y:host.y+inner.y,
                    width:inner.width,height:inner.height};
    assert.equal(policy.within(actual,1000,700),true);
    assert.equal(policy.within({...host,width:999},1000,700),false);
    assert.equal(policy.within({...inner,x:500},host.width,host.height),false);
});

test("real existing user launch and close actions remain the only source of intent", () => {
    assert.match(coverage, /signal nativeVectorLaunchRequested\(bool online\)/);
    assert.match(coverage, /signal nativeVectorClosed\(\)/);
    assert.match(coverage, /onTriggered: root\.launchVector\(false\)/);
    assert.match(coverage, /onTriggered: root\.launchVector\(true\)/);
    assert.match(coverage, /if \(vectorController\.launch\(online\)\)\s*root\.nativeVectorLaunchRequested\(online\)/);
    assert.match(coverage, /onRunningChanged: if \(!running\) root\.nativeVectorClosed\(\)/);
    assert.match(coverage, /vectorController\.stop\(\)/);
    assert.match(company, /target:\s*coverageLoader\.item/);
    assert.match(company, /function onNativeVectorLaunchRequested\(online\)/);
    assert.match(company, /vectorBridgeLink\.requestIntent\(online\)/);
    assert.match(company, /function onNativeVectorClosed\(\)/);
    assert.match(company, /vectorBridgeLink\.closeIntent\(\)/);
    assert.match(link, /if \(!bridgeEnabled \|\| !object \|\| !object\.wireBound\)/);
    assert.match(link, /return object\.requestLaunch\(Boolean\(online\)\)/);
    assert.match(link, /object\.close\(\)/);
    assert.match(ctl, /vectorRunner\.command = \["\/usr\/bin\/python3"/);
    assert.match(ctl, /Quickshell\.shellPath\("services\/company\/CompanyVectorSidecarLaunch\.py"\)/);
    assert.match(ctl, /vectorRunner\.running=true/);
    assert.match(ctl, /vectorRunner\.running=false/);
});

test("no Weather pairing, actor custody, seat control, or claim of embedded map", () => {
    const combined = company + coverage + link;
    assert.doesNotMatch(combined, /import PostApollo\.StageDirector/);
    assert.doesNotMatch(combined, /\bWatchBridge\s*\{/);
    assert.doesNotMatch(combined, /stage_director_company_map_probe\(/);
    assert.doesNotMatch(combined, /wlr_scene_|wlr_seat_|swaymsg|posix_spawn/);
    assert.match(link, /existing Company operational/);
    assert.match(link, /failure must not suppress or replace the M15 launcher/i);
    assert.match(company, /WlrLayershell\.namespace:\s*"post-apollo-company-network"/);
    assert.match(company, /WlrLayershell\.keyboardFocus:\s*\n\s*menuOpen \? WlrKeyboardFocus\.OnDemand : WlrKeyboardFocus\.None/);
    assert.match(coverage, /labelText: vectorController\.running \? "CLOSE VECTOR" : "VECTOR VIEW ▸"/);
});
