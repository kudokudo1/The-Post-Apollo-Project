#!/usr/bin/env python3
"""Hospital Room lifecycle integration contract: source-owned, trust held."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
view = (ROOT / "widgets/HospitalRegisteredWorkerView.qml").read_text()
policy = (ROOT / "services/hospital/HospitalRoomTrashReviewPolicy.js").read_text()
action = (ROOT / "services/hospital/HospitalRoomLifecycleService.qml").read_text()
bin_service = (ROOT / "services/hospital/HospitalRoomBinService.qml").read_text()
trash = (ROOT / "modules/Trash.qml").read_text()
deck = (ROOT / "components/TrashLifecycleActionDeck.qml").read_text()

def requires(needle, data, label):
    assert needle in data, label

requires('import "../services/hospital/HospitalRoomTrashReviewPolicy.js" as TrashReviewPolicy',
         view, "historical source-owner policy stays distinct")
requires('root.viewMode = "lifecycle"', view, "explicit Room route")
requires('text: "TRASH++ // HOSPITAL ROOM LIFECYCLE"', view,
         "existing lifecycle review screen preserved")
requires('HospitalRoomLifecycleService {', view, "PX owner transport present")
requires('TrashLifecycleActionDeck {', view, "canonical Trash++ controls reused")
for guard in (
    'ownerId: "hospital"', 'resourceId: root.pinnedRoomId',
    'resourceRevision: String(roomLifecycle.review.digest || "")',
    'showBurn: true', 'burnCapable: false',
    'ownerApproved: false',
    'policyReviewed: false',
    'protectedResource: true',
    'retentionHold: true',
    'REQUEST NATIVE APPROVAL // TRASH ROOM',
    'REQUEST NATIVE APPROVAL // RESTORE ROOM',
    'onTrashReviewRequested:', 'onRestoreReviewRequested:',
    'enabledAction: root.lifecycleArmed',
):
    requires(guard, view, "review-only until authenticated source grant: " + guard)
for guard in (
    'active && nativeClientInstalled',
    'if (!active || !nativeClientInstalled || operating',
    'executeProcess.exec([nativeClientPath, action, room]);',
    'payload.status !== "COMMITTED"',
    'nativeReadPath, "review", id',
    'payload.originalPreserved !== true',
    'payload.burnAllowed !== false',
):
    requires(guard, action, "transport never invents trusted authority: " + guard)
for guard in ('hospital-room-read', 'item.burnAllowed === false',
              'root.loaded = false', 'root.lastError',
              'HOSPITAL BACKEND NOT READY'):
    requires(guard, bin_service, "bin metadata authority and stale errors")
for guard in (
    'entryType:"hospital"', 'visible: trashEntry.modelData.entryType !== "hospital"',
    'hospitalRestore.permissionReady', 'hospitalBin.loaded',
    'room-lifecycle' if False else 'id: hospitalRestore',
):
    requires(guard, trash, "Hospital resources isolated from file/copy Burn")
for phrase in (
    'trashAllowed: false', 'restoreAllowed: false',
    'burnAllowed: false', 'enqueueAllowed: false',
    'sourceMutationAllowed: false'
):
    requires(phrase, policy, "old metadata-only review keeps deny-only contract")
assert "onBurnReviewRequested:" not in view
assert "gio trash" not in view.lower()
assert '"BURN_ALL"' not in action
assert "gio trash" not in bin_service.lower()
requires("signal trashReviewRequested", deck, "canonical shared deck")
for marker in ("id: transcriptScroll","id: continuityView","id: attachScroll"):
    requires(marker, view, "existing Room actions must remain intact")
assert 'room-lifecycle-trash' not in action
assert 'room-lifecycle-restore' not in action
print("HOSPITAL ROOM TRASH++ CONTRACT // PASS // native-only mutation, guarded bin, Burn omitted")
