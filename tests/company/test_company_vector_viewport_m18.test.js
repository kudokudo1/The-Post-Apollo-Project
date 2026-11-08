#!/usr/bin/env node
"use strict";

// M18 verifies pure geometry policy and QML wiring, not live compositor pairing.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policyFile="widgets/CompanyVectorViewportPolicy.js";
const policy={};
vm.runInNewContext(read(policyFile).replace(/^\s*\.pragma library\s*/,""),policy,
                   {filename:policyFile});
const coverage=read("widgets/CompanyCoveragePane.qml");
const company=read("widgets/CompanyNetworkW.qml");
const controller=read("services/company/CompanyVectorSidecarController.qml");
const launcher=read("services/company/CompanyVectorSidecarLaunch.py");

test("M18 rectangle guard checks true bounds",()=>{
    assert.equal(policy.FORMAT,"post-apollo.company.vector-viewport.m18.v1");
    for(const frame of [
        {x:0,y:0,width:800,height:400},
        {x:1.25,y:3.75,width:175.5,height:127.5},
        {x:799,y:399,width:1,height:1}
    ]) assert.equal(policy.within(frame,800,400),true,JSON.stringify(frame));
    for(const frame of [
        null,undefined,{}, {x:0,y:0,width:0,height:10},
        {x:0,y:0,width:10,height:0},
        {x:0,y:0,width:-10,height:10},
        {x:-1,y:10,width:10,height:10},
        {x:10,y:-1,width:10,height:10},
        {x:700,y:0,width:101,height:10},
        {x:0,y:380,width:10,height:21},
        {x:0,y:0,width:Infinity,height:10},
        {x:NaN,y:0,width:100,height:10},
        {x:0,y:0,width:100,height:NaN}
    ]) assert.equal(policy.within(frame,800,400),false,JSON.stringify(frame));
    assert.equal(policy.within({x:0,y:0,width:10,height:10},0,400),false);
    assert.equal(policy.within({x:0,y:0,width:10,height:10},800,NaN),false);
});

test("only active visible native presentation may publish a candidate",()=>{
    const nominal=[true,true,false,false,false,false,false];
    assert.equal(policy.owner(...nominal),"native");
    for(let index=0;index<nominal.length;index++){
        const state=nominal.slice();
        state[index]=!state[index];
        assert.equal(policy.owner(...state),"none","changed state index "+index);
    }
    assert.equal(policy.owner(true,false,false,false,false,false,false),"none");
});

test("size guards respond to compact, standard and fullscreen host dimensions",()=>{
    const rect={x:100,y:115,width:600,height:240};
    assert.equal(policy.within(rect,800,400),true);
    assert.equal(policy.within(rect,640,400),false);
    assert.equal(policy.within(rect,1280,720),true);
    assert.equal(policy.within({...rect,width:1181},1280,720),false);
    assert.equal(policy.within({...rect,y:510},1280,720),false);
});

test("actual Coverage canvas is the only rectangle source",()=>{
    assert.match(coverage,/import "CompanyVectorViewportPolicy\.js" as VectorViewportPolicy/);
    assert.match(coverage,/readonly property rect activeVectorViewportRect:/);
    assert.match(coverage,/readonly property bool activeVectorViewportValid:/);
    assert.match(coverage,/VectorViewportPolicy\.owner\(\s*root\.visible,\s*vectorController\.running/);
    for(const guard of ["vectorConsentOpen","hubEditorOpen","streetMode",
                        "hubPlacementArmed","streetConsentOpen","mapRow.visible",
                        "mapSurface.visible","mapCanvas.visible"]){
        assert.ok(coverage.includes(guard),guard);
    }
    assert.match(coverage,/column\.x \+ mapRow\.x \+ mapSurface\.x \+ mapCanvas\.x/);
    assert.match(coverage,/column\.y \+ mapRow\.y \+ mapSurface\.y \+ mapCanvas\.y/);
    for (const guard of ["mapCanvas.parent !== mapSurface",
                         "mapSurface.parent !== mapRow",
                         "mapRow.parent !== column",
                         "column.parent !== root",
                         "mapCanvas.scale !== 1",
                         "column.rotation !== 0"])
        assert.ok(coverage.includes(guard),guard);
    assert.doesNotMatch(coverage,/mapCanvas\.mapToItem\(root,\s*0,\s*0\)/);
    assert.match(coverage,/mapCanvas\.width,\s*mapCanvas\.height/);
    assert.match(coverage,/VectorViewportPolicy\.within\(candidate,\s*root\.width,\s*root\.height\)/);
    assert.match(coverage,/id: mapSurface/);
    assert.match(coverage,/id: mapCanvas/);
    assert.match(coverage,/anchors\.margins: 1/);
});

test("Company root republishes candidate only in visible active Coverage mode",()=>{
    assert.match(company,/readonly property rect activeVectorViewportRect:/);
    assert.match(company,/readonly property bool activeVectorViewportValid:/);
    assert.match(company,/!root\.menuOpen \|\| root\.selectedMainModeIndex !== 0/);
    assert.match(company,/!coverageLoader\.active \|\| !coverageLoader\.visible/);
    assert.match(company,/!coverageLoader\.item \|\| !coverageLoader\.item\.visible/);
    assert.match(company,/const local = coverage\.activeVectorViewportRect/);
    assert.match(company,/coverage\.mapToItem\(companyFrame,\s*local\.x,\s*local\.y\)/);
    assert.match(company,/candidate,\s*companyFrame\.width,\s*companyFrame\.height/);
    assert.match(company,/id: coverageLoader/);
    assert.match(company,/CompanyCoveragePane \{ \}/);
    assert.match(company,/property string chassisLevel: "standard"/);
});

test("no compositor input authority or unsafe second process added",()=>{
    for(const source of [coverage,company]) {
        assert.doesNotMatch(source,/\bWatchBridge\s*\{/);
        assert.doesNotMatch(source,/import PostApollo\.StageDirector/);
        assert.doesNotMatch(source,/\bwl_display_connect\b|\bposix_spawn\b/);
        assert.doesNotMatch(source,/\b(?:Process|FileView)\s*\{/);
        assert.doesNotMatch(source,/Qt\.openUrlExternally/);
    }
    assert.match(controller,/vectorRunner\.running=false/);
    assert.match(controller,/Quickshell\.shellPath\("services\/company\/CompanyVectorSidecarLaunch\.py"\)/);
    assert.match(coverage,/vectorController\.stop\(\)/);
    assert.match(coverage,/vectorController\.launch\(online\)/);
    assert.match(coverage,/CompanyStreetMap\s*\{/);
    assert.match(coverage,/\bCanvas\s*\{/);
    assert.match(launcher,/options = \["--styled-online"\] if action == "online" else \[\]/);
});
