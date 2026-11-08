#!/usr/bin/env node
"use strict";
// Synthetic Cleanup QML logic tests. Never invoke Camera CLI or filesystem Trash.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const qml = fs.readFileSync(path.join(root, "widgets/CameraW.qml"), "utf8");
const from = qml.indexOf("    function batchContains(path) {");
const to = qml.indexOf("    function prepareCapture(mode) {", from);
if (from < 0 || to <= from)
    throw new Error("Camera Batch/Swipe interface is missing");
const functions = qml.slice(from, to);
const files = [
    {name:"Alpha.png",path:"/tmp/Alpha.png"},
    {name:"Bravo.mp4",path:"/tmp/Bravo.mp4"},
    {name:"Charlie.webp",path:"/tmp/Charlie.webp"},
];

function createState() {
    const state = {
        busy:false,
        batchMode:true,
        activeView:"cleanup",
        cleanupTechnique:"batch",
        cleanupCustomFolder:"/tmp/CameraReview",
        galleryFiles:files.slice(),
        batchPaths:[],
        batchPreview:null,
        batchReviewKey:"",
        batchReceipt:"",
        swipeIndex:0,
        swipeHistory:[],
        feedback:"",
        called:[],
        run(action,args) {
            // Camera.qml calls run as a lexical root function rather than
            // a method. Do not rely on 'this' inside the synthetic harness.
            state.called.push({action,args});
            return true;
        },
    };
    state.camera = state;
    vm.createContext(state);
    vm.runInContext(functions, state);
    return state;
}

test("Batch lives in Cleanup, Gallery remains a viewing surface", () => {
    const gallery = qml.slice(qml.indexOf("id: galleryPage"),
                              qml.indexOf("id: cleanupPage"));
    const cleanup = qml.slice(qml.indexOf("id: cleanupPage"));
    assert.doesNotMatch(gallery, /label: "SELECT LOADED"/);
    assert.doesNotMatch(gallery, /label: "REVIEW QUEUE/);
    assert.doesNotMatch(gallery, /label: "BATCH ON"/);
    assert.doesNotMatch(gallery, /onLeftClicked: camera\.batchToggle\(modelData\)/);
    assert.match(cleanup, /label: "SELECT LOADED"/);
    assert.match(cleanup, /label: "REVIEW QUEUE/);
    assert.match(cleanup, /label: "CONFIRM TRASH"/);
    assert.match(cleanup, /id: cleanupSwipeView/);
    assert.match(cleanup, /id: swipeVisualCard/);
    assert.match(cleanup, /rotation: swipeDeck\.dragX \/ 24/);
    assert.match(cleanup, /onPositionChanged: function\(mouse\)/);
    assert.match(cleanup, /onCanceled: \{/);
    assert.match(cleanup, /id: cleanupDesktopView/);
    assert.match(cleanup, /HUNT \/\/ NEXT/);
    assert.match(qml, /readonly property bool batchMode: activeView === "cleanup"/);
    assert.match(qml, /camera\.loadGallery\(false, "cleanup"\)/);
});

test("Batch selects by loaded name, never deletes without review", () => {
    const s = createState();
    assert.equal(s.batchSelectLoaded("bravo"),true);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Bravo.mp4"]);
    assert.equal(s.called.length,0);
    assert.equal(s.batchToggle(files[0]),true);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Bravo.mp4","/tmp/Alpha.png"]);
    assert.equal(s.batchToggle(files[0]),true);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Bravo.mp4"]);
    assert.equal(s.batchClear(),true);
    assert.equal(s.batchPaths.length,0);
});

test("Swipe left marks, right keeps, down skips, undo restores queue and card", () => {
    const s = createState();
    s.cleanupTechnique = "swipe";
    assert.equal(s.swipeDecide("trash"),true);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Alpha.png"]);
    assert.equal(s.swipeIndex,1);
    assert.equal(s.swipeDecide("skip"),true);
    assert.equal(s.swipeIndex,2);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Alpha.png"]);
    assert.equal(s.swipeDecide("keep"),true);
    assert.equal(s.swipeIndex,3);
    assert.equal(s.called.length,0);
    assert.equal(s.swipeUndo(),true);
    assert.equal(s.swipeIndex,2);
    assert.equal(s.swipeUndo(),true);
    assert.equal(s.swipeIndex,1);
    assert.equal(s.swipeUndo(),true);
    assert.equal(s.swipeIndex,0);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.swipeUndo(),false);
});

test("Swipe keeps explicit Batch selections consistent and reversible", () => {
    const s = createState();
    s.batchSelectLoaded("alpha");
    s.batchSelectLoaded("bravo");
    s.cleanupTechnique = "swipe";
    assert.equal(s.swipeDecide("keep"),true);
    assert.deepEqual(Array.from(s.batchPaths), ["/tmp/Bravo.mp4"]);
    assert.equal(s.swipeUndo(),true);
    assert.deepEqual(Array.from(s.batchPaths),
                     ["/tmp/Alpha.png","/tmp/Bravo.mp4"]);
});

test("Shared Trash plan uses Cleanup scope and requires separate confirmation", () => {
    const s = createState();
    s.batchSelectLoaded("alpha");
    assert.equal(s.previewBatchTrash(),true);
    assert.equal(s.called.length,1);
    assert.equal(s.called[0].action,"previewBatch");
    assert.deepEqual(Array.from(s.called[0].args), [
        "preview-batch",JSON.stringify(["/tmp/Alpha.png"]),
        "--folder","/tmp/CameraReview"
    ]);
    // No file move request just from selection or preview.
    assert.equal(s.called.some(x=>x.action==="trashBatch"),false);
    s.batchPreview = {planId:"test-plan",count:1};
    assert.equal(s.confirmBatchTrash(),true);
    assert.equal(s.called[1].action,"trashBatch");
    assert.deepEqual(Array.from(s.called[1].args),[
        "trash-batch","test-plan","MOVE_TO_TRASH"
    ]);
    assert.equal(s.batchPreview,null);
});

test("Bad mode, expired view or full queue cannot mark more files", () => {
    const s = createState();
    s.activeView="gallery";
    s.batchMode=false;
    assert.equal(s.batchToggle(files[0]),false);
    s.cleanupTechnique="swipe";
    assert.equal(s.swipeDecide("trash"),false);
    s.activeView="cleanup";
    s.batchMode=true;
    s.batchPaths = Array.from({length:500},(_,i)=>"/tmp/f"+i+".png");
    assert.equal(s.swipeDecide("trash"),false);
    assert.equal(s.swipeIndex,0);
    assert.equal(s.swipeHistory.length,0);
    assert.equal(s.batchPaths.length,500);
});
