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

test("Zoom-only frame fit preserves guest height without the black bottom gutter", () => {
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
        'readonly property int zoomControlDeckBottom: Math.max(0, Math.round(',
        'cameraBodyColumn.y + cameraModes.y + cameraModes.height',
        'readonly property int zoomDeckReserve: Math.max(',
        'zoomControlDeckBottom + zoomDeckGap + zoomBayBottom',
        'readonly property int availableFrameHeight: Math.max(',
        'financeSize.height + zoomDeckReserve',
        'camera.activeView === "zoom"',
        'Math.min(availableFrameHeight,'
    ]) assert.ok(camera.includes(token), 'missing zoom deck budget: ' + token);
    const reserve = 12 + 37 + 2 + (8 * 2) + 42 + 3 + 1;
    const maxFrame = 1440 - 9 - 8;
    const expandedZoomFrame = Math.min(maxFrame, medium.height + reserve);
    assert.equal(reserve, 113);
    assert.equal(expandedZoomFrame, 1013);
    assert.equal(expandedZoomFrame - reserve, 900);
    // Compact's header is raised by 4px margin, 5px header, 8px spacing.
    // The 3px gap below buttons is opaque and the browser is not overlapped.
    const compactDeckEnd = 8 + 32 + 2 * 4 + 2 + 42;
    const compactBrowserTop = compactDeckEnd + 3;
    assert.equal(compactDeckEnd, 92);
    assert.equal(compactBrowserTop, 95);
    assert.equal(699 - compactBrowserTop - 1, 603);
    assert.match(camera, /readonly property int zoomDeckGap: 3/);
    assert.match(camera, /readonly property int zoomBrowserRise: 13/);
    assert.match(camera, /readonly property int zoomFrameBottomFit: 12/);
    assert.match(camera, /readonly property int zoomGuestBottomClearance: 2/);
    assert.match(camera, /readonly property int frameHeightBase:/);
    assert.match(camera, /camera\.activeView === "zoom" \? zoomFrameBottomFit : 0/);
    assert.doesNotMatch(camera, /zoomWebBottomTrim/);
    assert.match(camera, /y: camera\.zoomControlDeckBottom \+ camera\.zoomDeckGap\s*- camera\.zoomBrowserRise/);
    assert.match(camera, /frame\.height - y - camera\.zoomBayBottom\s*- camera\.zoomGuestBottomClearance/);
    assert.match(camera, /height: Math\.max\(0, camera\.zoomControlDeckBottom - y \+ 1\)/);
    // A shared frame+guest reduction cannot fix relative overflow. The
    // frame remains at the last accepted dimensions; only the guest shrinks
    // 2px more at its bottom. The opaque backing is now 3px, not 5–10px.
    const raisedTop = compactBrowserTop - 13;
    const inputTop = Math.max(raisedTop, compactDeckEnd);
    const frameFit = 12;
    const clearance = 2;
    const compactZoomFrame = 699 - frameFit;
    const expandedFittedFrame = expandedZoomFrame - frameFit;
    const fullscreenFittedFrame = 1345 - frameFit;
    assert.equal(raisedTop, 82);
    assert.equal(compactZoomFrame, 687);
    assert.equal(compactZoomFrame - raisedTop - 1 - clearance, 602);
    assert.equal(inputTop, compactDeckEnd);
    assert.equal(602 - (inputTop - raisedTop), 592);
    assert.equal(expandedFittedFrame, 1001);
    assert.equal(expandedFittedFrame - (reserve - 13) - clearance, 899);
    assert.equal(fullscreenFittedFrame, 1333);
    assert.equal(fullscreenFittedFrame - 99 - 1 - clearance, 1231);
    assert.equal(compactZoomFrame - (raisedTop + 602), 3);
    assert.equal(expandedFittedFrame - (99 + 899), 3);
    assert.equal(fullscreenFittedFrame - (99 + 1231), 3);
    assert.doesNotMatch(camera, /zoomTopNudge/);
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
    const reserve = 113;
    // Fullscreen retains Finance's baseline instead of growing into the
    // physical output area reserved by Sway's top panel.
    assert.match(camera, /camera.activeView === "zoom" && chassisLevel === "expanded"/);
    for (const [width, height] of [[2560,1440],[1920,1080],[1360,768]]) {
        const base = policy.frame("fullscreen", width, height, 12, 9, 8);
        const available = height - 9 - 8;
        const zoomFrame = Math.max(1, base.height - 10);
        assert.equal(zoomFrame, base.height - 10);
        assert.ok(zoomFrame <= available);
    }
    const workareaTop = 82; // DP-3's operator-verified Sway workarea origin
    const baselineBrowserBottom = workareaTop + 9 + full.height - 1;
    assert.equal(baselineBrowserBottom, 1435);
    // The Zoom-only 10px frame fit makes this even safer.
    const fittedZoomBottom = workareaTop + 9 + (full.height - 10) - 1;
    assert.equal(fittedZoomBottom, 1425);
    const rejectedFrame = Math.min(1440 - 9 - 8, full.height + reserve);
    assert.equal(rejectedFrame, 1423);
    assert.equal(workareaTop + 9 + rejectedFrame - 1, 1513);
    assert.ok(fittedZoomBottom <= 1440);
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

test("Camera's transparent Zoom frame seals its inner 2px perimeter but leaves desktop outside frame untouched", () => {
    const frame = camera.split("WindowPanelFrame {", 2)[1];
    assert.ok(frame, "Camera's frame exists");
    assert.match(frame, /fillOpacity: camera\.zoomWebVisualHeld \? 0\.0 : 0\.97/);
    assert.match(frame, /clipContent: camera\.zoomWebVisualHeld/);
    for (const id of ["zoomWebLeftEdgeSeal", "zoomWebRightEdgeSeal"]) {
        assert.ok(frame.includes("id: " + id), "missing perimeter: " + id);
    }
    const left = frame.split("id: zoomWebLeftEdgeSeal", 2)[1].split("id: zoomWebRightEdgeSeal", 2)[0];
    const right = frame.split("id: zoomWebRightEdgeSeal", 2)[1].split("id: zoomViewport", 2)[0];
    assert.ok(left.includes("width: Math.max(0, camera.zoomActorLeft)"));
    assert.ok(right.includes("width: Math.max(0, frame.width - x)"));
    assert.ok(right.includes("x: camera.zoomActorLeft + camera.zoomActorWidth"));
    assert.ok(left.includes("visible: camera.zoomWebVisualHeld"));
    assert.ok(right.includes("visible: camera.zoomWebVisualHeld"));
    for (const [width, height, top] of [[784,687,82],[1000,1001,99],[2536,1333,99]]) {
        const inset = 2, browserWidth = width - 2 * inset;
        const browserBottom = height - 3;
        assert.equal(inset + browserWidth + inset, width);
        assert.equal(top + (browserBottom - top) + 3, height);
    }
    assert.match(camera, /readonly property int zoomBrowserRise: 13/);
    assert.match(camera, /intersection: Intersection\.Subtract/);
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
