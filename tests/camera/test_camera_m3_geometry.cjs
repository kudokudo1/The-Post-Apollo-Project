#!/usr/bin/env node
"use strict";
// Source-only contract plus executable Finance geometry policy. No QML
// application launch or user's images/files. Native rendering is separate.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const camera = read("widgets/CameraW.qml");
const viewer = read("components/CameraImageViewer.qml");
const shell = read("shell.qml");
const finance = read("widgets/FinanceW.qml");
const financePolicy = read("widgets/FinanceChassisPolicy.js");
const policy = vm.createContext({});
vm.runInContext(financePolicy.replace(/^\s*\.pragma library\s*$/m, ""), policy);

test("Camera compact retains its size; Zoom expanded reserves deck height beyond Finance's 1000x900 content baseline", () => {
    assert.match(camera, /property string chassisLevel: "compact"/);
    assert.match(camera, /chassisLevel === "compact"\s*\? Math\.max\(1, Math\.min\(784,/);
    assert.match(camera, /chassisLevel === "compact"\s*\? Math\.max\(1, Math\.min\(699, availableFrameHeight\)\)/);
    assert.match(camera, /FinanceChassisPolicy\.frame\(\s*chassisLevel, viewportWidth, viewportHeight,/);
    assert.match(camera, /: financeSize\.width/);
    assert.match(camera, /: financeSize\.height/);
    assert.match(camera, /FinanceChassisPolicy\.step\(chassisLevel, 1\)/);
    assert.match(camera, /FinanceChassisPolicy\.step\(chassisLevel, -1\)/);
    const medium = policy.frame("expanded", 2560, 1440, 12, 9, 8);
    assert.equal(medium.width, 1000);
    assert.equal(medium.height, 900);
    // Camera preserves Finance's 900px *browser content* baseline when
    // there is screen room. Its fixed-height deck is reserved separately.
    for (const token of [
        'readonly property int zoomDeckReserve: Math.max(0, Math.round(',
        'cameraBodyColumn.y + cameraModes.y + cameraModes.height',
        '+ zoomBayBottom))',
        'readonly property int availableFrameHeight: Math.max(',
        'financeSize.height + zoomDeckReserve',
        'camera.activeView === "zoom"',
        'Math.min(availableFrameHeight,'
    ]) assert.ok(camera.includes(token), 'missing zoom deck budget: ' + token);
    const reserve = 12 + 37 + 2 + (8 * 2) + 42 + 1;
    const maxFrame = 1440 - 9 - 8;
    const expandedZoomFrame = Math.min(maxFrame, medium.height + reserve);
    assert.equal(reserve, 110);
    assert.equal(expandedZoomFrame, 1010);
    assert.equal(expandedZoomFrame - reserve, 900);
    assert.match(camera, /zoomTopNudge: chassisLevel === "compact" \? 17 : 0/);
    assert.equal(policy.step("compact", 1), "expanded");
    assert.equal(policy.step("expanded", 1), "fullscreen");
    assert.equal(policy.step("fullscreen", -1), "expanded");
});

test("Camera uses Finance's baseline fullscreen width/height outside Zoom; Zoom extra deck is bounded to output", () => {
    assert.match(finance, /FinanceChassisPolicy\.frame\(/);
    assert.match(camera, /FinanceChassisPolicy\.frame\(/);
    assert.match(camera, /readonly property int glowGutter: 12/);
    assert.match(camera, /readonly property int frameTopInset: 9/);
    assert.match(camera, /readonly property int bottomScreenGap: 8/);
    for (const [w,h] of [[2560,1440],[1360,768],[1920,1080],[3440,1440]]) {
        const f = policy.frame("fullscreen", w, h, 12, 9, 8);
        assert.equal(f.width, w - 24);
        assert.equal(f.height, Math.min(h - 17, 1345));
    }
    const full = policy.frame("fullscreen", 2560, 1440, 12, 9, 8);
    assert.equal(full.width, 2536);
    assert.equal(full.height, 1345);
    const reserve = 110;
    for (const [width, height] of [[2560,1440],[1920,1080],[1360,768]]) {
        const base=policy.frame("fullscreen",width,height,12,9,8);
        const available=height-9-8;
        const zoomFrame=Math.min(available,base.height+reserve);
        assert.ok(zoomFrame>=base.height);
        assert.ok(zoomFrame<=available);
    }
    assert.match(camera, /: financeSize\.height/);
    assert.match(camera, /FinanceChassisPolicy\.leftMargin\(/);
    assert.match(camera, /top: 0/);
    assert.doesNotMatch(camera, /top: 94/);
    assert.match(camera, /y: camera\.frameTopInset/);
    assert.match(camera, /anchors\.topMargin: camera\.frameTopInset/);
    assert.match(camera, /anchors\.bottomMargin: camera\.bottomScreenGap/);
    assert.match(camera, /frameHeight \+ frameTopInset \+ bottomScreenGap/);
    assert.match(shell, /id: cameraWindow[\s\S]*?dockCenterX: shellRoot\.margins\.left \+ leftModules\.x/);
});

test("Header has Finance-style independent down/up size controls and close", () => {
    assert.match(camera, /id: cameraCollapseButton/);
    assert.match(camera, /label: "↓"/);
    assert.match(camera, /available: camera\.chassisLevel !== "compact"/);
    assert.match(camera, /onLeftClicked: camera\.collapseChassis\(\)/);
    assert.match(camera, /id: cameraExpandButton/);
    assert.match(camera, /label: "↑"/);
    assert.match(camera, /available: camera\.chassisLevel !== "fullscreen"/);
    assert.match(camera, /onLeftClicked: camera\.expandChassis\(\)/);
    assert.match(camera, /label: "X"/);
    assert.match(camera, /onLeftClicked: camera\.menuOpen = false/);
    assert.match(camera, /visible: camera\.menuOpen/);
    assert.match(camera, /width: camera\.menuOpen \? camera\.frameWidth : 0/);
    assert.match(camera, /height: camera\.menuOpen \? camera\.frameHeight : 0/);
});

test("Viewer consumes wheel for zoom; left drag pans x and y, not wheel scroll", () => {
    assert.match(viewer, /Flickable \{/);
    assert.match(viewer, /interactive: false/);
    assert.match(viewer, /MouseArea \{/);
    assert.match(viewer, /anchors\.fill: viewport/);
    assert.match(viewer, /acceptedButtons: Qt\.LeftButton/);
    assert.match(viewer, /onWheel: function\(wheel\)/);
    assert.match(viewer, /wheel\.accepted = true/);
    assert.match(viewer, /viewer\.changeZoom\(delta > 0 \? 1\.25 : 0\.8,/);
    assert.match(viewer, /onPressed: function\(mouse\)/);
    assert.match(viewer, /onPositionChanged: function\(mouse\)/);
    assert.match(viewer, /viewport\.contentX = Math\.max/);
    assert.match(viewer, /viewport\.contentY = Math\.max/);
    assert.match(viewer, /viewer\.zoom <= 1\.001/);
    assert.match(viewer, /function reset\(\)/);
    assert.match(viewer, /onSourceChanged: reset\(\)/);
    assert.doesNotMatch(viewer, /WheelHandler \{/);
});
