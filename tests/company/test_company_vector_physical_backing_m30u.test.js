#!/usr/bin/env node
"use strict";

// M30u is an isolated arithmetic contract, not runtime selected-host
// admission. It never runs MapLibre, opens user records, or starts a Qt child.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const policySource = fs.readFileSync(path.join(root,
    "widgets/CompanyVectorPhysicalBackingPolicy.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*\n/, ""),
    context, {timeout:1000,filename:"CompanyVectorPhysicalBackingPolicy.js"});
const choose = (width,height,bpp=4,alignment=8) =>
    JSON.parse(JSON.stringify(context.candidate(width,height,bpp,alignment)));

test("M30u exact M30t fullscreen source: 1493 canvas -> 1494 physical",()=>{
    const result=choose(1493,788);
    assert.equal(result.status,"CANDIDATE_ONLY");
    assert.equal(result.schema,
        "post-apollo.company.vector-physical-backing.m30u.v1");
    assert.equal(result.evidenceLevel,"EXACT_CI_OBSERVATION");
    assert.equal(result.sourceProof,"SwayPX-M30t-CI-20261108");
    assert.equal(result.logicalWidth,1493);
    assert.equal(result.logicalHeight,788);
    assert.equal(result.physicalWidth,1494);
    assert.equal(result.physicalHeight,788);
    assert.equal(result.rightCropColumns,1);
    assert.equal(result.calculatedStrideBytes,5976);
    assert.deepEqual(result.visibleRect,{
        x:0,y:0,width:1493,height:788
    });
    assert.equal(result.productionAuthority,false);
    assert.equal(result.candidateOnly,true);
});

test("M30u parity arithmetic is consistent but never generalized as measured evidence",()=>{
    const cases=[
        [1492,1492,0,5968],
        [1493,1494,1,5976],
        [1494,1494,0,5976],
        [1495,1496,1,5984],
        [1496,1496,0,5984],
        [840,840,0,3360],
        [573,574,1,2296],
        [441,442,1,1768],
        [1920,1920,0,7680],
        [1,2,1,8],
        [2,2,0,8],
        [4095,4096,1,16384],
        [4096,4096,0,16384]
    ];
    for(const [width,backing,pad,stride] of cases) {
        const result=choose(width,Math.min(788,2160));
        assert.equal(result.status,"CANDIDATE_ONLY",String(width));
        assert.equal(result.physicalWidth,backing,String(width));
        assert.equal(result.rightCropColumns,pad,String(width));
        assert.equal(result.calculatedStrideBytes,stride,String(width));
        assert.equal(result.calculatedStrideBytes%8,0,String(width));
        assert.equal(result.visibleRect.width,width,String(width));
        assert.equal(result.productionAuthority,false,String(width));
        if(width!==1493)
            assert.equal(result.evidenceLevel,
                "ARITHMETIC_ONLY_UNVERIFIED_FOR_REAL_RENDERER",
                String(width));
    }
});

test("M30u must refuse unknown dimensions, types and pixel pitch",()=>{
    for(const [w,h] of [
        [0,788],[-1,788],[1493,0],[1493,-788],
        [4097,788],[1493,2161],[4096.01,788],
        [1493,787.9],["1493",788],[1493,"788"],
        [NaN,788],[Infinity,788],[1493,Infinity],
        [null,788],[1493,undefined]
    ]) {
        const result=choose(w,h);
        assert.equal(result.status,"REFUSED",
            "unsafe dimensions "+String(w)+","+String(h));
        assert.equal(result.reason,"INVALID_OR_UNSUPPORTED_VIEWPORT");
        assert.equal(result.productionAuthority,false);
    }
    for(const [bpp,align] of [
        [1,8],[2,8],[3,8],[8,8],[4,0],[4,4],
        [4,16],[4,32],["4",8],[4,"8"],[undefined,8],
        [4,null]
    ]) {
        const result=choose(1493,788,bpp,align);
        assert.equal(result.status,"REFUSED",
            "unknown pixel layout "+String(bpp)+","+String(align));
        assert.equal(result.reason,"UNVERIFIED_BUFFER_FORMAT_OR_ROW_ALIGNMENT");
        assert.equal(result.productionAuthority,false);
    }
});

test("M30u no new authority, plugin load, child launcher or runtime mutation",()=>{
    const company=fs.readFileSync(path.join(root,
        "widgets/CompanyNetworkW.qml"),"utf8");
    const bridge=fs.readFileSync(path.join(root,
        "widgets/CompanyVectorBridgeLink.qml"),"utf8");
    const sidecar=fs.readFileSync(path.join(root,
        "services/company/CompanyVectorSidecarController.qml"),"utf8");
    assert.match(company,/property bool vectorBridgeOptIn: false/);
    assert.match(bridge,/property bool bridgeEnabled: false/);
    assert.match(sidecar,/signal nativeChildStarted\(int pid\)/);
    assert.match(sidecar,/vectorRunner\.command = \["\/usr\/bin\/python3"/);
    assert.doesNotMatch(policySource,/Qt\.createQmlObject|Qt\.openUrlExternally|\.running\s*=|swaymsg|execv\s*\(/);
    assert.doesNotMatch(policySource,/import PostApollo|import Quickshell/);
    assert.match(policySource,/productionAuthority:\s*false/);
    assert.match(policySource,/EXACT_CI_OBSERVATION/);
    assert.match(policySource,/ARITHMETIC_ONLY_UNVERIFIED_FOR_REAL_RENDERER/);
});
