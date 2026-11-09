"use strict";
// Synthetic Trash++ -> Camera handoff. No Quickshell, GIO or real files.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const root = path.resolve(__dirname, "../..");
const cameraSource = fs.readFileSync(path.join(root, "widgets/CameraW.qml"), "utf8");
const trashSource = fs.readFileSync(path.join(root, "modules/Trash.qml"), "utf8");
const shellSource = fs.readFileSync(path.join(root, "shell.qml"), "utf8");

function functionSource(text, name) {
    const start = text.indexOf("    function " + name + "(");
    assert.notEqual(start, -1, "Missing QML function " + name);
    const open = text.indexOf("{", start);
    let depth = 0;
    for (let i = open; i < text.length; i++) {
        if (text[i] === "{") depth++;
        if (text[i] === "}") depth--;
        if (depth === 0) return text.slice(start, i + 1);
    }
    throw new Error("Unbalanced QML function " + name);
}

const changeSource = functionSource(cameraSource, "selectCleanupTechnique");
const handoffSource = functionSource(cameraSource, "openCleanupFromTrash");
const trashRequestSource = functionSource(trashSource, "requestCameraCleanup");
const trashResultSource = functionSource(trashSource, "finishCleanupHandoff");

function cameraHarness(overrides={}) {
    const files = ["/home/example/Pictures/A.png", "/home/example/Pictures/B.jpg"];
    const ctx = {
        busy: false,
        nativeRegionSelecting: false,
        zoomWebBusy: false,
        activeView: "gallery",
        galleryRequestedView: "gallery",
        galleryFiles: [],
        galleryTotal: 2,
        menuOpen: false,
        cleanupTechnique: "batch",
        cleanupCustomFolder: "",
        cleanupLoadedFolder: "",
        cleanupQueueOpen: false,
        batchPaths: files.slice(),
        huntPaused: false,
        huntScoped: true,
        huntHitFlash: true,
        huntShotEffect: {kind:"visual"},
        huntAutoPending: true,
        huntSettingsOpen: true,
        huntPauseMenuOpen: true,
        huntMouseActive: true,
        huntMouseMovingTicks: 2,
        batchPreview: {id: "expired"},
        batchReviewKey: "expired",
        calls: [],
        hideZoomWeb() { ctx.calls.push("hide-zoom"); },
        loadGallery(append, where) {
            ctx.calls.push("scan:" + where);
            ctx.activeView = where;
            ctx.galleryRequestedView = where;
            ctx.busy = true;
            return true;
        },
        Qt: {callLater() {}},
        swipeDeck: {forceActiveFocus() {}},
        ...overrides,
    };
    // QML root id "camera" resolves to the same state for callLater callbacks.
    ctx.camera = ctx;
    vm.createContext(ctx);
    vm.runInContext(changeSource + "\n" + handoffSource, ctx);
    return ctx;
}

test("Trash++ exposes all owner-controlled modes and one live queue count", ()=>{
    assert.match(trashSource, /signal cleanupRequested\(string technique\)/);
    assert.match(trashSource, /cameraCleanupQueueCount: 0/);
    for (const mode of ["batch", "grid", "swipe", "hunt", "desktop", "queue"]) {
        assert.ok(trashSource.includes('{id: "' + mode + '"'));
    }
    assert.match(shellSource, /cameraCleanupQueueCount: cameraWindow\.batchPaths\.length/);
    assert.match(shellSource, /cameraCleanupBusy: cameraWindow\.busy/);
    assert.match(shellSource, /const accepted = cameraWindow\.openCleanupFromTrash\(technique\)/);
    assert.match(shellSource, /trashWindow\.finishCleanupHandoff\(accepted, technique\)/);
});

test("handoff preserves the actual Camera queue and requests one approved scan", ()=>{
    const ctx = cameraHarness();
    const oldQueue = ctx.batchPaths.slice();
    assert.equal(vm.runInContext('openCleanupFromTrash("grid")', ctx), true);
    assert.deepEqual(Array.from(ctx.batchPaths), oldQueue);
    assert.equal(ctx.cleanupTechnique, "grid");
    assert.equal(ctx.menuOpen, true);
    assert.equal(ctx.activeView, "cleanup");
    assert.deepEqual(Array.from(ctx.calls), ["scan:cleanup"]);
    assert.equal(ctx.cleanupQueueOpen, false);
    assert.equal(ctx.feedback.includes("SHARED QUEUE 2"), true);
});

test("VIEW QUEUE retains existing selection and active Swipe mode without rescan", ()=>{
    const ctx=cameraHarness({
        menuOpen:true, activeView:"cleanup", galleryRequestedView:"cleanup",
        cleanupTechnique:"swipe", galleryFiles:[{name:"A.png"}]
    });
    assert.equal(vm.runInContext('openCleanupFromTrash("queue")', ctx), true);
    assert.equal(ctx.cleanupTechnique, "swipe");
    assert.equal(ctx.cleanupQueueOpen, true);
    assert.deepEqual(Array.from(ctx.batchPaths), [
        "/home/example/Pictures/A.png", "/home/example/Pictures/B.jpg"
    ]);
    assert.deepEqual(Array.from(ctx.calls), []);
});

test("Hunt to Batch safely pauses effects without erasing the queue", ()=>{
    const ctx=cameraHarness({
        activeView:"cleanup", menuOpen:true, galleryRequestedView:"cleanup",
        cleanupTechnique:"hunt", galleryFiles:[{name:"A.png"}]
    });
    assert.equal(vm.runInContext('openCleanupFromTrash("batch")', ctx), true);
    assert.equal(ctx.cleanupTechnique, "batch");
    assert.equal(ctx.huntPaused, true);
    assert.equal(ctx.huntScoped, false);
    assert.equal(ctx.huntHitFlash, false);
    assert.equal(ctx.huntAutoPending, false);
    assert.equal(ctx.huntSettingsOpen, false);
    assert.equal(ctx.huntPauseMenuOpen, false);
    assert.equal(ctx.batchReviewKey, "");
    assert.equal(ctx.cleanupQueueOpen, false);
    assert.equal(ctx.batchPaths.length, 2);
    assert.deepEqual(Array.from(ctx.calls), []);
});

test("bad technique and busy/native-capture/zoom states refuse without mutation", ()=>{
    for (const overrides of [
        {busy:true}, {nativeRegionSelecting:true}, {zoomWebBusy:true}
    ]) {
        const ctx=cameraHarness(overrides);
        assert.equal(vm.runInContext('openCleanupFromTrash("hunt")', ctx), false);
        assert.equal(ctx.menuOpen, false);
        assert.equal(ctx.activeView, "gallery");
        assert.equal(ctx.batchPaths.length, 2);
        assert.equal(ctx.calls.length, 0);
    }
    const ctx=cameraHarness();
    assert.equal(vm.runInContext('openCleanupFromTrash("delete-all")', ctx), false);
    assert.equal(ctx.menuOpen, false);
    assert.equal(ctx.calls.length, 0);
});

test("Trash request does not invent deletion authority or close on failed handoff", ()=>{
    assert.doesNotMatch(trashRequestSource, /trashQueuedNow|trashBatch|\\bgio\\b|burn-all/);
    assert.doesNotMatch(handoffSource, /trashQueuedNow|trashBatch|\\bgio\\b|burn-all/);
    assert.match(cameraSource, /function trashQueuedNow\(\)/);
    assert.match(cameraSource, /"trash-batch-now", JSON\.stringify\(batchPaths\)/);
    assert.match(cameraSource, /"MOVE_TO_TRASH", "--folder", cleanupCustomFolder/);
    assert.match(trashResultSource, /if \(accepted !== true\)/);
    assert.match(trashResultSource, /menuOpen = false;/);
    assert.match(trashRequestSource, /activeMode !== "cleanup"/);
    assert.match(trashRequestSource, /cameraCleanupBusy/);
    assert.match(trashRequestSource, /confirmMode !== ""/);
});

function trashHarness(overrides={}) {
    const ctx={
        menuOpen:true,
        busy:false,
        cameraCleanupBusy:false,
        confirmMode:"",
        activeMode:"cleanup",
        status:"",
        requests:[],
        cleanupRequested(mode) { ctx.requests.push(mode); },
        clearConfirmation() {ctx.confirmMode="";},
        ...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(trashRequestSource + "\n" + trashResultSource,ctx);
    return ctx;
}

test("request is read-only, rejects busy/wrong-mode and keeps panel open on failure", ()=>{
    const ctx=trashHarness();
    assert.equal(vm.runInContext('requestCameraCleanup("swipe")',ctx),true);
    assert.deepEqual(Array.from(ctx.requests),["swipe"]);
    assert.equal(ctx.menuOpen,true);
    assert.equal(vm.runInContext('finishCleanupHandoff(false,"swipe")',ctx),false);
    assert.equal(ctx.menuOpen,true);
    assert.match(ctx.status,/CAMERA BUSY OR UNAVAILABLE/);

    const blocked=[
        {busy:true}, {cameraCleanupBusy:true},
        {confirmMode:"all"}, {activeMode:"trash"}, {menuOpen:false}
    ];
    for (const override of blocked) {
        const sample=trashHarness(override);
        assert.equal(vm.runInContext('requestCameraCleanup("hunt")',sample),false);
        assert.equal(sample.requests.length,0);
    }
    assert.equal(vm.runInContext('requestCameraCleanup("burn-all")',ctx),false);
    assert.equal(ctx.requests.length,1);
    assert.equal(vm.runInContext('finishCleanupHandoff(true,"swipe")',ctx),true);
    assert.equal(ctx.menuOpen,false);
});
