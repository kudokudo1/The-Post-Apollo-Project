#!/usr/bin/env python3
"""F5 RANGE source, boundary geometry and compatibility contracts.

This is a static/numeric check, not an actual Quickshell pointer test.
"""
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
surface = (ROOT / "components/SelectorRangeSurface.qml").read_text(encoding="utf-8")
qmldir = (ROOT / "components/qmldir").read_text(encoding="utf-8")
fixture = (ROOT / "tests/fixtures/SelectorSliderRangeDemo.qml").read_text(encoding="utf-8")
shell = (ROOT / "SelectorRangeTest.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
value_fixture = (ROOT / "tests/fixtures/SelectorSliderValueDemo.qml").read_text(encoding="utf-8")
step_fixture = (ROOT / "tests/fixtures/SelectorSliderStepDemo.qml").read_text(encoding="utf-8")

# All previously accepted profiles and production uses remain intact.
assert 'property string selectorProfile: "index"' in slider
assert 'readonly property bool valueMode: selectorProfile === "value"' in slider
assert 'readonly property bool stepMode: selectorProfile === "step"' in slider
assert 'readonly property bool rangeMode: selectorProfile === "range"' in slider
assert 'property string indexInteraction: "legacy"' in slider
assert 'function requestDragValue(handleY)' in slider
assert 'function requestStepDelta(direction)' in slider
assert 'property bool previewGestureActive: false' in slider
assert 'SelectorRangeSurface 1.0 SelectorRangeSurface.qml' in qmldir
assert 'id: rangeSurface' in slider
assert 'visible: !slider.rangeMode' in slider
assert 'enabledControl: slider.enabledSlider && slider.rangeMode' in slider
assert 'rangeRequested(real lower, real upper)' in slider
assert 'onRangeRequested: function(lower, upper)' in slider
assert 'readonly property bool rangePreviewActive:' in slider
assert 'readonly property real rangePreviewLower:' in slider
assert 'readonly property real rangePreviewUpper:' in slider
assert 'gitService.selectRepo(index);' in git
assert 'gitService.selectRemote(index);' in git
assert 'LIVE FLOOR // OFF' in hospital
assert 'selectorProfile: "range"' not in git
assert 'selectorProfile: "range"' not in hospital
assert 'selectorProfile: "range"' not in (ROOT / "shell.qml").read_text()
assert value_fixture.count('selectorProfile: "value"') == 2
assert step_fixture.count('selectorProfile: "step"') == 2

# Standalone harness must be at config root (prior nested shell broke imports).
assert 'import "tests/fixtures" as Fixtures' in shell
assert 'Fixtures.SelectorSliderRangeDemo' in shell
assert fixture.count('selectorProfile: "range"') == 2
assert 'GitService' not in fixture
assert 'HospitalFloorService' not in fixture

# Distinct handles, selection display and whole interval manipulation.
for needle in (
    'id: lowerThumb', 'id: upperThumb', 'id: selectedBand',
    'text: "LO"', 'text: "HI"',
    'readonly property real displayLower:', 'readonly property real displayUpper:',
    'property bool dragActive: false', 'property bool committing: false',
    'function beginPointer(mouse)', 'function updatePointer(y)',
    'function finishPointer()', 'function cancelPreview()',
    'dragTarget = "whole"', 'dragTarget = "lower"',
    'dragTarget = "upper"', 'const forceWhole =',
    'const width = initialUpper - initialLower',
    'candidateUpper = candidateLower + width;',
    'candidateLower = Math.min(target, initialUpper);',
    'candidateUpper = Math.max(target, initialLower);',
    'rangeRequested(low, high);', 'Keys.onEscapePressed:',
    'Keys.onLeftPressed:', 'Keys.onRightPressed:',
    'Keys.onUpPressed:', 'Keys.onDownPressed:',
):
    assert needle in surface, needle

# Only one owner request on release, with preview held through synchronous echo.
commit = surface.split('function finishPointer()', 1)[1].split(
    'function stepTarget(direction)', 1
)[0]
assert commit.count('rangeRequested(low, high);') == 1
assert commit.index('committing = true;') < commit.index(
    'rangeRequested(low, high);') < commit.index('committing = false;')
assert commit.index('rangeRequested(low, high);') < commit.index(
    'dragActive = false;')

# Numeric contract: both ends clamp, hard collision allows equal values.
# Moving the entire interval translates it without altering its width.
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def set_lower(target, lo, hi, owner_high):
    return min(clamp(target, lo, hi), owner_high), owner_high

def set_upper(target, lo, hi, owner_low):
    return owner_low, max(clamp(target, lo, hi), owner_low)

def move_whole(start_lo, start_hi, delta, lo, hi):
    span = start_hi - start_lo
    low = clamp(start_lo + delta, lo, hi - span)
    return low, low + span

for domain_min, domain_max, left, right in (
    (0, 100, 20, 75),
    (-40, 80, -15, 45),
    (0, 1, 0.2, 0.8),
    (0, 100, 50, 50),
):
    assert set_lower(domain_max + 999, domain_min, domain_max, right) == (right, right)
    assert set_upper(domain_min - 999, domain_min, domain_max, left) == (left, left)
    for delta in (-9999, -11.5, 0, 6.25, 9999):
        a, b = move_whole(left, right, delta, domain_min, domain_max)
        assert domain_min <= a <= b <= domain_max
        assert isclose(b - a, right - left, abs_tol=1e-9)
    assert move_whole(left, right, -9999, domain_min, domain_max)[0] == domain_min
    assert move_whole(left, right, 9999, domain_min, domain_max)[1] == domain_max

print("SELECTOR F5 RANGE // STATIC + HARD COLLISION + WHOLE SPAN PASS")
