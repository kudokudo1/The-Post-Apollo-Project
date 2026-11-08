#!/usr/bin/env node
"use strict";

// M30q // Company-owned implementation of M30i's disposable CI-only
// map-candidate coordinate fix. This tests the actual QML expressions;
// native compositor pairing/render/input authority is OUT OF SCOPE.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const coverage = read("widgets/CompanyCoveragePane.qml");
const company = read("widgets/CompanyNetworkW.qml");
const link = read("widgets/CompanyVectorBridgeLink.qml");
const controller = read("services/company/CompanyVectorSidecarController.qml");

const mapExpression = coverage.match(
    /const origin = Qt\.point\(\s*([^,;]+),\s*([^,;]+)\);/);
const guardedCondition = coverage.match(
    /if \((mapCanvas\.parent !== mapSurface[\s\S]*?column\.rotation !== 0)\)\s*return Qt\.rect\(0, 0, 0, 0\);/);

function hierarchy(offsets) {
    const root = {x:0, y:0, scale:1, rotation:0};
    const column = {parent:root, x:offsets[0][0], y:offsets[0][1],
                    scale:1, rotation:0};
    const mapRow = {parent:column, x:offsets[1][0], y:offsets[1][1],
                    scale:1, rotation:0};
    const mapSurface = {parent:mapRow, x:offsets[2][0], y:offsets[2][1],
                        scale:1, rotation:0};
    const mapCanvas = {parent:mapSurface, x:offsets[3][0], y:offsets[3][1],
                       scale:1, rotation:0};
    return {root, column, mapRow, mapSurface, mapCanvas};
}
function calculate(ancestors) {
    assert.ok(mapExpression, "the real QML computes a Qt.point origin");
    return vm.runInNewContext(
        "({x:" + mapExpression[1] + ", y:" + mapExpression[2] + "})",
        ancestors, {timeout:100});
}
function refused(ancestors) {
    assert.ok(guardedCondition, "the actual QML refuses unsafe item hierarchies");
    return vm.runInNewContext(
        "Boolean(" + guardedCondition[1] + ")", ancestors,
        {timeout:100});
}

test("M30q keeps Coverage candidate in actual Coverage-local coordinates", () => {
    const cases = [
        ["standard",[[0,0],[0,124],[0,0],[1,1]]],
        ["compact",[[0,0],[0,186],[0,0],[1,1]]],
        ["fullscreen",[[0,0],[0,118],[0,0],[1,1]]],
        ["repositioned",[[14,9],[3,180],[2,8],[1,1]]],
        ["fractional",[[3.25,7.5],[1.5,152.75],[0,0],[1.25,1.25]]]
    ];
    for(const [name, offsets] of cases) {
        const refs=hierarchy(offsets);
        assert.equal(refused(refs),false,name+" remains within the exact Item chain");
        const p=calculate(refs);
        const expected=offsets.reduce((acc,xy) =>
            [acc[0]+xy[0],acc[1]+xy[1]], [0,0]);
        assert.equal(p.x,expected[0],name+" x is the sum of Item-local offsets");
        assert.equal(p.y,expected[1],name+" y is the sum of Item-local offsets");
    }
    assert.doesNotMatch(coverage,/mapCanvas\.mapToItem\(root,\s*0,\s*0\)/);
    assert.match(coverage,/VectorViewportPolicy\.within\(candidate,\s*root\.width,\s*root\.height\)/);
    assert.match(coverage,/!mapRow\.visible \|\| !mapSurface\.visible \|\| !mapCanvas\.visible/);
});

test("M30q invalid parent chain or transformed item revokes the candidate", () => {
    for(const item of ["mapCanvas","mapSurface","mapRow","column"]) {
        const refs=hierarchy([[0,0],[0,150],[0,0],[1,1]]);
        refs[item].parent={x:10,y:20};
        assert.equal(refused(refs),true,item+" parent mismatch");
    }
    for(const item of ["mapCanvas","mapSurface","mapRow","column"]) {
        for(const state of [{scale:1.2},{rotation:8}]) {
            const refs=hierarchy([[0,0],[0,150],[0,0],[1,1]]);
            Object.assign(refs[item],state);
            assert.equal(refused(refs),true,item+" transform "+JSON.stringify(state));
        }
    }
    assert.match(coverage,/if \(VectorViewportPolicy\.owner\(/);
    assert.match(coverage,/return Qt\.rect\(0, 0, 0, 0\);/);
});

test("Company root maps Item to scene, not to the PanelWindow QObject", () => {
    assert.match(company,/companyFrame\.mapToItem\(null,\s*0,\s*0\)/);
    assert.doesNotMatch(company,/companyFrame\.mapToItem\(root,\s*0,\s*0\)/);
    assert.match(company,/coverage\.mapToItem\(companyFrame,\s*local\.x,\s*local\.y\)/);
    assert.match(company,/VectorViewportPolicy\.within\(candidate,\s*root\.width,\s*root\.height\)/);
    assert.match(company,/!root\.menuOpen \|\| !companyFrame\.visible/);
});

test("No renderer custody, automatic plugin, network tiles or new child launcher", () => {
    assert.match(company,/property bool vectorBridgeOptIn: false/);
    assert.match(link,/property bool bridgeEnabled: false/);
    assert.match(coverage,/CompanyVectorSidecarController\s*\{/);
    assert.match(controller,/vectorRunner\.command = \["\/usr\/bin\/python3"/);
    assert.match(company,/frameRect:\s*root\.activeVectorFrameInHostRect/);
    assert.match(company,/mapRect:\s*root\.activeVectorViewportRect/);
    for(const file of [company,coverage]) {
        assert.doesNotMatch(file,/\b(?:Process|FileView)\s*\{/);
        assert.doesNotMatch(file,/wl_display_connect|wlr_scene_|wlr_seat_|swaymsg/);
    }
});
