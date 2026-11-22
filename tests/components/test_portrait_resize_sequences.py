#!/usr/bin/env python3
"""Exercise Finance's actual JS resize policy and Time's TASKS portrait ratios.

Runs without Quickshell, credentials, writes, financial services or desktop
activation. Native layer-shell acceptance is a separate operator check.
"""
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
finance_policy = ROOT / "widgets/FinanceChassisPolicy.js"
time = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
tasks = (ROOT / "widgets/TasksChassisPolicy.js").read_text(encoding="utf-8")

# Keep the same three numeric portrait targets and Tasks' 0.58 width ceiling.
time_steps = re.search(
    r"readonly property var resizeSteps:\s*\[(.*?)\]", time, re.S
)
assert time_steps, "TimeW missing resizeSteps"
steps = [
    tuple(map(int, pair))
    for pair in re.findall(r"\{\s*width:\s*(\d+),\s*height:\s*(\d+)\s*\}",
                           time_steps.group(1))
]
assert steps == [(432, 790), (560, 1020), (760, 1345)], steps
assert "Math.floor(frameHeight * 0.58)" in time
assert "Math.floor(height * 0.58)" in tasks
assert "frameHeight + frameTopInset + glowGutter" in time
assert "visible: true" in time
for screen_w, screen_h in ((2560, 1440), (1360, 768), (900, 900)):
    for target_w, target_h in steps:
        height = min(target_h, max(1, screen_h - 9 - 12))
        width = min(target_w, max(1, math.floor(height * 0.58)),
                    max(1, screen_w - 13 - 24))
        assert 0 < width <= screen_w
        assert 0 < height <= screen_h
        assert width <= math.floor(height * 0.58)
assert steps[0] == (432, 790), "compact Time identity must be unchanged"

# Run the real QML-compatible JavaScript, not a Python reimplementation.
# Only the harmless '.pragma library' QML directive is stripped for Node.
js = r'''
const fs = require("fs"), vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8")
    .replace(/^\.pragma library[^\n]*\n/, "");
const context = {};
vm.createContext(context);
vm.runInContext(source, context, {timeout: 1000});
const levels = Array.from(context.financeLevels);
const cameraLevels = Array.from(context.levels);
let stage = "compact", forward = [stage];
for (let i = 0; i < 5; i++) {
    stage = context.step(stage, 1, "finance");
    forward.push(stage);
}
let backward = [stage];
for (let i = 0; i < 5; i++) {
    stage = context.step(stage, -1, "finance");
    backward.push(stage);
}
const profiles = levels.map(l => context.frame(l, 2560, 1440, 12, 9, 8, "finance"));
const compactScreen = levels.map(l => context.frame(l, 900, 768, 12, 9, 8, "finance"));
const cameraExpanded = context.frame("expanded", 2560, 1440, 12, 9, 8);
const cameraNext = context.step("expanded", 1);
console.log(JSON.stringify({levels, cameraLevels, cameraNext, cameraExpanded, forward, backward, profiles, compactScreen}));
'''
p = subprocess.run(
    ["node", "-e", js, str(finance_policy)],
    check=True, capture_output=True, text=True, timeout=15,
)
actual = json.loads(p.stdout)
assert actual["levels"] == [
    "compact", "expanded", "tall", "large", "fullscreen"
], actual["levels"]
assert actual["cameraLevels"] == ["compact", "expanded", "fullscreen"]
assert actual["cameraNext"] == "fullscreen"
assert actual["cameraExpanded"] == {"width": 1000, "height": 900}
assert actual["forward"] == [
    "compact", "expanded", "tall", "large", "fullscreen", "fullscreen"
], actual["forward"]
assert actual["backward"] == [
    "fullscreen", "large", "tall", "expanded", "compact", "compact"
], actual["backward"]
assert [(p["width"], p["height"]) for p in actual["profiles"]] == [
    (432, 790), (1000, 790), (1000, 1020), (1000, 1345),
    (2536, 1345)
], actual["profiles"]
for p in actual["compactScreen"]:
    assert 0 < p["width"] <= 876
    assert 0 < p["height"] <= 751

finance = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
assert "chassisLevel = FinanceChassisPolicy.step(chassisLevel, 1, "finance");" in finance
assert "chassisLevel = FinanceChassisPolicy.step(chassisLevel, -1, "finance");" in finance
assert 'glowGutter, frameTopInset, bottomScreenGap, "finance"' in finance
assert "implicitHeight: frameHeight + frameTopInset + bottomScreenGap" in finance
assert "property string selectorPreviewActive:" in finance
assert "visible: true" in finance
print("Time portrait and Finance five-step actual JS resize policy: PASS")
