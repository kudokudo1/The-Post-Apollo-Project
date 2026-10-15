#!/usr/bin/env python3
"""F2 VALUE selector opt-in source and numeric boundary contract.

Static checks do not replace a QML engine/runtime test. The arithmetic
examples below independently check the specified normalized geometry.
"""
from pathlib import Path
from math import isclose

ROOT = Path(__file__).resolve().parents[2]
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
demo = (ROOT / "tests/fixtures/SelectorSliderValueDemo.qml").read_text(encoding="utf-8")
shell = (ROOT / "tests/selector-value/shell.qml").read_text(encoding="utf-8")

# Safe defaults: no existing selector silently migrates to numeric mode.
assert 'property string selectorProfile: "index"' in slider
assert 'property string indexInteraction: "legacy"' in slider
assert 'property bool previewGestureActive: false' in slider
assert 'selectorProfile: "value"' not in git
assert 'selectorProfile: "value"' not in hospital
assert 'LIVE REPO //' not in git and 'LIVE REMOTE //' not in git
assert 'LIVE FLOOR // OFF' in hospital

# The F2 owner owns real value acknowledgment; visual motion never performs
# an external action or pretends that a requested value was accepted.
for token in (
    'signal valueRequested(real value)',
    'property real minimumValue: 0',
    'property real maximumValue: 100',
    'property real currentValue: 0',
    'readonly property bool validValueDomain:',
    'function clampedValue(value)',
    'function valueForHandleY(y)',
    'function handleYForValue(value)',
    'function requestDragValue(handleY)',
    'function stepValue(direction)',
    'slider.valueText(slider.currentValue)',
    'id: valueFill',
    'valueDecimals',
    'valueSuffix',
    'slider.valueDragHandleY',
):
    assert token in slider, token
assert 'selectorProfile: "value"' in demo
assert demo.count('selectorProfile: "value"') == 2
assert 'Fixtures.SelectorSliderValueDemo' in shell
assert 'GitService' not in demo and 'HospitalFloorService' not in demo

# Legacy INDEX is still intact, including live change on pointer travel and
# the selected REMOTE activity-point decorations.
assert 'slider.indexRequested(index);' in slider
assert 'slider.activityPoints || []' in slider
assert 'root.remoteActivityPoints()' in git
assert 'gitService.selectRepo(index);' in git
assert 'gitService.selectRemote(index);' in git

# Numeric contract: min is at the bottom, max at the top; values stay
# bounded even for out-of-track pointers. Domain collapse disables input.
def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

def y_for_value(value: float, minimum: float, maximum: float, travel: float) -> float:
    return travel * (1 - ((clamp(value, minimum, maximum) - minimum)
                         / (maximum - minimum)))

def value_for_y(y: float, minimum: float, maximum: float, travel: float) -> float:
    return minimum + (1 - clamp(y, 0, travel) / travel) * (maximum - minimum)

for lo, hi, travel in ((0, 100, 165), (-40, 160, 170), (0.0, 1.0, 210)):
    assert isclose(y_for_value(lo, lo, hi, travel), travel)
    assert isclose(y_for_value(hi, lo, hi, travel), 0)
    assert isclose(value_for_y(-100, lo, hi, travel), hi)
    assert isclose(value_for_y(travel + 100, lo, hi, travel), lo)
    for value in (lo, (lo + hi) / 2, hi):
        y = y_for_value(value, lo, hi, travel)
        assert isclose(value_for_y(y, lo, hi, travel), value)

print("SELECTOR F2 VALUE // STATIC + NUMERIC GEOMETRY CONTRACT PASS")
