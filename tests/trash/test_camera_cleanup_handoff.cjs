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

test("compact Cleanup fits via scroll instead of clipping or changing Camera data",()=>{
    // The compact frame has 450px height with a 314px lifecycle panel.
    // Pinning a 29px scroll rail leaves a 285px interactive viewport.
    const compactFrameHeight=450, compactFrameWidth=420;
    const lifecycleHeight=Math.max(145,compactFrameHeight-136);
    const viewportHeight=lifecycleHeight-29;
    const batchCanvasHeight=Math.max(viewportHeight,650);
    const otherCanvasHeight=Math.max(viewportHeight,525);
    assert.equal(viewportHeight,285);
    assert.equal(batchCanvasHeight-viewportHeight,365);
    assert.equal(otherCanvasHeight-viewportHeight,240);
    assert.match(trashSource,/readonly property bool cleanupScrollRailVisible:/);
    assert.match(trashSource,/anchors\.bottomMargin: trashLauncher\.cleanupScrollRailVisible \? 29 : 0/);
    assert.match(trashSource,/id: cleanupPageViewport/);
    assert.match(trashSource,/contentHeight: Math\.max\(height,/);
    assert.match(trashSource,/\? 650 : 525\)/);
    assert.match(trashSource,/id: cleanupCompactScrollRail/);
    assert.match(trashSource,/visible: trashLauncher\.cleanupScrollRailVisible/);
    assert.match(trashSource,/cleanupPageViewport\.contentY \+ 170/);
    assert.match(trashSource,/cleanupPageViewport\.contentY - 170/);
    assert.match(trashSource,/flickable: cleanupPageViewport/);
    assert.ok(compactFrameWidth<=450);
});

test("compact Batch stacks list above preview while wide layout stays side by side",()=>{
    assert.match(cleanupSource,/readonly property bool compactHosted: width <= 450/);
    assert.match(cleanupSource,/id: cleanupBatchView/);
    assert.match(cleanupSource,/id: cleanupBatchListPane/);
    assert.match(cleanupSource,/id: cleanupBatchPreviewPane/);
    assert.match(cleanupSource,/height: Math\.max\(75, cleanupBatchListPane\.height - 101\)/);
    assert.match(cleanupSource,/height: Math\.max\(65, cleanupBatchPreviewPane\.height - 88\)/);
    assert.match(cleanupSource,/x: cleanupPage\.compactHosted\s*\? 0 : cleanupBatchListPane\.width \+ 9/);
    assert.match(cleanupSource,/y: cleanupPage\.compactHosted\s*\? cleanupBatchListPane\.height \+ 9 : 0/);
    // For 420px compact and 650px page content, both panels remain
    // inside the work area rather than laying out at negative/zero widths.
    const contentHeight=650, workHeight=Math.max(145,contentHeight-216);
    const left=Math.floor((workHeight-9)*0.57), preview=workHeight-left-9;
    assert.ok(left>=200 && preview>=150);
    assert.ok(left-101>=75 && preview-88>=65);
});

test("Hunt and Swipe keep their gestures but get independent scroll controls",()=>{
    assert.match(trashSource,/cleanupTechnique\s*!== "swipe"/);
    assert.match(trashSource,/cleanupTechnique\s*!== "hunt"/);
    assert.match(trashSource,/frameHeight < 661/);
    assert.match(trashSource,/label: "↑ UP"/);
    assert.match(trashSource,/label: "↓ DOWN"/);
    assert.match(trashSource,/cleanupPageViewport\.contentHeight/);
    assert.match(cleanupSource,/id: swipeDeck/);
    assert.match(cleanupSource,/id: huntArena/);
    assert.match(cleanupSource,/camera\.selectCleanupTechnique\(modelData\.id\)/);
    assert.match(cleanupSource,/camera\.trashQueuedNow\(\)/);
    assert.match(cleanupSource,/id: cleanupQueuedList/);
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
    assert.match(trashSource,/id: managedResearchBurnConfirm/);
    assert.match(trashSource,/burnConfirmationOpen/);
    assert.doesNotMatch(trashSource,/id: burnAllConfirmMenu/);
    assert.doesNotMatch(trashMethods,/gio|trashQueuedNow|trash-batch-now/);
});
