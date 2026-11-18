#!/usr/bin/env python3
"""Hospital source-owned Trash++ integration: UI controls are review-only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
view = (ROOT / "widgets/HospitalRegisteredWorkerView.qml").read_text()
policy = (ROOT / "services/hospital/HospitalRoomTrashReviewPolicy.js").read_text()
deck = (ROOT / "components/TrashLifecycleActionDeck.qml").read_text()

def requires(needle, data, label):
    assert needle in data, label

requires('import "../services/hospital/HospitalRoomTrashReviewPolicy.js" as TrashReviewPolicy',
         view, "source-owner policy must be imported")
requires('root.viewMode = "lifecycle"', view, "explicit Room lifecycle route")
requires('text: "TRASH++ // HOSPITAL ROOM LIFECYCLE"', view, "named review surface")
requires('TrashLifecycleActionDeck {', view, "reuse Trash++ review primitive")
for guard in (
    'ownerId: "hospital"', 'resourceId: root.pinnedRoomId',
    'resourceRevision: ""', 'showTrash: true', 'showRestore: true',
    'showBurn: true', 'trashCapable: false',
    'restoreCapable: false', 'burnCapable: false',
    'ownerApproved: false', 'policyReviewed: false',
    'protectedResource: true', 'retentionHold: true'
):
    requires(guard, view, "source-owned Room actions must fail closed: " + guard)
for phrase in ("trashAllowed: false", "restoreAllowed: false",
               "burnAllowed: false", "enqueueAllowed: false",
               "sourceMutationAllowed: false"):
    requires(phrase, policy, "deny-only policy: " + phrase)
assert "gio trash" not in view.lower(), "never trash the shared PX database"
assert "onTrashReviewRequested:" not in view
assert "onBurnReviewRequested:" not in view
assert "onRestoreReviewRequested:" not in view
requires("signal trashReviewRequested", deck, "use canonical shared Trash++ deck")
requires('id: transcriptScroll', view, "preserve existing Room chat")
requires('id: continuityView', view, "preserve existing continuity")
requires('id: attachScroll', view, "preserve attached Session route")
print("HOSPITAL ROOM TRASH++ UI // PASS // source-owned review-only controls")
