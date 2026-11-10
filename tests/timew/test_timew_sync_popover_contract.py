#!/usr/bin/env python3
"""TimeW mode title + local resync menu regression contracts (source only)."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text()
service = (root / "services/time/TimeSettings.qml").read_text()
settings = (root / "widgets/TimeSettingsPane.qml").read_text()

assert 'readonly property string headingModeName:' in qml
assert 'selectedMode === "calc" ? "CALCULATOR" : selectedName' in qml
assert 'text: "TIME // " + timew.headingModeName' in qml
assert 'text: "TIME // W"' not in qml
for mode in ('"clock"', '"calc"', '"tools"', '"machine"', '"planned"', '"settings"'):
    assert mode in qml
assert 'fontSizeMode: Text.HorizontalFit' in qml

button = qml.split('id: syncButton', 1)[1].split('id: closeButton', 1)[0]
assert 'onLeftClicked: timew.toggleSyncPopover()' in button
assert 'timew.chooseMode(' not in button
assert 'TimeSettings.requestResync()' not in button
assert 'TimeSettings.resyncStatus !== "working"' not in button

popup = qml.split('id: syncPopover', 1)[1].split('id: chassis', 1)[0]
assert 'visible: timew.syncPopoverOpen && timew.menuOpen' in popup
assert 'z: 100' in popup
assert 'syncButton.mapToItem(timewFrame,' in popup
assert 'text: "RESYNC // HOST TIME"' in popup
for label in ('"CONFIRM RESYNC"', '"CANCEL"', '"CLOSE"', '"DIAGNOSE"', '"CHECK TIME"'):
    assert label in popup, label
for call in ('TimeSettings.requestResync()', 'TimeSettings.diagnoseResync()',
             'TimeSettings.checkTimeAccuracy()', 'timew.closeSyncPopover()'):
    assert call in popup, call
assert 'available: TimeSettings.resyncConfirmRequired' in popup
assert '&& !TimeSettings.authSessionActive' in popup
assert '&& !TimeSettings.resyncAuthPending' in popup
assert 'CONFIRM CONTACTS TIME SERVERS (IP VISIBLE)' in popup
assert 'CORRECTION MAY CHANGE SYSTEM / FILE TIMES.' in popup
assert 'TimeSettings.resyncMessage' in popup
assert 'TimeSettings.diagnosticMessage' in popup
assert 'timew.chooseMode(' not in popup
assert 'TimeSettings.prepareResync()' not in popup

funcs = qml.split('function closeSyncPopover()', 1)[1].split('function toggleSyncPopover()', 1)[0]
assert 'TimeSettings.cancelResync();' in funcs
toggle = qml.split('function toggleSyncPopover()', 1)[1].split('function toggle()', 1)[0]
assert 'TimeSettings.prepareResync();' in toggle
assert 'TimeSettings.requestResync();' not in toggle
assert 'syncPopoverOpen = true;' in toggle
assert 'if (syncPopoverOpen)' in toggle
assert 'if (!menuOpen)' in qml and 'closeSyncPopover();' in qml
assert 'if (syncPopoverOpen)\n            closeSyncPopover();' in qml

# Click-away logic must exclude the trigger and the popup, otherwise the
# same click that opens confirmation can immediately dismiss the panel.
outside = qml.split('// Clicking anywhere outside the yellow', 1)[1].split('Rectangle {\n            id: syncPopover', 1)[0]
assert 'const overMenu' in outside
assert 'const overTrigger' in outside
assert 'if (!overMenu && !overTrigger)' in outside
assert 'timew.closeSyncPopover();' in outside
assert qml.count('if (timew.syncPopoverOpen)\n') >= 2

# We only reuse existing service methods. Privileged correction must still
# have an independent confirmation and Polkit/host-control guard.
for decl in ('function prepareResync()', 'function requestResync()',
             'function cancelResync()', 'function diagnoseResync()',
             'function checkTimeAccuracy()'):
    assert decl in service, decl
assert 'authSessionActive = true;' in service
assert 'Quickshell.shellPath("services/time/TimeHostControl.py"), "resync"' in service
assert 'label: "CONFIRM RESYNC"' in settings
assert 'label: "DIAGNOSE"' in settings
assert 'label: "CHECK TIME"' in settings
assert 'TimeSettings.requestResync()' in settings
assert not re.search(r'^\s*property bool syncPopoverOpen:', popup, re.M)

print("TIME // dynamic mode title + inline guarded resync controls PASS")
