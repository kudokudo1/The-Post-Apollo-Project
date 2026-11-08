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
const motionSource = fs.readFileSync(
    path.join(root, "widgets/CameraHuntMotion.js"), "utf8");
const motion = {};
vm.createContext(motion);
vm.runInContext(motionSource.replace(/^\s*\.pragma library\s*$/m,""),motion);
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
        huntTargets:[],
        huntHistory:[],
        huntRound:0,
        huntTick:0,
        huntSecondsLeft:25,
        huntShots:0,
        huntHits:0,
        huntMisses:0,
        huntCombo:0,
        huntScore:0,
        huntPaused:true,
        huntRoundComplete:false,
        huntLastEvent:"READY // NEW ROUND",
        huntMouseX:0.5,
        huntMouseY:0.5,
        huntMouseActive:false,
        HuntMotion:motion,
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
    assert.match(cleanup, /label: "HUNT"/);
    assert.doesNotMatch(cleanup, /HUNT \/\/ NEXT/);
    assert.match(cleanup, /id: cleanupHuntView/);
    assert.match(cleanup, /id: huntArena/);
    assert.match(cleanup, /id: huntTargetRepeater/);
    assert.match(cleanup, /model: camera\.huntTargets\.length/);
    assert.match(cleanup, /property var target: camera\.huntTargets\[index\]/);
    assert.match(cleanup, /target\.xNorm/);
    assert.match(cleanup, /target\.yNorm/);
    assert.match(cleanup, /target\.sizeScale/);
    assert.match(cleanup, /Behavior on x/);
    assert.match(cleanup, /Behavior on y/);
    assert.match(cleanup, /camera\.huntSetPointer\(/);
    assert.match(cleanup, /onClicked: camera\.huntFire\(/);
    assert.match(cleanup, /onTriggered: camera\.huntAdvance\(\)/);
    assert.match(cleanup, /cursorShape: Qt\.CrossCursor/);
    assert.match(cleanup, /label: "UNDO SHOT"/);
    assert.match(cleanup, /label: "NEW ROUND"/);
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


test("Hunt draws exactly 3 random eligible loaded files without touching Trash", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    assert.equal(s.huntStartRound(), true);
    assert.equal(s.huntRound, 1);
    assert.equal(s.huntPaused, false);
    assert.equal(s.huntSecondsLeft,25);
    assert.equal(s.huntTargets.length,3);
    assert.equal(new Set(s.huntTargets.map(t=>t.path)).size,3);
    assert.equal(new Set(s.huntTargets.map(t=>t.profile)).size,3);
    for (const target of s.huntTargets) {
        assert.ok(files.some(f=>f.path===target.path));
        assert.ok(motion.PROFILES.includes(target.profile));
        assert.ok(target.xNorm>=0 && target.xNorm<=1);
        assert.ok(target.yNorm>=0 && target.yNorm<=1);
        assert.ok(target.sizeScale>0);
        assert.ok(Number.isFinite(target.vx));
        assert.ok(Number.isFinite(target.vy));
    }
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.called.length,0);
});

test("Hunt hit marks only a displayed target; Undo restores target and selection", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    assert.equal(s.huntStartRound(),true);
    const target = s.huntTargets[0].path;
    assert.equal(s.huntFire("/tmp/not-an-active-target.png"),false);
    assert.equal(s.huntShots,0);
    assert.equal(s.huntFire(target),true);
    assert.equal(s.huntHits,1);
    assert.equal(s.huntShots,1);
    assert.equal(s.huntMisses,0);
    assert.equal(s.huntScore,100);
    assert.deepEqual(Array.from(s.batchPaths),[target]);
    assert.equal(s.huntTargets.length,2);
    assert.equal(s.called.length,0);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.huntHits,0);
    assert.equal(s.huntShots,0);
    assert.equal(s.huntScore,0);
    assert.equal(s.huntTargets.length,3);
    assert.equal(s.batchPaths.length,0);
});

test("Hunt misses do not queue media and are undoable", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    s.huntStartRound();
    assert.equal(s.huntFire(""),true);
    assert.equal(s.huntShots,1);
    assert.equal(s.huntHits,0);
    assert.equal(s.huntMisses,1);
    assert.equal(s.huntScore,0);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntTargets.length,3);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.huntMisses,0);
    assert.equal(s.huntShots,0);
});

test("Hunt pause and timeout leave unhit files eligible for next round", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    s.huntStartRound();
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntAdvance(),false);
    assert.equal(s.huntTick,0);
    assert.equal(s.huntTogglePause(),true);
    for (let i=0;i<250;i++) assert.equal(s.huntAdvance(),true);
    assert.equal(s.huntRoundComplete,true);
    assert.equal(s.huntPaused,true);
    assert.equal(s.huntSecondsLeft,0);
    assert.equal(s.huntTargets.length,0);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntHistory.length,0);
    assert.equal(s.huntStartRound(),true);
    assert.equal(s.huntRound,2);
    assert.equal(s.huntTargets.length,3);
    assert.equal(s.huntSecondsLeft,25);
});

test("Hunt round finishes after all targets, with combo score and no automatic Trash", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    s.huntStartRound();
    while(s.huntTargets.length)
        assert.equal(s.huntFire(s.huntTargets[0].path),true);
    assert.equal(s.huntHits,3);
    assert.equal(s.huntShots,3);
    assert.equal(s.huntScore,375);
    assert.equal(s.batchPaths.length,3);
    assert.equal(s.huntRoundComplete,true);
    assert.equal(s.huntPaused,true);
    assert.equal(s.called.length,0);
    assert.equal(s.huntStartRound(),false); // all loaded files already queued
    assert.equal(s.called.length,0);
});

test("Hunt full 500 item queue blocks and mode switching never authorizes deleting", () => {
    const s = createState();
    s.cleanupTechnique = "hunt";
    s.batchPaths = Array.from({length:500},(_,i)=>"/tmp/queued"+i+".png");
    assert.equal(s.huntStartRound(),false);
    assert.equal(s.huntTargets.length,0);
    s.batchPaths = Array.from({length:499},(_,i)=>"/tmp/queued"+i+".png");
    assert.equal(s.huntStartRound(),true);
    assert.equal(s.huntFire(s.huntTargets[0].path),true);
    assert.equal(s.batchPaths.length,500);
    assert.equal(s.huntFire(s.huntTargets[0].path),false);
    assert.equal(s.huntPaused,true);
    assert.equal(s.batchPaths.length,500);
    assert.equal(s.called.length,0);
    s.activeView="gallery";
    assert.equal(s.huntTogglePause(),false);
    assert.equal(s.huntUndo(),false);
});

test("Mutating Batch selection invalidates Hunt undo history", () => {
    const s = createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntHistory.length,1);
    s.cleanupTechnique="batch";
    assert.equal(s.batchClear(),true);
    assert.equal(s.huntHistory.length,0);
    s.cleanupTechnique="hunt";
    assert.equal(s.huntUndo(),false);
    assert.equal(s.called.length,0);
});


test("Movement profiles are distinct, normalized, and do not alter file paths", () => {
    assert.deepEqual(Array.from(motion.PROFILES), ["bird","frog","deer","ox","fox"]);
    const record = {path:"/tmp/Example.png",name:"Example.png",mediaType:"image"};
    const targets = motion.PROFILES.map(profile =>
        motion.createTarget(record,profile,()=>0.6));
    for (let t of targets) {
        const before = {...t};
        let moved2D = false;
        for (let i=0;i<210;i++) {
            const next = motion.advanceTarget(t,{active:false,x:0.5,y:0.5});
            assert.equal(next.path,record.path);
            assert.equal(next.name,record.name);
            assert.equal(next.profile,before.profile);
            assert.ok(next.xNorm>=0 && next.xNorm<=1,t.profile+" x");
            assert.ok(next.yNorm>=0 && next.yNorm<=1,t.profile+" y");
            assert.ok(Number.isFinite(next.vx) && Number.isFinite(next.vy));
            if (Math.abs(next.xNorm-before.xNorm)>0.02
                 && Math.abs(next.yNorm-before.yNorm)>0.02)
                moved2D = true;
            t = next;
        }
        assert.equal(moved2D,true,"Expected 2D travel for "+before.profile);
    }
    assert.ok(targets.find(t=>t.profile==="ox").sizeScale >
              targets.find(t=>t.profile==="fox").sizeScale);
    const ox = targets.find(t=>t.profile==="ox");
    const deer = targets.find(t=>t.profile==="deer");
    assert.ok(Math.abs(ox.vx) < Math.abs(deer.vx));
});

test("Bird bounces in X and Y without leaving arena", () => {
    const t = motion.createTarget({path:"/tmp/bird.png"}, "bird",()=>0.6);
    t.xNorm=0.997; t.vx=0.020;
    t.yNorm=0.997; t.vy=0.020;
    const moved = motion.advanceTarget(t,{active:false});
    assert.ok(moved.xNorm<=1 && moved.xNorm>=0);
    assert.ok(moved.yNorm<=1 && moved.yNorm>=0);
    assert.ok(moved.vx<0, "bird should reverse horizontal velocity");
    assert.ok(moved.vy<0, "bird should reverse vertical velocity");
    assert.equal(t.vx,0.020,"motion must not mutate history snapshots");
});

test("Frog rests then makes an airborne arc and returns to landing level", () => {
    let t = motion.createTarget({path:"/tmp/frog.png"}, "frog",()=>0.6);
    const floor = t.baseY;
    const initial = t.xNorm;
    let sawAir = false, sawRest = false;
    for (let i=0;i<100;i++) {
        t = motion.advanceTarget(t,{active:false});
        if (t.state==="hop" && t.yNorm < floor-0.06) sawAir = true;
        if (i>20 && t.state==="idle" &&
            Math.abs(t.yNorm-floor)<0.00001) sawRest=true;
    }
    assert.equal(sawAir,true);
    assert.equal(sawRest,true);
    assert.ok(Math.abs(t.xNorm-initial)>0.001);
});

test("Deer runs fast, leaps diagonally and settles back to its baseline", () => {
    let t = motion.createTarget({path:"/tmp/deer.png"}, "deer",()=>0.6);
    const floor = t.baseY;
    let sawRun=false, sawLeap=false, sawAir=false, landed=false;
    for(let i=0;i<120;i++) {
        const previous = t;
        t=motion.advanceTarget(t,{active:false});
        if(t.state==="run")sawRun=true;
        if(t.state==="leap")sawLeap=true;
        if(t.yNorm<floor-0.07)sawAir=true;
        if(sawLeap && t.state==="run" && Math.abs(t.yNorm-floor)<0.03)
            landed=true;
        assert.equal(t.path,previous.path);
    }
    assert.ok(sawRun && sawLeap && sawAir && landed);
});

test("Fox gently dodges nearby pointer but has a strict speed cap", () => {
    const f = motion.createTarget({path:"/tmp/fox.png"}, "fox",()=>0.6);
    f.xNorm=0.60; f.yNorm=0.60; f.vx=0.006; f.vy=0.002;
    const noCursor=motion.advanceTarget(f,{active:false,x:0.45,y:0.55});
    const nearby=motion.advanceTarget(f,{active:true,x:0.45,y:0.55});
    assert.ok(nearby.xNorm > noCursor.xNorm,"fox should drift away from cursor");
    let t=nearby;
    for(let i=0;i<600;i++) {
        t=motion.advanceTarget(t,{
            active:true,x:Math.max(0,t.xNorm-0.06),
            y:Math.max(0,t.yNorm-0.06)
        });
        assert.ok(Math.abs(t.vx)<=0.022001);
        assert.ok(Math.abs(t.vy)<=0.018001);
        assert.ok(t.xNorm>=0 && t.xNorm<=1);
        assert.ok(t.yNorm>=0 && t.yNorm<=1);
    }
});

test("Hunt clock advances actual 2D target coordinates and keeps immutable Undo", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    const before=s.huntTargets.map(t=>({path:t.path,x:t.xNorm,y:t.yNorm}));
    const historyStart = s.huntTargets[0];
    s.huntAdvance();
    assert.equal(s.huntTick,1);
    assert.equal(s.huntTargets.length,3);
    assert.notEqual(s.huntTargets[0],historyStart);
    assert.ok(s.huntTargets.some((t,i)=>
        t.xNorm!==before[i].x || t.yNorm!==before[i].y));
    assert.equal(s.called.length,0);
    const shotPath=s.huntTargets[0].path;
    const shotSnapshot=s.huntTargets.find(t=>t.path===shotPath);
    s.huntFire(shotPath);
    for(let i=0;i<4;i++) s.huntAdvance();
    s.huntUndo();
    const restored=s.huntTargets.find(t=>t.path===shotPath);
    assert.ok(restored);
    assert.equal(restored.xNorm,shotSnapshot.xNorm);
    assert.equal(restored.yNorm,shotSnapshot.yNorm);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.called.length,0);
});

test("Only Hunt mode accepts pointer tracking; normalized mouse coordinates are clamped", () => {
    const s=createState();
    assert.equal(s.huntSetPointer(33,45,100,100),false);
    s.cleanupTechnique="hunt";
    assert.equal(s.huntSetPointer(33,45,100,100),true);
    assert.equal(s.huntMouseX,0.33);
    assert.equal(s.huntMouseY,0.45);
    assert.equal(s.huntMouseActive,true);
    s.huntSetPointer(400,-20,100,100);
    assert.equal(s.huntMouseX,1);
    assert.equal(s.huntMouseY,0);
    assert.equal(s.huntSetPointer(40,50,0,100),false);
});
