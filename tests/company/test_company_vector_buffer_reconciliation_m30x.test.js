#!/usr/bin/env node
"use strict";

// Company M30x: compare two separately measured allocations; do NOT grant
// native-host or compositor authority from caller-supplied metadata.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const policy = fs.readFileSync(path.join(root,
    "widgets/CompanyVectorBufferReconciliation.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*\n/, ""),
    context, {timeout: 1000, filename: "CompanyVectorBufferReconciliation.js"});

const witnessed = () => ({
    allocationKind: "SHM",
    fourcc: "0x36314752",
    physicalWidth: 1494,
    physicalHeight: 788,
    strideBytes: 2988,
    planeCount: 1,
    scale: 1,
    transform: 0,
    modifier: null
});
const compare = (w, h, b) =>
    JSON.parse(JSON.stringify(context.compare(w, h, b)));

test("M30x exact observed imported SHM RGB565 is not Qt CPU RGBA", () => {
    const r = compare(1493, 788, witnessed());
    assert.equal(r.status, "MATCHES_RECORDED_CI_PROFILE_ONLY");
    assert.equal(r.schema,
        "post-apollo.company.vector-native-buffer-reconciliation.m30x.v1");
    assert.equal(r.sourceProof, "SwayPX-M30w-CI-42513247422");
    assert.equal(r.evidenceScope, "ONE_HEADLESS_MESA_WAYLAND_TEST");
    assert.equal(r.metadataTrust, "CALLER_SUPPLIED_NOT_AUTHENTICATED");
    assert.equal(r.visibleWidth, 1493);
    assert.equal(r.visibleHeight, 788);
    assert.equal(r.nativePhysicalWidth, 1494);
    assert.equal(r.nativePhysicalHeight, 788);
    assert.equal(r.rightCropColumns, 1);
    assert.equal(r.nativePixelFormat, "RGB565");
    assert.equal(r.nativeBytesPerPixel, 2);
    assert.equal(r.nativeStrideBytes, 2988);
    assert.equal(r.qtCpuReadbackStrideBytesReference, 5976);
    assert.equal(r.cpuReadbackIsNativeAllocation, false);
    assert.equal(r.m30uFourByteEightByteModelIsNativeEvidence, false);
    assert.equal(r.originalUnpaddedNativeStrideBytes, null);
    assert.equal(r.actualFedoraBufferProfileVerified, false);
    assert.equal(r.universalStrideAlignmentVerified, false);
    for(const key of ["productionAuthority", "selectedNativeActorAuthorized",
                      "sceneAuthority", "inputAuthority"])
        assert.equal(r[key], false, key);
});

test("M30x refuses untested logical canvases and invented native row pitch", () => {
    for(const dims of [[1492,788], [1494,788], [1493,787],
                       [1493,789], [1493.0,788.1], ["1493",788],
                       [null,788], [1493,undefined], [Infinity,788]]) {
        const r = compare(dims[0],dims[1],witnessed());
        assert.equal(r.status,"REFUSED",String(dims));
        assert.equal(r.reason,"VISIBLE_GEOMETRY_NOT_TESTED");
        assert.equal(r.productionAuthority,false);
    }
    for (const stride of [2986, 2992, 5976, "2988", null, 0, NaN]) {
        const r = compare(1493,788,{...witnessed(),strideBytes:stride});
        assert.equal(r.reason,"NATIVE_STRIDE_MISMATCH",String(stride));
    }
});

test("M30x refuses changed allocation/format, unknown metadata and actor claims", () => {
    for (const value of [null, undefined, [], "SHM", 2988, {}]) {
        const r = compare(1493,788,value);
        assert.equal(r.status,"REFUSED");
        assert.equal(r.productionAuthority,false);
    }
    for (const change of [
        {allocationKind:"DMABUF"}, {allocationKind:"RGBA"},
        {fourcc:"0x34325241"}, {fourcc:"RGB565"},
        {fourcc:0x36314752}, {fourcc:"0x36314752",allocationKind:"DMABUF"},
        {physicalWidth:1493}, {physicalWidth:1495},
        {physicalHeight:789}, {planeCount:2}, {planeCount:0},
        {scale:2}, {scale:1.25}, {transform:1},
        {modifier:0}, {modifier:"INVALID"}
    ]) {
        const r = compare(1493,788,{...witnessed(),...change});
        assert.equal(r.status,"REFUSED",JSON.stringify(change));
        assert.equal(r.productionAuthority,false);
        assert.equal(r.selectedNativeActorAuthorized,false);
        assert.equal(r.sceneAuthority,false);
        assert.equal(r.inputAuthority,false);
    }
});

test("M30x compares evidence without changing Company, Qt child or SwayPX", () => {
    const company = fs.readFileSync(path.join(root,
        "widgets/CompanyNetworkW.qml"),"utf8");
    const sidecar = fs.readFileSync(path.join(root,
        "services/company/CompanyVectorSidecarController.qml"),"utf8");
    const m30u = fs.readFileSync(path.join(root,
        "widgets/CompanyVectorPhysicalBackingPolicy.js"),"utf8");
    assert.match(company,/property bool vectorBridgeOptIn: false/);
    assert.match(sidecar,/signal nativeChildStarted\(int pid\)/);
    assert.match(m30u,/Explicit 4-bytes-per-pixel, 8-byte-alignment/);
    assert.doesNotMatch(company,/CompanyVectorBufferReconciliation/);
    assert.doesNotMatch(policy,/import Quickshell|import PostApollo|Qt\.createQmlObject/);
    assert.doesNotMatch(policy,/QProcess|swaymsg|execv|network|Qt\.openUrlExternally/);
    assert.match(policy,/productionAuthority: false/);
    assert.match(policy,/originalUnpaddedNativeStrideBytes: null/);
});
