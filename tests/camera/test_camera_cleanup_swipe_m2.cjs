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
        cleanupLoadedFolder:"/tmp/CameraReview",
        cleanupQueueOpen:false,
        cleanupSearchQuery:"",
        cleanupMediaFilter:"all",
        galleryRequestedFolder:"/tmp/CameraReview",
        galleryRequestedView:"cleanup",
        galleryFiles:files.slice(),
        batchPaths:[],
        batchPreview:null,
        batchReviewKey:"",
        batchReceipt:"",
        swipeIndex:0,
        swipeHistory:[],
        huntTargets:[],
        huntHistory:[],
        huntSparedPaths:[],
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
        huntSpawnCount:3,
        huntTargetsPerTier:1,
        huntTargetsEvery:5,
        huntSpeedGainPercent:10,
        huntSpeedEvery:5,
        huntRoundSpeed:1,
        huntRoundSpawnCount:3,
        huntAutoRounds:true,
        huntAutoPending:false,
        huntSettingsOpen:false,
        huntPauseMenuOpen:false,
        huntScoped:false,
        huntHitFlash:false,
        huntShotEffect:null,
        huntShotSerial:0,
        huntLaserCycle:0,
        Colors:{
            omnitrix:"#00F782",orange:"#ED981A",
            yellow:"#F2BE4E",cyan:"#55CFCA",
            magenta:"#C74EC7",red:"#D16041",white:"#DCF3FA"
        },
        huntMouseX:0.5,
        huntMouseY:0.5,
        huntMouseActive:false,
        huntMouseMovingTicks:0,
        huntMouseVX:0,
        huntMouseVY:0,
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
    assert.match(cleanup, /label: "MOVE " \+ camera\.batchPaths\.length \+ " TO TRASH"/);
    assert.match(cleanup, /onLeftClicked: camera\.trashQueuedNow\(\)/);
    assert.doesNotMatch(cleanup, /label: "REVIEW FOR TRASH/);
    assert.doesNotMatch(cleanup, /label: "CANCEL REVIEW"/);
    assert.match(cleanup, /label: "CLEAR MARKS"/);
    assert.match(cleanup, /label: "BATCH SCROLL"/);
    assert.match(cleanup, /label: "BATCH GRID"/);
    assert.match(cleanup, /id: cleanupGridView/);
    assert.match(cleanup, /id: cleanupGridList/);
    assert.match(cleanup, /GridView \{/);
    assert.match(cleanup, /onClicked: camera\.batchToggle\(modelData\)/);
    assert.match(cleanup, /id: cleanupQueueView/);
    assert.match(cleanup, /id: cleanupQueuedList/);
    assert.match(cleanup, /onLeftClicked: camera\.batchRemovePath\(modelData\)/);
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
    assert.match(cleanup, /camera\.huntFire\(/);
    assert.match(cleanup, /onTriggered: camera\.huntAdvance\(\)/);
    assert.match(cleanup, /label: "UNDO SHOT"/);
    assert.match(cleanup, /label: "NEW ROUND"/);
    assert.match(cleanup, /id: huntAutoNextTimer/);
    assert.match(cleanup, /onTriggered: camera\.huntAutoStartNext\(\)/);
    assert.match(cleanup, /interval: 1250/);
    assert.match(cleanup, /id: huntScopeReticle/);
    assert.match(cleanup, /acceptedButtons: Qt\.LeftButton \| Qt\.RightButton/);
    assert.match(cleanup, /mouse\.button === Qt\.LeftButton/);
    assert.match(cleanup, /mouse\.button === Qt\.RightButton/);
    assert.match(cleanup, /camera\.huntScopeScale/);
    assert.match(cleanup, /unscopedWidth \* camera\.huntScopeScale/);
    assert.match(cleanup, /id: huntSettingsOverlay/);
    assert.match(cleanup, /label: "BACK TO PAUSE"/);
    assert.match(cleanup, /id: huntPauseContents/);
    assert.match(cleanup, /visible: camera\.huntPauseMenuOpen/);
    assert.match(cleanup, /label: "SETTINGS"/);
    assert.match(cleanup, /label: "RESET DEFAULTS \/\/ SETTINGS"/);
    assert.match(cleanup, /label: "RESTART GAME \/\/ ROUND 1"/);
    assert.doesNotMatch(cleanup.slice(cleanup.indexOf("id: huntSpawnRow"),
                        cleanup.indexOf("id: huntArena")), /label: "SETTINGS"/);
    assert.match(cleanup, /AUTO NEXT ROUND/);
    assert.match(cleanup, /ADD EVERY N ROUNDS/);
    assert.match(cleanup, /SPEED GAIN \/ TIER/);
    assert.match(cleanup, /SPEED EVERY N ROUNDS/);
    assert.match(cleanup, /label: "SPAWN -"/);
    assert.match(cleanup, /label: "SPAWN \+"/);
    assert.match(cleanup, /TARGETS \/\//);
    assert.match(cleanup, /z: camera\.huntTargetDepth\(target\.profile\)/);
    assert.match(cleanup, /readonly property color targetTint/);
    assert.match(cleanup, /RectangularShadow \{/);
    assert.match(cleanup, /id: huntTargetPlate/);
    assert.match(cleanup, /id: huntNormalCrosshair/);
    assert.match(cleanup, /cursorShape: camera\.huntPaused/);
    assert.match(cleanup, /Qt\.BlankCursor/);
    assert.match(cleanup, /id: huntHitWash/);
    assert.match(cleanup, /camera\.huntHitFlash\s*&& huntLaserLayer\.impactReached/);
    assert.match(cleanup, /\? 0\.045 : 0\.0/);
    assert.match(cleanup, /id: huntHitAnimalEcho/);
    assert.match(cleanup, /id: huntLaserLayer/);
    assert.match(cleanup, /id: huntLaserFlight/);
    assert.match(cleanup, /HuntMotion\.laserTrajectory\(/);
    assert.match(cleanup, /readonly property real tailProgress:/);
    assert.match(cleanup, /readonly property real visibleStreak:/);
    assert.match(cleanup, /readonly property bool impactReached:/);
    assert.match(cleanup, /huntLaserLayer\.impactReached/);
    assert.match(cleanup, /huntLaserLayer\.trajectory\.entryProgress/);
    assert.match(cleanup, /duration: 180/);
    assert.match(cleanup, /interval: 320/);
    assert.doesNotMatch(cleanup, /huntLaserLayer\.length \* huntLaserLayer\.progress/);
    assert.match(cleanup, /impact\.x \/ huntArena\.width/);
    assert.match(cleanup, /impact\.y \/ huntArena\.height/);
    assert.doesNotMatch(cleanup, /readonly property real muzzleX: width \* 0\.5/);
    assert.doesNotMatch(cleanup, /readonly property real muzzleY: height \* 0\.97/);
    assert.match(cleanup, /function onHuntShotSerialChanged/);
    assert.match(cleanup, /opacity: huntTargetItem\.hovered \? 0\.18 : 0\.10/);
    assert.match(cleanup, /opacity: 0\.055/);
    assert.match(cleanup, /huntTargetItem\.mediaTint/);
    assert.match(cleanup, /camera\.huntMediaLabel\(/);
    assert.match(cleanup, /huntTargetItem\.target\.protected/);
    assert.match(cleanup, /huntKeepProtected\(/);
    assert.match(cleanup, /id: huntHitFlashTimer/);
    assert.match(cleanup, /readonly property real crowdScale/);
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

test("Fox juke-orbits moving pointer but taunts a stationary one at bounded speeds", () => {
    const f = motion.createTarget({path:"/tmp/fox.png"}, "fox",()=>0.6);
    f.xNorm=0.72; f.yNorm=0.50; f.vx=0; f.vy=0;
    const untracked=motion.advanceTarget(f,{active:false,x:0.50,y:0.50});
    const taunting=motion.advanceTarget(f,{active:true,moving:false,x:0.50,y:0.50});
    const chased=motion.advanceTarget(f,{active:true,moving:true,x:0.50,y:0.50});
    assert.ok(taunting.xNorm < untracked.xNorm,"settled cursor attracts fox");
    assert.ok(chased.xNorm > untracked.xNorm,"moving cursor triggers evasive radial juke");
    assert.ok(Math.abs(chased.vy)>Math.abs(untracked.vy),
              "moving cursor induces sideways orbit motion");
    assert.equal(chased.state,"juke");
    assert.equal(taunting.state,"taunt");
    let t=chased;
    for(let i=0;i<600;i++) {
        t=motion.advanceTarget(t,{
            active:true,moving:true,x:Math.max(0,t.xNorm-0.06),
            y:Math.max(0,t.yNorm-0.06)
        });
        assert.ok(Math.abs(t.vx)<=0.041001);
        assert.ok(Math.abs(t.vy)<=0.034001);
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


test("Spawn controls cap at 1–10 and do not modify active round or touch Trash", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    assert.equal(s.huntSpawnCount,3);
    assert.equal(s.huntSetSpawnCount(999),true);
    assert.equal(s.huntSpawnCount,10);
    assert.equal(s.huntSetSpawnCount(-10),true);
    assert.equal(s.huntSpawnCount,1);
    assert.equal(s.huntSetSpawnCount("not-a-number"),false);
    assert.equal(s.huntSpawnCount,1);
    assert.equal(s.huntSetSpawnCount(4),true);
    assert.equal(s.huntStartRound(),true);
    // Only 3 eligible files exist despite requesting four.
    assert.equal(s.huntTargets.length,3);
    assert.equal(s.huntSetSpawnCount(9),true);
    assert.equal(s.huntTargets.length,3);
    assert.equal(s.called.length,0);
    s.activeView="gallery";
    assert.equal(s.huntSetSpawnCount(5),false);
});

test("Ten Hunt targets draw from eligible inventory with shuffled profile cycles", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:15},(_,i)=>({
        path:"/tmp/inventory_"+i+".png",
        name:"inventory_"+i+".png",mediaType:"image"
    }));
    s.huntSetSpawnCount(10);
    assert.equal(s.huntStartRound(),true);
    assert.equal(s.huntTargets.length,10);
    assert.equal(new Set(s.huntTargets.map(t=>t.path)).size,10);
    assert.equal(new Set(s.huntTargets.slice(0,5).map(t=>t.profile)).size,5);
    assert.equal(new Set(s.huntTargets.slice(5,10).map(t=>t.profile)).size,5);
    assert.equal(s.huntTargets.some(t=>t.profile==="ox"),true);
    assert.equal(s.called.length,0);
    s.huntFire(s.huntTargets[0].path);
    assert.equal(s.batchPaths.length,1);
    assert.equal(s.called.length,0);
});

test("Ox is substantially bigger; Frog is smaller and hop parameters vary", () => {
    const f=motion.createTarget({path:"/tmp/frog.png"},"frog",()=>0.6);
    const ox=motion.createTarget({path:"/tmp/ox.png"},"ox",()=>0.6);
    assert.ok(ox.sizeScale>=1.6);
    assert.ok(f.sizeScale<=0.70);
    assert.ok(ox.sizeScale > f.sizeScale*2);
    let frog=f;
    const hops=[];
    let previous="idle";
    for(let i=0;i<300;i++) {
        frog=motion.advanceTarget(frog,{active:false});
        if(frog.state==="hop" && previous==="idle")
            hops.push({speed:Math.abs(frog.vx),height:Math.abs(frog.vy),
                       gravity:frog.hopGravity});
        previous=frog.state;
    }
    assert.ok(hops.length>=3,"need several frog jumps");
    assert.ok(new Set(hops.map(x=>x.speed.toFixed(5))).size>=2,
              "hop distance varies");
    assert.ok(new Set(hops.map(x=>x.height.toFixed(5))).size>=2,
              "hop lift varies");
});

test("Bird occasionally perches and then takes flight again", () => {
    let t=motion.createTarget({path:"/tmp/bird.png"},"bird",()=>0.6);
    assert.ok(Math.abs(t.vx)>=0.015);
    let perched=false,resumed=false;
    for(let i=0;i<160;i++) {
        const before=t;
        t=motion.advanceTarget(t,{active:false});
        if(t.state==="perch") {
            perched=true;
            assert.equal(t.vx,0);
            assert.equal(t.vy,0);
            assert.equal(t.xNorm,before.xNorm);
            assert.equal(t.yNorm,before.yNorm);
        } else if(perched && t.state==="fly")
            resumed=true;
    }
    assert.ok(perched && resumed);
});

test("Deer takes rare short rest and resumes its prior run", () => {
    let t=motion.createTarget({path:"/tmp/deer.png"},"deer",()=>0.6);
    assert.ok(t.fatigueAt>=215);
    t.fatigueAt=3; // synthetic forced rare event
    let rested=false,resumed=false;
    for(let i=0;i<40;i++) {
        t=motion.advanceTarget(t,{active:false});
        if(t.state==="rest") rested=true;
        if(rested && t.state==="run") resumed=true;
    }
    assert.ok(rested && resumed);
    assert.ok(t.fatigueAt>40);
});

test("Mouse motion decays to settled after five ticks and resets at new scan", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    assert.equal(s.huntSetPointer(50,50,100,100),true);
    assert.equal(s.huntMouseMovingTicks,0); // first sighting isn't a chase
    s.huntSetPointer(70,45,100,100);
    assert.equal(s.huntMouseMovingTicks,5);
    assert.ok(s.huntMouseVX>0);
    s.huntStartRound();
    for(let i=0;i<5;i++)
        s.huntAdvance();
    assert.equal(s.huntMouseMovingTicks,0);
    assert.equal(s.huntMouseActive,true);
    assert.equal(s.called.length,0);
});


test("Progression defaults: target +1 per 5 rounds and speed +10% per five, capped", () => {
    assert.equal(motion.spawnForRound(3,1,5,1),3);
    assert.equal(motion.spawnForRound(3,1,5,5),3);
    assert.equal(motion.spawnForRound(3,1,5,6),4);
    assert.equal(motion.spawnForRound(3,1,5,10),4);
    assert.equal(motion.spawnForRound(3,1,5,11),5);
    assert.equal(motion.spawnForRound(3,1,5,999),10);
    assert.equal(motion.spawnForRound(10,5,1,1000),10);
    assert.equal(motion.spawnForRound(3,0,1,100),3);
    assert.equal(motion.speedForRound(10,5,1),1);
    assert.equal(motion.speedForRound(10,5,5),1);
    assert.ok(Math.abs(motion.speedForRound(10,5,6)-1.1)<1e-9);
    assert.ok(Math.abs(motion.speedForRound(10,5,11)-1.21)<1e-9);
    assert.equal(motion.speedForRound(50,1,100),2.5);
    assert.equal(motion.speedForRound(0,1,100),1);
});

test("Progression settings are bounded and update only the following round", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:25},(_,i)=>({
        path:"/tmp/prog_"+i+".png",name:"prog_"+i+".png",mediaType:"image"
    }));
    s.huntRound=5; s.huntRoundComplete=true;
    assert.equal(s.huntStartRound(),true);
    assert.equal(s.huntRound,6);
    assert.equal(s.huntRoundSpawnCount,4);
    assert.equal(s.huntTargets.length,4);
    assert.ok(Math.abs(s.huntRoundSpeed-1.1)<1e-8);
    assert.equal(s.huntSetProgression("targetGain",5),true);
    assert.equal(s.huntSetProgression("targetEvery",1),true);
    assert.equal(s.huntSetProgression("speedGain",50),true);
    assert.equal(s.huntSetProgression("speedEvery",1),true);
    assert.equal(s.huntTargets.length,4);
    assert.ok(Math.abs(s.huntRoundSpeed-1.1)<1e-8);
    assert.equal(s.huntSetProgression("speedEvery",0),true);
    assert.equal(s.huntSpeedEvery,1);
    assert.equal(s.huntSetProgression("targetEvery",999),true);
    assert.equal(s.huntTargetsEvery,50);
    assert.equal(s.huntSetProgression("targetGain",-1),true);
    assert.equal(s.huntTargetsPerTier,0);
    assert.equal(s.huntSetProgression("invalid",100),false);
    assert.equal(s.huntSetProgression("speedGain","whoops"),false);
    assert.equal(s.called.length,0);
});

test("Speed tiers move a slow ox farther without compounding stored velocity", () => {
    const ox=motion.createTarget({path:"/tmp/ox.png"},"ox",()=>0.6);
    ox.xNorm=0.3; ox.yNorm=0.3; ox.vx=0.003; ox.vy=0.002;
    const normal=motion.advanceTarget(ox,{active:false},1);
    const fast=motion.advanceTarget(ox,{active:false},1.5);
    assert.ok(fast.xNorm>normal.xNorm);
    assert.ok(fast.yNorm>normal.yNorm);
    assert.ok(Math.abs(fast.vx-normal.vx)<1e-10);
    assert.ok(Math.abs(fast.vy-normal.vy)<1e-10);
    let t=fast;
    for(let i=0;i<500;i++) {
        t=motion.advanceTarget(t,{active:false},2.5);
        assert.ok(t.xNorm>=0&&t.xNorm<=1);
        assert.ok(t.yNorm>=0&&t.yNorm<=1);
    }
    assert.equal(ox.xNorm,0.3); // immutable input
});

test("Auto-next starts once after all hits and never moves files itself", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:30},(_,i)=>({
        path:"/tmp/round_"+i+".png",name:"round_"+i+".png",mediaType:"image"
    }));
    assert.equal(s.huntStartRound(),true);
    while(s.huntTargets.length)
        s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntRoundComplete,true);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntAutoStartNext(),true);
    assert.equal(s.huntRound,2);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.huntRoundComplete,false);
    assert.equal(s.huntAutoStartNext(),false);
    assert.equal(s.called.length,0);
});

test("Auto-next fails closed when no eligible photos remain; no repeat loop", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    while(s.huntTargets.length)
        s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntAutoStartNext(),false);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.huntTargets.length,0);
    assert.equal(s.huntRound,1);
    assert.equal(s.called.length,0);
    assert.equal(s.huntAutoStartNext(),false);
});

test("Undo cancels pending auto-next and restores a queued shot", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    while(s.huntTargets.length)
        s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.huntRoundComplete,false);
    assert.equal(s.huntPaused,false);
    assert.equal(s.huntTargets.length,1);
    assert.equal(s.batchPaths.length,2);
    assert.equal(s.called.length,0);
});

test("Auto-round setting and opening settings safely halt active gameplay", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    assert.equal(s.huntSetScoped(true),true);
    assert.equal(s.huntScoped,true);
    assert.equal(s.huntToggleSettings(),false); // Settings requires Pause menu
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntPauseMenuOpen,true);
    assert.equal(s.huntSettingsOpen,false);
    assert.equal(s.huntScoped,false);
    assert.equal(s.huntPaused,true);
    assert.equal(s.huntToggleSettings(),true);
    assert.equal(s.huntSettingsOpen,true);
    assert.equal(s.huntSetScoped(true),false);
    assert.equal(s.huntToggleSettings(),true);
    assert.equal(s.huntSettingsOpen,false);
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntPauseMenuOpen,false);
    assert.equal(s.huntSetScoped(true),true);
    assert.equal(s.huntSetScoped(false),true);
    assert.equal(s.huntScoped,false);
    assert.equal(s.huntSetAutoRounds(false),true);
    assert.equal(s.huntAutoRounds,false);
    assert.equal(s.called.length,0);
});

test("Auto-next is scheduled on timeout, not triggered by a miss or normal pause", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    s.huntFire("");
    assert.equal(s.huntAutoPending,false);
    s.huntTogglePause();
    assert.equal(s.huntAutoPending,false);
    s.huntTogglePause();
    for(let i=0;i<250;i++) s.huntAdvance();
    assert.equal(s.huntRoundComplete,true);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntAutoStartNext(),true);
    assert.equal(s.huntRound,2);
    assert.equal(s.called.length,0);
});


test("Hunt profile depth makes frog below fox and ox above all others", () => {
    const s=createState();
    const sorted=["frog","fox","deer","bird","ox"]
        .map(name=>({name,z:s.huntTargetDepth(name)}));
    for(let i=1;i<sorted.length;i++)
        assert.ok(sorted[i].z>sorted[i-1].z,
                  sorted[i-1].name+" must remain behind "+sorted[i].name);
    assert.deepEqual(sorted.map(x=>x.z),[5,10,30,35,50]);
});

test("Hunt animal colors use existing palette including Omnitrix", () => {
    const s=createState();
    assert.equal(s.huntTargetColor("frog"),"#00F782");
    assert.equal(s.huntTargetColor("fox"),"#ED981A");
    assert.equal(s.huntTargetColor("deer"),"#F2BE4E");
    assert.equal(s.huntTargetColor("bird"),"#55CFCA");
    assert.equal(s.huntTargetColor("ox"),"#C74EC7");
    assert.equal(s.huntTargetColor("other"),"#DCF3FA");
});

test("Ox size varies across spawns while staying bigger than other animals", () => {
    const tinyOx=motion.createTarget({path:"/tmp/oxA.png"},"ox",()=>0.05);
    const largeOx=motion.createTarget({path:"/tmp/oxB.png"},"ox",()=>0.95);
    assert.ok(tinyOx.sizeScale>=1.5);
    assert.ok(largeOx.sizeScale>tinyOx.sizeScale+0.5);
    assert.ok(largeOx.sizeScale<=2.25);
    const frog=motion.createTarget({path:"/tmp/frog.png"},"frog",()=>0.95);
    assert.ok(tinyOx.sizeScale>frog.sizeScale*2);
});

test("Ox chooses frog to shield before fox even if fox is nearer", () => {
    const ox=motion.createTarget({path:"/tmp/ox.png"},"ox",()=>0.5);
    ox.xNorm=0.18; ox.yNorm=0.22; ox.vx=0; ox.vy=0;
    const frog={path:"/tmp/frog.png",profile:"frog",xNorm:0.85,yNorm:0.87,vx:0};
    const fox={path:"/tmp/fox.png",profile:"fox",xNorm:0.20,yNorm:0.10,vx:0};
    assert.equal(motion.shieldingPrey(ox,[ox,fox,frog]).path,frog.path);
    const withFrog=motion.advanceTarget(ox,{active:false},1,[ox,fox,frog]);
    const withoutFrog=motion.advanceTarget(ox,{active:false},1,[ox,fox]);
    assert.ok(withFrog.vy>0,"frog is below ox; shield should drift toward it");
    assert.ok(withoutFrog.vy<0,"without frog, ox tracks nearby fox above");
    assert.equal(withFrog.state,"shield");
    assert.equal(ox.vx,0,"immutable movement leaves source intact");
});

test("Ox slowly closes on frog without teleport or exceeding heavy velocity caps", () => {
    let ox=motion.createTarget({path:"/tmp/ox.png"},"ox",()=>0.5);
    ox.xNorm=0.12; ox.yNorm=0.12; ox.vx=0; ox.vy=0;
    const frog={path:"/tmp/frog.png",profile:"frog",xNorm:0.73,yNorm:0.77,vx:0};
    const initial=Math.hypot(ox.xNorm-frog.xNorm,ox.yNorm-frog.yNorm);
    let previous=ox;
    for(let i=0;i<90;i++) {
        ox=motion.advanceTarget(ox,{active:false},1,[previous,frog]);
        assert.ok(ox.xNorm>=0&&ox.xNorm<=1);
        assert.ok(ox.yNorm>=0&&ox.yNorm<=1);
        assert.ok(Math.abs(ox.vx)<=0.007501);
        assert.ok(Math.abs(ox.vy)<=0.006001);
        assert.ok(Math.hypot(ox.xNorm-previous.xNorm,ox.yNorm-previous.yNorm)<0.012);
        previous=ox;
    }
    assert.ok(Math.hypot(ox.xNorm-frog.xNorm,ox.yNorm-frog.yNorm)<initial*0.7);
});

test("Hunt hit triggers animal impact echo; misses and selection alone do not flash arena", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    assert.equal(s.huntHitFlash,false);
    s.huntStartRound();
    assert.equal(s.huntHitFlash,false);
    s.huntFire("");
    assert.equal(s.huntHitFlash,false);
    const path=s.huntTargets[0].path;
    s.huntFire(path);
    assert.equal(s.huntHitFlash,true);
    assert.equal(s.batchPaths.length,1);
    assert.equal(s.called.length,0);
    s.huntUndo();
    assert.equal(s.huntHitFlash,false);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.called.length,0);
});


test("Hunt classifies media by backend type and screenshot flags, not guessing names", () => {
    assert.equal(motion.mediaKind({mediaType:"screenshot"}),"screenshot");
    assert.equal(motion.mediaKind({mediaType:"other-image",screenshotLikely:true}),"screenshot");
    assert.equal(motion.mediaKind({mediaType:"other-image",name:"family.jpg"}),"photo");
    assert.equal(motion.mediaKind({mediaType:"webcam-photo"}),"photo");
    assert.equal(motion.mediaKind({mediaType:"webcam-video"}),"webcam-video");
    assert.equal(motion.mediaKind({mediaType:"other-video"}),"video");
    assert.equal(motion.mediaKind({mediaType:"screen-video"}),"screen-video");
    assert.equal(motion.protectedHuntMedia({mediaType:"screen-video"}),true);
    assert.equal(motion.protectedHuntMedia({mediaType:"other-video",name:"screen_hello.mp4"}),false);
    const screen=motion.createTarget({
        path:"/tmp/screen.mp4",name:"screen.mp4",mediaType:"screen-video"
    },"bird",()=>0.5);
    assert.equal(screen.mediaKind,"screen-video");
    assert.equal(screen.protected,true);
});

test("Hunt media wash colors follow the content, not the animal", () => {
    const s=createState();
    assert.equal(s.huntMediaTint("photo"),"#55CFCA");
    assert.equal(s.huntMediaTint("screenshot"),"#ED981A");
    assert.equal(s.huntMediaTint("video"),"#D16041");
    assert.equal(s.huntMediaTint("webcam-video"),"#C74EC7");
    assert.equal(s.huntMediaTint("screen-video"),"#F2BE4E");
    assert.equal(s.huntMediaLabel("screen-video"),"SCREEN RECORDING · SAFE");
    assert.equal(s.huntMediaLabel("webcam-video"),"WEBCAM VIDEO");
    assert.equal(s.huntMediaLabel("photo"),"PHOTO");
    assert.equal(s.huntTargetColor("frog"),"#00F782");
    assert.equal(s.huntTargetColor("fox"),"#ED981A");
});

test("Cyan/orange/magenta laser rotates on shots and only hits tint the arena", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    assert.equal(s.huntFire("",0.1,0.3),true);
    assert.equal(s.huntShotEffect.color,"#55CFCA");
    assert.equal(s.huntShotEffect.hit,false);
    assert.equal(s.huntHitFlash,false);
    assert.equal(s.huntShotEffect.aimX,0.1);
    const first=s.huntTargets[0];
    assert.equal(s.huntFire(first.path,0.66,0.4,0.5,0.3,0.2,0.15),true);
    assert.equal(s.huntShotEffect.color,"#ED981A");
    assert.equal(s.huntShotEffect.hit,true);
    assert.equal(s.huntShotEffect.path,first.path);
    assert.equal(s.huntHitFlash,true);
    assert.equal(s.huntShotEffect.rectW,0.2);
    assert.equal(s.huntShotEffect.rectH,0.15);
    assert.equal(s.huntFire("",0.9,0.1),true);
    assert.equal(s.huntShotEffect.color,"#C74EC7");
    assert.equal(s.huntShotEffect.hit,false);
    assert.equal(s.huntHitFlash,false);
    assert.equal(s.huntFire("",0.5,0.5),true);
    assert.equal(s.huntShotEffect.color,"#55CFCA");
    assert.equal(s.huntLaserCycle,4);
    assert.equal(s.huntShotSerial,4);
    assert.equal(s.called.length,0);
});

test("Screen recordings remain visible but safe and cannot be fired into Hunt Trash", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=[
        {path:"/tmp/screen_a.mp4",name:"screen_a.mp4",
         mediaType:"screen-video"},
        {path:"/tmp/sc.png",name:"sc.png",
         mediaType:"screenshot",screenshotLikely:true}
    ];
    assert.equal(s.huntStartRound(),true);
    const protectedTarget=s.huntTargets.find(x=>x.mediaType==="screen-video");
    assert.ok(protectedTarget);
    assert.equal(protectedTarget.protected,true);
    assert.equal(s.huntFire(protectedTarget.path),false);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntShotSerial,0);
    assert.equal(s.huntKeepProtected(protectedTarget.path),true);
    assert.equal(s.batchPaths.length,0);
    assert.deepEqual(Array.from(s.huntSparedPaths),[protectedTarget.path]);
    assert.equal(s.huntShots,0);
    assert.equal(s.huntHits,0);
    assert.equal(s.huntTargets.length,1);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.huntTargets.length,2);
    assert.equal(s.huntSparedPaths.length,0);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntKeepProtected(protectedTarget.path),true);
    const screenshot=s.huntTargets.find(x=>x.mediaType==="screenshot");
    assert.equal(s.huntFire(screenshot.path),true);
    assert.deepEqual(Array.from(s.batchPaths),[screenshot.path]);
    assert.equal(s.huntShots,1);
    assert.equal(s.called.length,0);
});

test("Shot effects do not mutate file records, and Undo clears laser and hit cue", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    const before=s.huntTargets[0];
    assert.equal(s.huntFire(before.path,2,-4,-1,3,2,1),true);
    assert.ok(s.huntHitFlash);
    assert.equal(s.huntShotEffect.aimX,1);
    assert.equal(s.huntShotEffect.aimY,0);
    assert.equal(s.huntShotEffect.rectX,0);
    assert.equal(s.huntShotEffect.rectY,1);
    assert.equal(s.huntShotEffect.rectW,1);
    assert.equal(s.huntShotEffect.rectH,1);
    assert.equal(before.path,s.huntShotEffect.path);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.huntHitFlash,false);
    assert.equal(s.huntShotEffect,null);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.called.length,0);
});


test("Spared screen recordings do not respawn in later rounds", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=[
        {path:"/tmp/preserved-screen.mp4",name:"screen_001.mp4",
         mediaType:"screen-video"},
        {path:"/tmp/photo.png",name:"photo.png",mediaType:"other-image"},
        {path:"/tmp/again.jpg",name:"again.jpg",mediaType:"other-image"}
    ];
    assert.equal(s.huntStartRound(),true);
    const safe=s.huntTargets.find(t=>t.protected);
    assert.equal(s.huntKeepProtected(safe.path),true);
    assert.equal(s.huntTargets.some(t=>t.path===safe.path),false);
    // Complete round without deleting screen media.
    while(s.huntTargets.length)
        s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntAutoStartNext(),false);
    assert.equal(s.huntTargets.length,0);
    assert.equal(s.huntSparedPaths.includes(safe.path),true);
    assert.equal(s.batchPaths.includes(safe.path),false);
    assert.equal(s.called.length,0);
});

test("Time-out spares protected videos without queuing them for Trash", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=[
        {path:"/tmp/safe-screen.mp4",name:"safe-screen.mp4",
         mediaType:"screen-video"}
    ];
    assert.equal(s.huntStartRound(),true);
    for(let i=0;i<250;i++)
        s.huntAdvance();
    assert.equal(s.huntRoundComplete,true);
    assert.deepEqual(Array.from(s.huntSparedPaths),["/tmp/safe-screen.mp4"]);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntAutoStartNext(),false);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.called.length,0);
});


test("Laser launches from below visible arena following cursor aim, not fixed deck", () => {
    const a=motion.laserEntryPoint(0.1);
    const mid=motion.laserEntryPoint(0.5);
    const b=motion.laserEntryPoint(0.9);
    assert.ok(a.y>1 && mid.y>1 && b.y>1,"muzzle is below visible world");
    assert.ok(a.x>=0 && a.x<=1 && b.x>=0 && b.x<=1);
    assert.ok(a.x<mid.x && mid.x<b.x,"origin follows cursor side to side");
    assert.ok(Math.abs(a.x-0.5)>0.2,"not fixed center of deck");
    assert.ok(Math.abs(b.x-0.5)>0.2,"not fixed center of deck");
    assert.ok(Math.abs(a.x-0.1)<0.11,"slight handheld muzzle offset");
    assert.ok(Math.abs(b.x-0.9)<0.11,"slight handheld muzzle offset");
    assert.equal(motion.laserEntryPoint(500).y,1.14);
    assert.equal(motion.laserEntryPoint(-200).y,1.14);
});

test("Pause menu alone hosts Settings; auto-rounds wait while the menu is open", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    assert.equal(s.huntToggleSettings(),false);
    assert.equal(s.huntTogglePause(),true); // even without a live round
    assert.equal(s.huntPauseMenuOpen,true);
    assert.equal(s.huntSettingsOpen,false);
    assert.equal(s.huntToggleSettings(),true);
    assert.equal(s.huntSettingsOpen,true);
    assert.equal(s.huntSetProgression("speedGain",35),true);
    assert.equal(s.huntResetDefaults(),true);
    assert.equal(s.huntSpeedGainPercent,10);
    assert.equal(s.huntToggleSettings(),true);
    assert.equal(s.huntPauseMenuOpen,true);
    assert.equal(s.huntSettingsOpen,false);
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntPauseMenuOpen,false);
    assert.equal(s.called.length,0);
});

test("Reset Defaults restores every Hunt option without resetting round, score or queue", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:9},(_,i)=>({
        path:"/tmp/default"+i+".png",name:"default"+i+".png",mediaType:"image"
    }));
    s.huntSpawnCount=9;
    s.huntTargetsPerTier=4;
    s.huntTargetsEvery=2;
    s.huntSpeedGainPercent=45;
    s.huntSpeedEvery=3;
    s.huntAutoRounds=false;
    s.huntRound=7;
    s.huntScore=1200;
    s.batchPaths=["/tmp/to-review.jpg"];
    assert.equal(s.huntResetDefaults(),false);
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntResetDefaults(),false); // not yet in Settings
    assert.equal(s.huntToggleSettings(),true);
    assert.equal(s.huntResetDefaults(),true);
    assert.equal(s.huntSpawnCount,3);
    assert.equal(s.huntTargetsPerTier,1);
    assert.equal(s.huntTargetsEvery,5);
    assert.equal(s.huntSpeedGainPercent,10);
    assert.equal(s.huntSpeedEvery,5);
    assert.equal(s.huntAutoRounds,true);
    assert.equal(s.huntRound,7);
    assert.equal(s.huntScore,1200);
    assert.deepEqual(Array.from(s.batchPaths),["/tmp/to-review.jpg"]);
    assert.equal(s.called.length,0);
});

test("Restart Game begins Round 1 and resets progression statistics, not queued files", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:12},(_,i)=>({
        path:"/tmp/restart"+i+".png",name:"restart"+i+".png",mediaType:"image"
    }));
    s.huntSpawnCount=4;
    s.huntTargetsPerTier=2;
    s.huntTargetsEvery=2;
    s.huntSpeedGainPercent=35;
    s.huntSpeedEvery=2;
    s.batchPaths=["/tmp/restart0.png"];
    s.batchPreview={planId:"previous"};
    s.batchReviewKey=JSON.stringify(s.batchPaths);
    s.huntRound=15;
    s.huntScore=2500;
    s.huntHits=10;
    s.huntShots=14;
    s.huntMisses=4;
    s.huntSparedPaths=["/tmp/restart2.png"];
    s.huntAutoPending=true;
    assert.equal(s.huntRestartGame(),false); // requires Pause
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntRestartGame(),true);
    assert.equal(s.huntRound,1);
    assert.equal(s.huntTargets.length,4);
    assert.ok(s.huntTargets.every(t=>t.path!=="/tmp/restart0.png"));
    assert.equal(s.huntRoundSpeed,1);
    assert.equal(s.huntScore,0);
    assert.equal(s.huntHits,0);
    assert.equal(s.huntShots,0);
    assert.equal(s.huntMisses,0);
    assert.equal(s.huntLaserCycle,0);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.huntPauseMenuOpen,false);
    assert.equal(s.huntSettingsOpen,false);
    assert.equal(s.huntPaused,false);
    assert.equal(s.huntTargetsPerTier,2); // Restart !== reset settings
    assert.equal(s.huntAutoRounds,true);
    assert.equal(s.batchPreview,null); // old plan is invalidated
    assert.equal(s.batchReviewKey,"");
    assert.deepEqual(Array.from(s.batchPaths),["/tmp/restart0.png"]);
    assert.equal(s.huntSparedPaths.length,0);
    assert.equal(s.called.length,0);
});

test("Restart remains paused with no eligible files, preserving reviewed queue", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=[{path:"/tmp/only.png",name:"only.png",mediaType:"image"}];
    s.batchPaths=["/tmp/only.png"];
    s.huntRound=19;
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntRestartGame(),false);
    assert.equal(s.huntRound,0);
    assert.equal(s.huntPaused,true);
    assert.equal(s.huntPauseMenuOpen,true);
    assert.equal(s.huntAutoPending,false);
    assert.deepEqual(Array.from(s.batchPaths),["/tmp/only.png"]);
    assert.equal(s.called.length,0);
});

test("Pause menu blocks auto-next until explicitly closed", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:20},(_,i)=>({
        path:"/tmp/auto"+i+".jpg",name:"auto"+i+".jpg",mediaType:"image"
    }));
    s.huntStartRound();
    while(s.huntTargets.length)s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntPauseMenuOpen,true);
    assert.equal(s.huntAutoStartNext(),false);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntTogglePause(),true);
    assert.equal(s.huntAutoStartNext(),true);
    assert.equal(s.huntRound,2);
    assert.equal(s.called.length,0);
});


test("Reset Defaults re-arms Auto Next for a finished round when re-enabled", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.galleryFiles=Array.from({length:12},(_,i)=>({
        path:"/tmp/rearm"+i+".jpg",name:"rearm"+i+".jpg",mediaType:"image"
    }));
    s.huntStartRound();
    s.huntSetAutoRounds(false);
    while(s.huntTargets.length)s.huntFire(s.huntTargets[0].path);
    assert.equal(s.huntRoundComplete,true);
    assert.equal(s.huntAutoPending,false);
    s.huntTogglePause();
    s.huntToggleSettings();
    assert.equal(s.huntResetDefaults(),true);
    assert.equal(s.huntAutoRounds,true);
    assert.equal(s.huntAutoPending,true);
    assert.equal(s.huntAutoStartNext(),false,"pause overlay prevents auto start");
    s.huntToggleSettings();
    s.huntTogglePause();
    assert.equal(s.huntAutoStartNext(),true);
    assert.equal(s.huntRound,2);
    assert.equal(s.huntAutoPending,false);
    assert.equal(s.called.length,0);
});


test("Laser trajectory enters from below playfield and strikes exact cursor", () => {
    const cases=[
        {x:0.0,y:0.0},{x:0.2,y:0.35},{x:0.5,y:0.5},
        {x:0.93,y:0.8},{x:1,y:1}
    ];
    for(const {x,y} of cases) {
        const trajectory=motion.laserTrajectory(x,y);
        assert.ok(trajectory.originY>1,"gun starts outside arena");
        assert.equal(trajectory.aimX,x);
        assert.equal(trajectory.aimY,y);
        assert.ok(trajectory.entryX>=0&&trajectory.entryX<=1);
        assert.ok(trajectory.entryProgress>=0&&trajectory.entryProgress<=1);
        const atEdge=trajectory.originX +
            (trajectory.aimX-trajectory.originX)*
            trajectory.entryProgress;
        const yAtEdge=trajectory.originY +
            (trajectory.aimY-trajectory.originY)*
            trajectory.entryProgress;
        assert.ok(Math.abs(atEdge-trajectory.entryX)<1e-10);
        assert.ok(Math.abs(yAtEdge-1)<1e-10);
    }
    const left=motion.laserTrajectory(0.08,0.35);
    const right=motion.laserTrajectory(0.92,0.35);
    assert.ok(left.originX<right.originX);
});

test("Laser geometry safely clamps non-finite and out-of-range aim input", () => {
    const samples=[
        [NaN,Infinity],[Infinity,NaN],[-8,3],[5,-3],[null,undefined]
    ];
    for(const [x,y] of samples) {
        const p=motion.laserTrajectory(x,y);
        for(const val of [p.originX,p.originY,p.aimX,p.aimY,
                          p.entryX,p.entryProgress])
            assert.ok(Number.isFinite(val));
        assert.ok(p.aimX>=0&&p.aimX<=1);
        assert.ok(p.aimY>=0&&p.aimY<=1);
        assert.ok(p.entryProgress>=0&&p.entryProgress<=1);
    }
});

test("Laser impact feedback follows bolt arrival, while shots stay immediate", () => {
    const s=createState();
    s.cleanupTechnique="hunt";
    s.huntStartRound();
    const record=s.huntTargets[0];
    assert.equal(s.huntFire(record.path,0.3,0.4),true);
    assert.equal(s.huntHitFlash,true);
    assert.equal(s.huntShots,1);
    assert.deepEqual(Array.from(s.batchPaths),[record.path]);
    assert.equal(s.called.length,0);
    // Visual only: explicit QML arrival gate ensures the world/animal
    // wash does not precede the moving projectile's collision.
    assert.match(qml, /camera\.huntHitFlash\s*&& huntLaserLayer\.impactReached/);
    assert.match(qml, /opacity: huntLaserLayer\.impactReached\s*\? 0\.40 : 0/);
    assert.match(qml, /visible: huntLaserLayer\.impactReached\s*\n\s*text: "HIT"/);
    assert.match(qml, /huntLaserLayer\.tailX/);
    assert.match(qml, /huntLaserLayer\.tailY/);
    assert.equal(s.huntUndo(),true);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.huntShotEffect,null);
});


test("Queue can be inspected and cleared from Grid, Swipe or Hunt without deleting", () => {
    const s=createState();
    s.batchToggle(files[0]);
    for(const mode of ["grid","swipe","hunt"]) {
        s.cleanupTechnique=mode;
        assert.equal(s.cleanupToggleQueue(),true);
        assert.equal(s.cleanupQueueOpen,true);
        assert.equal(s.cleanupToggleQueue(),true);
        assert.equal(s.cleanupQueueOpen,false);
        assert.deepEqual(Array.from(s.batchPaths),["/tmp/Alpha.png"]);
    }
    s.cleanupTechnique="grid";
    assert.equal(s.batchRemovePath("/tmp/not-queued"),false);
    assert.equal(s.batchRemovePath("/tmp/Alpha.png"),true);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.called.length,0);
    s.batchToggle(files[1]);
    assert.equal(s.batchClear(),true);
    assert.equal(s.batchPaths.length,0);
    assert.match(s.feedback,/NO FILES MOVED/);
    assert.equal(s.called.length,0);
});

test("Queue supports Grid review and explicit backend Trash confirmation", () => {
    const s=createState();
    s.cleanupTechnique="grid";
    s.batchToggle(files[0]);
    s.batchToggle(files[2]);
    assert.equal(s.previewBatchTrash(),true);
    assert.equal(s.cleanupQueueOpen,true);
    assert.equal(s.called.length,1);
    assert.equal(s.called[0].action,"previewBatch");
    assert.deepEqual(Array.from(s.called[0].args),[
        "preview-batch",
        JSON.stringify(["/tmp/Alpha.png","/tmp/Charlie.webp"]),
        "--folder","/tmp/CameraReview"
    ]);
    assert.equal(s.called.some(c=>c.action==="trashBatch"),false);
    s.batchPreview={planId:"synthetic-plan",count:2};
    assert.equal(s.confirmBatchTrash(),true);
    assert.equal(s.called.length,2);
    assert.equal(s.called[1].action,"trashBatch");
    assert.deepEqual(Array.from(s.called[1].args),[
        "trash-batch","synthetic-plan","MOVE_TO_TRASH"
    ]);
});

test("Review refuses stale Cleanup folder or Gallery scan", () => {
    const s=createState();
    s.batchToggle(files[0]);
    s.galleryRequestedFolder="/tmp/AnotherScope";
    assert.equal(s.previewBatchTrash(),false);
    assert.equal(s.called.length,0);
    assert.match(s.feedback,/SCAN CLEANUP FOLDER/);
    s.galleryRequestedFolder="/tmp/CameraReview";
    s.galleryRequestedView="gallery";
    assert.equal(s.previewBatchTrash(),false);
    assert.equal(s.called.length,0);
    s.galleryRequestedView="cleanup";
    assert.equal(s.previewBatchTrash(),true);
});

test("Refreshing Cleanup search/filter preserves queue, changing folder clears it", () => {
    const s=createState();
    const begin=qml.indexOf("    function loadGallery(append, targetView) {");
    const end=qml.indexOf("    function selectImage(record) {",begin);
    assert.ok(begin>0 && end>begin);
    vm.runInContext(qml.slice(begin,end),s);
    s.batchPaths=["/tmp/Alpha.png","/tmp/Bravo.mp4"];
    s.cleanupQueueOpen=true;
    s.cleanupSearchQuery="Alpha";
    s.cleanupMediaFilter="screenshots";
    assert.equal(s.loadGallery(false,"cleanup"),true);
    assert.deepEqual(Array.from(s.batchPaths),
                     ["/tmp/Alpha.png","/tmp/Bravo.mp4"]);
    assert.equal(s.cleanupQueueOpen,true);
    s.cleanupCustomFolder="/tmp/NewScopedFolder";
    assert.equal(s.loadGallery(false,"cleanup"),true);
    assert.equal(s.cleanupQueueOpen,false);
    assert.equal(s.batchPaths.length,0);
    assert.equal(s.batchReviewKey,"");
    assert.equal(s.called.some(c=>c.action==="trashBatch"),false);
});

test("Cleanup queue receipt preserves skipped/failed paths, not just a success count", () => {
    // Source contract verifies successful backend receipt does not
    // erase files that GIO could not move.
    const start=qml.indexOf('        } else if (action === "trashBatch" || action === "trashBatchNow") {');
    const end=qml.indexOf('        } else if (action === "previewSelected") {',start);
    assert.ok(start>0&&end>start);
    const code=qml.slice(start,end);
    assert.match(code,/Array\.isArray\(payload\.unmovedPaths\)/);
    assert.match(code,/payload\.unmovedPaths\.slice\(\)/);
    assert.match(code,/SKIPPED/);
    assert.match(code,/FAILED/);
    assert.match(code,/camera\.loadGallery\(false, "cleanup"\)/);
});


test("One click from any Cleanup selection mode executes a single direct Trash command", () => {
    for(const mode of ["batch","grid","swipe","hunt"]) {
        const state=createState();
        state.cleanupTechnique=mode;
        state.batchPaths=["/tmp/Alpha.png","/tmp/Bravo.mp4"];
        assert.equal(state.trashQueuedNow(),true);
        assert.equal(state.called.length,1,"one UI click must start one process");
        assert.equal(state.called[0].action,"trashBatchNow");
        assert.deepEqual(Array.from(state.called[0].args),[
            "trash-batch-now",
            JSON.stringify(["/tmp/Alpha.png","/tmp/Bravo.mp4"]),
            "MOVE_TO_TRASH","--folder","/tmp/CameraReview"
        ]);
        assert.equal(state.batchPreview,null);
        assert.equal(state.batchReviewKey,"");
        // The UI doesn't need to open the queue or request a plan.
        assert.equal(state.cleanupQueueOpen,false);
        assert.equal(state.called.some(c=>c.action==="previewBatch"),false);
        assert.equal(state.called.some(c=>c.action==="trashBatch"),false);
    }
});

test("One-click Trash fails closed for empty, busy, stale folder or Gallery scan", () => {
    const s=createState();
    assert.equal(s.trashQueuedNow(),false);
    s.batchToggle(files[0]);
    s.busy=true;
    assert.equal(s.trashQueuedNow(),false);
    s.busy=false;
    s.galleryRequestedView="gallery";
    assert.equal(s.trashQueuedNow(),false);
    s.galleryRequestedView="cleanup";
    s.cleanupCustomFolder="/tmp/OtherFolder";
    assert.equal(s.trashQueuedNow(),false);
    s.cleanupCustomFolder="/tmp/CameraReview";
    s.cleanupLoadedFolder="/tmp/AnotherFolder";
    assert.equal(s.trashQueuedNow(),false);
    assert.equal(s.called.length,0);
    assert.match(s.feedback,/SCAN CURRENT CLEANUP FOLDER FIRST/);
    s.cleanupLoadedFolder="/tmp/CameraReview";
    assert.equal(s.trashQueuedNow(),true);
    assert.equal(s.called.length,1);
});

test("Direct-trash response uses existing receipt and preserves failed paths", () => {
    const c=qml.slice(qml.indexOf("    function consume(raw) {"));
    assert.match(c,/action === "trashBatch" \|\| action === "trashBatchNow"/);
    assert.match(c,/payload\.unmovedPaths\.slice\(\)/);
    assert.match(c,/cleanupQueueOpen = batchPaths\.length > 0/);
    assert.match(c,/action === "trashBatchNow"\s*\?\s*"TRASH \/\/ NOT MOVED/);
    assert.match(c,/camera\.loadGallery\(false, "cleanup"\)/);
    assert.doesNotMatch(qml.slice(qml.indexOf("id: cleanupQueueActions"),
                          qml.indexOf("id: cleanupSearch")),/batchPreview\.count/);
});
