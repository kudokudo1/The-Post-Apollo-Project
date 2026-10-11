#!/usr/bin/env python3
"""Source contracts for operator-approved icon identities and Hunter interactions.

This is a structural check, not Quickshell runtime/rendering certification.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
app = (ROOT / "widgets/AppControlW.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hunter = (ROOT / "widgets/appcontrol/HunterControls.qml").read_text(encoding="utf-8")
overlay = (ROOT / "widgets/appcontrol/DestructiveConfirmOverlay.qml").read_text(encoding="utf-8")
task_manager = (ROOT / "widgets/appcontrol/TaskManagerView.qml").read_text(encoding="utf-8")
cpu = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")


def region(text, first, last):
    start = text.index(first)
    stop = text.index(last, start + len(first))
    return text[start:stop]


# Preserve semantic differences between the two six-button rails.
git_local = region(git, "id: gitModeButtonRow", "id: githubPage")
git_remote = region(git, "id: githubModeButtonRow", "id: githubModeMouse")
for glyph in ("🛠", "", "⚖", "࣪⋅˚🕮‧₊˚", "ﮩ٨✮ﮩ٨ـ", "🏗"):
    assert 'symbol: "' + glyph + '"' in git_local, glyph
for glyph in ("🖨", "🗄", "✮˙๋࣭⭑", "🗠",
              "⭒˗ˏˋ๋࣭⚠︎๋࣭⭑ˊ˗", "◀~~~~~~~~▶"):
    assert 'symbol: "' + glyph + '"' in git_remote, glyph

# Four SSH-specific surfaces use the full identity. The unrelated tab
# fallback deliberately retains the compact character.
assert 'symbol: "⌁⋆˚☾⭒"' in app
assert '"⌁⋆˚☾⭒ CONFIG"' in app
assert 'icon: "⌁⋆˚☾⭒"' in app
assert 'selectedAppIdentity.showingFile' in app
assert ': "⌁⋆˚☾⭒"' in app
assert 'return "⌁";' in app

# Click pulse, menu ownership, and background operation are distinct.
rail = region(app, "id: modeRail", "id: searchHeader")
assert 'killRailFirePulse' in rail
assert 'appControlWindow.fireKillRailOnce()' in rail
assert '(=ᗜ=)デ╾━' in rail
assert 'ദ്ദി(-_•)︻デ═一' in rail
assert 'favoritesKillFilterFirePulse' in app
assert 'favoritesKillViewFireMode' in app
assert 'fireFavoritesKillViewOnce(modelData.value)' in app
assert 'favoritesKillFilterFireTimer.restart()' in app

assert 'property bool clickFirePulse: false' in hunter
assert 'killViewFireTimer.restart()' in hunter
assert 'killBottomFireTimer.restart()' in hunter
assert 'readonly property bool menuOwned:' in hunter
assert 'controller.destructiveConfirmOpen' in hunter
assert 'controller.destructiveConfirmKind === ownedConfirmKind' in hunter
assert 'pressed || clickFirePulse' in hunter
assert 'operationFiring' not in hunter
assert 'controller.hunterOperationActive' in hunter  # running status still matters for eligibility
for action in ("requestKillAllEligibleTasks()", "requestKillHogs()", "requestKillMice()"):
    assert 'controller.' + action in hunter

# Individual destructive detail actions must retain a visible click pulse.
for name in ("hiddenKillAction", "appKillAction", "windowKillAction",
             "runKillAction", "tabCloseActionBelowFreeze"):
    assert "id: " + name + "FireTimer" in app, name
    assert name + ".clickFirePulse = true;" in app, name
assert "id: taskEndFireTimer" in task_manager
assert "taskEndAction.clickFirePulse = true;" in task_manager

# The confirmation title carries the opening shot and stays armed afterward.
assert 'property bool openingKillFirePulse: false' in overlay
assert 'openingKillFireTimer.restart()' in overlay
assert 'const armed = firing ? "(=ᗜ=)デ╾━' in overlay
assert ' : "ദ്ദി(-_•)デ╾━"' in overlay

# Preserve special cases: Kill-themed CLOSE TAB and CPU++ SWAP.
assert 'text: "\\"CLOSE\\" TAB"' in app
assert 'tabCloseActionBelowFreeze' in app
assert 'symbol: "⇄"' in cpu
assert 'text: "(-_•)︻デ═一"' not in app  # source uses reactive mode text now
print("Post-Apollo icon grammar static contracts: PASS")
