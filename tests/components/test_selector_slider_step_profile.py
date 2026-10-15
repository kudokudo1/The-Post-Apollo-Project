#!/usr/bin/env python3
"""F3 STEP profile static, quantization, compatibility, and fixture contracts.

These checks are not substitutes for real Quickshell pointer/runtime testing.
"""
from math import ceil, floor, isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
value_demo = (ROOT / "tests/fixtures/SelectorSliderValueDemo.qml").read_text(encoding="utf-8")
step_demo = (ROOT / "tests/fixtures/SelectorSliderStepDemo.qml").read_text(encoding="utf-8")
step_shell = (ROOT / "SelectorStepTest.qml").read_text(encoding="utf-8")

assert 'property string selectorProfile: "index"' in slider
assert 'readonly property bool stepMode: selectorProfile === "step"' in slider
assert 'readonly property bool numericMode: valueMode || stepMode' in slider
assert 'property string indexInteraction: "legacy"' in slider
assert 'readonly property bool validStepDomain:' in slider
assert 'property bool stepGestureActive: false' in slider
assert 'readonly property bool stepPreviewActive:' in slider
assert 'function stepValueForHandleY(y)' in slider
assert 'function stepValueAtIndex(index)' in slider
assert 'function stepIndexForValue(value)' in slider
assert 'function requestStepDelta(direction)' in slider
assert 'function cancelStepPreview()' in slider
assert 'slider.pendingStepValue = slider.stepValueForHandleY(' in slider
assert 'slider.cancelStepPreview();' in slider
assert 'slider.valueRequested(next);' in slider
assert 'visible: slider.numericMode' in slider
assert 'readonly property real tickValue:' in slider
assert 'slider.handleYForValue(tickValue)' in slider
assert 'easing.type: slider.stepMode' in slider
assert 'selectorProfile: "step"' not in git
assert 'selectorProfile: "step"' not in hospital
assert 'gitService.selectRepo(index);' in git
assert 'gitService.selectRemote(index);' in git
assert 'LIVE FLOOR // OFF' in hospital
assert value_demo.count('selectorProfile: "value"') == 2
assert step_demo.count('selectorProfile: "step"') == 2
assert 'import "tests/fixtures" as Fixtures' in step_shell
assert 'Fixtures.SelectorSliderStepDemo' in step_shell
assert 'GitService' not in step_demo and 'HospitalFloorService' not in step_demo
assert 'selectorProfile: "step"' not in (ROOT / "shell.qml").read_text()

release = slider.split('onReleased: {', 1)[1].split('onCanceled: {', 1)[0]
assert release.index('slider.valueRequested(next);') < release.index(
    'slider.stepGestureActive = false;'
)
assert 'stepMode && stepGestureActive' in slider  # external owner invalidates a preview

def detents(lo: float, hi: float, increment: float) -> list[float]:
    count = ceil((hi - lo) / increment - 1e-9) + 1
    return [min(hi, lo + increment * n) for n in range(count)]

def nearest(value: float, entries: list[float]) -> float:
    return min(entries, key=lambda x: abs(x - value))

for lo, hi, increment in (
    (0, 100, 10),
    (-40, 160, 25),
    (0, 1, .2),
    (0, 95, 20),  # final shorter endpoint detent must be selectable
):
    entries = detents(lo, hi, increment)
    assert isclose(entries[0], lo)
    assert isclose(entries[-1], hi)
    assert all(a < b for a, b in zip(entries, entries[1:]))
    assert isclose(nearest(lo - 999, entries), lo)
    assert isclose(nearest(hi + 999, entries), hi)
    for index, val in enumerate(entries):
        assert isclose(nearest(val, entries), val)
        assert lo <= val <= hi
        if index:
            assert val > entries[index - 1]
assert detents(0, 95, 20) == [0, 20, 40, 60, 80, 95]

print("SELECTOR F3 STEP // STATIC + DETENT NUMERIC CONTRACT PASS")
