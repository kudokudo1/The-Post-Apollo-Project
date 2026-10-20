#!/usr/bin/env node
// Static safety contracts for the QML headless-controller bridge.
// Runtime Quickshell and a real MPD service still require on-device testing.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = path.resolve(__dirname, "../..");
const deck = fs.readFileSync(path.join(base, "widgets/MediaDeckW.qml"), "utf8");
const bridge = fs.readFileSync(path.join(base, "services/media/HeadlessMediaController.qml"), "utf8");

test("deck uses persistent CLI bridge, never detached mpc for MPD", () => {
    assert.match(deck, /HeadlessMediaController\s*\{\s*id:\s*headless/);
    assert.match(deck, /headless\.transport\(action\)/);
    assert.doesNotMatch(deck, /Quickshell\.execDetached/);
    assert.doesNotMatch(deck, /\[\s*["']mpc["']/);
});

test("MPRIS transport is kept explicitly separate", () => {
    assert.match(deck, /if\s*\(transportMode\s*===\s*"mpris"\)/);
    assert.match(deck, /mediaAdapter\.run\(action\)/);
    assert.match(deck, /transportMode:\s*"mpd"/);
});

test("radio station load is explicit and does not autoplay", () => {
    assert.match(deck, /onClicked:\s*headless\.loadRadio\(deck\.radioStreamUrl\)/);
    assert.match(bridge, /issue\("load",\s*\["--source",\s*"direct-stream",\s*"--uri",\s*url\]\)/);
    assert.doesNotMatch(bridge, /--autoplay/);
    assert.match(deck, /LOAD DOES NOT AUTOPLAY/);
    assert.match(bridge, /Quickshell\.shellPath\("scripts\/media\/media_controller_cli\.py"\)/);
});

test("controller response determines UI status, not command launch", () => {
    assert.match(bridge, /JSON\.parse\(String\(raw\s*\|\|\s*""\)\)/);
    assert.match(bridge, /if\s*\(!payload\.ok\)/);
    assert.match(bridge, /snapshot\s*=\s*payload\.result/);
    assert.match(bridge, /ownsPlayback:/);
    assert.match(deck, /headless\.ownsPlayback/);
});

test("UI polling follows deck visibility; backend survives closure", () => {
    assert.match(deck, /polling:\s*deck\.menuOpen\s*&&\s*deck\.transportMode\s*===\s*"mpd"/);
    assert.match(bridge, /running:\s*bridge\.polling/);
    assert.doesNotMatch(bridge, /systemctl|pkill|killall|set-volume|wpctl|pactl|cava|\.stop\(\)/i);
});

test("live streams disallow seek/next and transport requires ownership", () => {
    assert.match(deck, /!headless\.loaded\.item\.live/);
    assert.match(deck, /headless\.ownsPlayback/);
    assert.match(deck, /enabled:\s*transportKey\.canControl/);
    assert.match(deck, /!headless\.busy/);
});

test("original browser audio experiment remains isolated to MPRIS", () => {
    assert.match(deck, /transportMode\s*!==\s*"mpris"/);
    assert.match(deck, /enabled:\s*deck\.transportMode\s*===\s*"mpris"/);
    assert.match(deck, /audioProbe\.refresh\(\)/);
});
