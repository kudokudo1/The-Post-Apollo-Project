#!/usr/bin/env python3
"""One Hospital-owned integration: source Room TRASH + Trash++ index + RESTORE.

Source-level contract. Real disposable SQLite behavior lives in PX PR #130.
No host writes or live UI activation are performed by this test.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
worker=(ROOT/"widgets/HospitalRegisteredWorkerView.qml").read_text()
trash=(ROOT/"modules/Trash.qml").read_text()
action=(ROOT/"services/hospital/HospitalRoomLifecycleService.qml").read_text()
bin_service=(ROOT/"services/hospital/HospitalRoomBinService.qml").read_text()
deck=(ROOT/"components/TrashLifecycleActionDeck.qml").read_text()

def check(text,source,label):
    assert text in source, label+": "+text

# Registered Room controls, exact Room state and deliberate confirm.
for marker in (
    'HospitalRoomLifecycleService {', 'roomId: root.pinnedRoomId',
    'function armLifecycleAction(action)', 'function confirmLifecycleAction()',
    'onTrashReviewRequested:', 'onRestoreReviewRequested:',
    'enabledAction: root.lifecycleArmed',
    'roomLifecycle.permissionReady', 'burnCapable: false',
    'onCommitted: function(receipt)',
    'root.refreshRequested();'
):
    check(marker,worker,"Room review")
# No click can invent source identity, and no persistent command is sent
# just from showing a review panel or opening a Room.
for marker in (
    'active && nativeClientInstalled',
    'executeProcess.exec([nativeClientPath, action, room]);',
    'nativeReadPath, "review", id',
    'pendingRevision = -1;',
    'pendingDigest = "";',
    'payload.roomId !== root.pendingRoomId',
    '!Number.isSafeInteger(payload.revision)',
    'payload.status !== "COMMITTED"',
    'payload.action !== root.pendingAction',
    'payload.originalPreserved !== true',
    'payload.burnAllowed !== false',
    'root.committed(payload)', 'root.refused(problem)'
):
    check(marker,action,"PX exact owner transport")
# The source-owned bin is a separate read-only Process, not GIO index.
for marker in ('hospital-room-read', 'Array.isArray(parsed)',
               'item.burnAllowed === false',
               'item.state === "TRASHED"', 'root.loaded = true',
               'root.loaded = false'):
    check(marker,bin_service,"Room bin")
for marker in (
    'HospitalRoomBinService {', 'HospitalRoomLifecycleService {',
    'entryType:"hospital"', 'trashViewFilter !== "hospital"',
    'if (trashViewFilter === "files"',
    'id:"hospital", label:"HOSP"',
    'reviewHospitalRestore(row)',
    'hospitalRestore.permissionReady',
    'trashEntry.modelData.entryType === "hospital"',
    'visible: trashEntry.modelData.entryType !== "hospital"',
    'hospitalBin.lastError'
):
    check(marker,trash,"Trash++ integrated source views")
# GIO and managed-copy Restore remain independent and unchanged.
for marker in ('restoreResearchCopy(', 'reviewGioFileRestore(',
               'reviewManagedCopyAction(', 'armBurn(', 'armResearchBurn('):
    check(marker,trash,"preserve older owners")
for marker in ('ownerApproved: false',
               'policyReviewed: false',
               'retentionHold: true'):
    check(marker,worker,"deny-by-default source trust")
check('property bool protectedResource: true',deck,"shared primitive")
assert "onBurnReviewRequested:" not in worker
assert "room-lifecycle-burn" not in trash
assert "gio trash" not in action.lower()
assert "gio trash" not in bin_service.lower()
assert 'room-lifecycle-trash' not in action
assert 'room-lifecycle-restore' not in action
print("HOSPITAL TRASH++ BATCH // PASS // native approval request, source bin, no Burn")
