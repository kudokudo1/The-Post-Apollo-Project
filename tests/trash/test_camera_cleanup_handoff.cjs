"use strict";
// Synthetic Trash++ HOSTED Cleanup test: no Quickshell, GIO, or user files.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const root = path.resolve(__dirname, "../..");
const cameraSource = fs.readFileSync(path.join(root, "widgets/CameraW.qml"), "utf8");
const cleanupSource = fs.readFileSync(path.join(root, "widgets/CameraCleanupView.qml"), "utf8");
const trashSource = fs.readFileSync(path.join(root, "modules/Trash.qml"), "utf8");
const shellSource = fs.readFileSync(path.join(root, "shell.qml"), "utf8");

function method(source, name) {
    const start = source.indexOf("    function " + name + "(");
    assert.notEqual(start, -1, "Missing method: " + name);
    const open = source.indexOf("{", start);
    let depth = 0;
    for (let i = open; i < source.length; i++) {
        if (source[i] === "{") depth++;
        if (source[i] === "}") depth--;
        if (depth === 0) return source.slice(start, i+1);
    }
    throw new Error("Unbalanced method: " + name);
}
const sourceMethods = [
    method(cameraSource,"selectCleanupTechnique"),
    method(cameraSource,"openCleanupFromTrash"),
    method(cameraSource,"suspendHostedCleanup")
].join("\n");
const trashMethods = [
    method(trashSource,"setMode"),
    method(trashSource,"requestCameraCleanup")
].join("\n");

function cameraHarness(overrides={}) {
    const ctx = {
        busy: false,
        nativeRegionSelecting: false,
        zoomWebBusy: false,
        activeView: "gallery",
        galleryRequestedView: "gallery",
        galleryFiles: [],
        galleryTotal: 0,
        menuOpen: false,
        hostedCleanupActive: true,
        hostedCleanupSurface: {focusSwipe(){}},
        cleanupTechnique: "batch",
        cleanupCustomFolder: "",
        cleanupLoadedFolder: "",
        cleanupQueueOpen: false,
        batchPaths: ["/tmp/sample-a.png", "/tmp/sample-b.png"],
        huntPaused: false,
        huntScoped: true,
        huntHitFlash: true,
        huntShotEffect: {kind:"visual"},
        huntAutoPending: true,
        huntSettingsOpen: true,
        huntPauseMenuOpen: true,
        huntMouseActive: true,
        huntMouseMovingTicks: 2,
        batchPreview: {id:"expired"},
        batchReviewKey: "expired",
        calls: [],
        Qt:{callLater(){}},
        hideZoomWeb(){ctx.calls.push("hide-zoom");},
        loadGallery(_append,view) {
            ctx.calls.push("scan:"+view);
            ctx.activeView = view;
            ctx.galleryRequestedView = view;
            ctx.busy = true;
            return true;
        },
        ...overrides
    };
    ctx.camera = ctx;
    vm.createContext(ctx);
    vm.runInContext(sourceMethods,ctx);
    return ctx;
}

function trashHarness(overrides={}) {
    const camera=overrides.cameraCleanupController || {
        calls:[],
        openCleanupFromTrash(mode) {this.calls.push(mode);return true;},
        suspendHostedCleanup(){this.calls.push("suspend");}
    };
    const ctx={
        menuOpen:true,
        activeMode:"trash",
        lifecycleModes:["cleanup","archive","trash","burn"],
        busy:false,
        researchBusy:false,
        researchBurnId:"",
        burnUiStage:"",
        cameraCleanupBusy:false,
        confirmMode:"",
        cameraCleanupController:camera,
        status:"",
        archiveRefreshCalls:0,
        researchRefreshCalls:0,
        refreshArchive(){ctx.archiveRefreshCalls++;return true;},
        refreshResearch(){ctx.researchRefreshCalls++;return true;},
        Qt:{callLater(fn){fn();}},
        ...overrides
    };
    // QML root id is available by name inside Qt.callLater callbacks.
    ctx.trashLauncher = ctx;
    vm.createContext(ctx);
    vm.runInContext(trashMethods,ctx);
    return ctx;
}

test("Cleanup UI physically moved: Camera no longer renders or links its Cleanup tab",()=>{
    assert.doesNotMatch(cameraSource, /id: cleanupPage/);
    assert.doesNotMatch(cameraSource, /\{id: "cleanup", label: "CLEANUP"\}/);
    assert.match(cameraSource,/\{id: "capture", label: "CAPTURE"\}/);
    assert.match(cameraSource,/\{id: "gallery", label: "GALLERY"\}/);
    assert.match(cameraSource,/\{id: "zoom", label: "ZOOM"\}/);
    assert.match(cleanupSource,/id: cleanupPage/);
    for(const id of ["cleanupBatchView","cleanupGridView","cleanupSwipeView",
                     "cleanupHuntView","cleanupDesktopView","cleanupQueueView"]) {
        assert.ok(cleanupSource.includes("id: "+id),id);
    }
    assert.match(trashSource,/CameraCleanupView \{/);
    assert.match(trashSource,/id: cleanupViewLoader/);
    assert.match(trashSource,/camera: trashLauncher.cameraCleanupController/);
    assert.match(trashSource,/readonly property var cleanupContentView: cleanupViewLoader.item/);
    assert.match(shellSource,/cameraCleanupController: cameraWindow/);
    assert.match(shellSource,/hostedCleanupActive: trashWindow.menuOpen/);
    assert.match(shellSource,/hostedCleanupSurface: trashWindow.cleanupContentView/);
    assert.doesNotMatch(shellSource,/onCleanupRequested:/);
    assert.doesNotMatch(trashSource,/signal cleanupRequested/);
});

test("Camera remains single backend; hosted mode never opens Camera panel",()=>{
    const ctx=cameraHarness();
    const oldQueue=ctx.batchPaths.slice();
    assert.equal(vm.runInContext('openCleanupFromTrash("grid")',ctx),true);
    assert.equal(ctx.menuOpen,false);
    assert.equal(ctx.activeView,"cleanup");
    assert.equal(ctx.cleanupTechnique,"grid");
    assert.deepEqual(Array.from(ctx.batchPaths),oldQueue);
    assert.deepEqual(Array.from(ctx.calls),["scan:cleanup"]);
    assert.equal(ctx.cleanupQueueOpen,false);
    assert.match(ctx.feedback,/SHARED QUEUE 2/);
});

test("VIEW QUEUE uses existing shared Camera selection without cloning it",()=>{
    const ctx=cameraHarness({
        activeView:"cleanup",galleryRequestedView:"cleanup",
        galleryFiles:[{name:"A.png"}],cleanupTechnique:"swipe"
    });
    const before=ctx.batchPaths;
    assert.equal(vm.runInContext('openCleanupFromTrash("queue")',ctx),true);
    assert.equal(ctx.cleanupQueueOpen,true);
    assert.equal(ctx.cleanupTechnique,"swipe");
    assert.equal(ctx.batchPaths,before);
    assert.deepEqual(Array.from(ctx.calls),[]);
    assert.match(cleanupSource,/onLeftClicked: camera.trashQueuedNow\(\)/);
    assert.match(cameraSource,/"trash-batch-now", JSON.stringify\(batchPaths\)/);
});

test("Hunt pauses on mode change and Trash close without deleting queue entries",()=>{
    const ctx=cameraHarness({
        activeView:"cleanup",galleryRequestedView:"cleanup",
        galleryFiles:[{name:"A.png"}],cleanupTechnique:"hunt"
    });
    assert.equal(vm.runInContext('openCleanupFromTrash("batch")',ctx),true);
    assert.equal(ctx.huntPaused,true);
    assert.equal(ctx.huntScoped,false);
    assert.equal(ctx.huntAutoPending,false);
    assert.equal(ctx.batchPaths.length,2);
    ctx.huntPaused=false;
    vm.runInContext('suspendHostedCleanup()',ctx);
    assert.equal(ctx.huntPaused,true);
    assert.equal(ctx.huntShotEffect,null);
    assert.equal(ctx.batchPaths.length,2);
    assert.match(cleanupSource,/running: camera.hostedCleanupActive && camera.huntAutoRounds/);
    assert.match(cleanupSource,/running: camera.hostedCleanupActive\s+&& camera.activeView/);
});

test("Camera refuses invalid or unsafe hosted requests without scanning/deleting",()=>{
    for(const override of [
        {busy:true},{nativeRegionSelecting:true},{zoomWebBusy:true}
    ]) {
        const ctx=cameraHarness(override);
        assert.equal(vm.runInContext('openCleanupFromTrash("hunt")',ctx),false);
        assert.deepEqual(Array.from(ctx.calls),[]);
        assert.equal(ctx.menuOpen,false);
        assert.equal(ctx.batchPaths.length,2);
    }
    const ctx=cameraHarness();
    assert.equal(vm.runInContext('openCleanupFromTrash("burn-all")',ctx),false);
    assert.deepEqual(Array.from(ctx.calls),[]);
});

test("Trash changes mode IN PLACE and does not hand off to Camera window",()=>{
    const ctx=trashHarness();
    assert.equal(vm.runInContext('setMode("cleanup")',ctx),true);
    assert.equal(ctx.activeMode,"cleanup");
    assert.deepEqual(Array.from(ctx.cameraCleanupController.calls),["batch"]);
    assert.equal(vm.runInContext('requestCameraCleanup("swipe")',ctx),true);
    assert.equal(ctx.activeMode,"cleanup");
    assert.equal(ctx.menuOpen,true);
    assert.deepEqual(Array.from(ctx.cameraCleanupController.calls),["batch","swipe"]);
    assert.equal(vm.runInContext('setMode("archive")',ctx),true);
    assert.deepEqual(Array.from(ctx.cameraCleanupController.calls),["batch","swipe","suspend"]);
    assert.equal(ctx.archiveRefreshCalls,1);
    assert.equal(ctx.researchRefreshCalls,1);
    assert.equal(ctx.menuOpen,true);
});

test("Busy or unowned actions fail closed and preserve current menu",()=>{
    for(const override of [
        {cameraCleanupBusy:true},{busy:true},{confirmMode:"all"},
        {cameraCleanupController:null}
    ]){
        const ctx=trashHarness(override);
        assert.equal(vm.runInContext('setMode("cleanup")',ctx),false);
        assert.equal(ctx.activeMode,"trash");
    }
    const ctx=trashHarness({activeMode:"cleanup"});
    assert.equal(vm.runInContext('requestCameraCleanup("burn-all")',ctx),false);
    assert.equal(ctx.menuOpen,true);
    assert.match(trashSource,/onLeftClicked: trashLauncher.setMode\("burn"\)/);
    assert.match(trashSource,/id: burnAllConfirmMenu/);
    assert.match(trashSource,/burnAllPointerRelocated/);
    assert.doesNotMatch(trashMethods,/gio|trashQueuedNow|trash-batch-now/);
});
