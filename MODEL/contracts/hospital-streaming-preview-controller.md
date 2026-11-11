# Hospital Surgery // streaming preview controller checkpoint

PATIENT // `The-Post-Apollo-Project`
ROOM // Hospital Surgery / Live Dictation Usability
STAFF // External Hospital-compatible DOC, not verified as a live worker
ASSIGNMENT // Reusable UI state controller for an eventual streaming recognizer
PERMISSIONS // GitHub-only bounded source/tests; no local workstation changes
PRODUCTION // HOLD

## IMPLEMENTATION

- `services/hospital/HospitalStreamingPreviewPolicy.js` is a pure QML-compatible reducer with five allowed Surgery inputs: START HERE brief (`intake`) and Job goal, constraints, definition of done, checklist. It validates field, mode, session token, exact event shape, strictly consecutive revisions, text controls, and per-field length. The maximum is 300 updates per session.
- A `hypothesis` updates **only** an in-memory provisional string. It cannot alter `field.value`, save, submit, or activate a worker.
- A `commit` is the **only** event allowed to modify editor text and must pass the existing `HospitalDictationTextPolicy.appendTranscription` function. Commit clears provisional words. Empty commit clears the preview without inventing text. Duplicate or missing revisions fail closed.
- Surgery `HospitalWorkforceManagerView.qml` stages `beginStreamingPreview`, `acceptStreamingPreview`, `finishStreamingPreview`, and `cancelStreamingPreview` using a single in-memory session. Only the selected field can change; the draft must match the controller's exact last confirmed version.
- Provisional words display in a **separate cyan HEARING line**, never in the editor. The editor is read-only during preview; a shared CANCEL control restores the original draft if it has not since been changed externally. Mode switch and manager close also cancel. STOP/cancel from the existing Whisper engine remains unchanged.
- **No actual streaming adapter calls these functions.** Normal Surgery and Whisper show no preview line, launch no Vosk model, and have no additional microphone or process.

## HOW TO USE

There is no new live control. The preview is staged and inert until a **separately authorized, bounded streaming adapter** is connected, with explicit opt-in and host testing. The synthetic event sequence can be verified through the new acceptance test:

`python3 tests/hospital/test_streaming_preview_controller_contracts.py`

This runs Node to test JavaScript transitions. It never records audio, opens a device, downloads models, or modifies user work.

## VERIFY

- Unit test feeds provisional `why do` then `why did` with two revisions and confirms that the editor contains neither until a final commit.
- Tests also cover stale owner tokens, out-of-order revisions, final-only append, empty final clearing preview, length boundaries, all five field/mode pairs, and CANCELLATION preserving the original.
- Source contract verifies independent visual preview, in-place single draft, controller lifecycle, and no streaming source binding to live host.
- Native Quickshell/Qt rendering not yet verified. No real model timings or accuracy results.

## WATCH OUT FOR

- Preview reducers and request tokens are presentation integrity gates, **not operating-system authentication**. A later process adapter must have its own protected transport and cancellation/teardown policy.
- A `commit` is still **editable draft text**. It is not a Room/Worker/Job record save and cannot trigger a provider.
- If another writer changes the field during preview, its content is preserved; stale streamed packets are refused. Hypotheses are transient and must not be journaled.
- PR #1904 was marked merged into **the PR #1899 feature branch**, not verified on `main`; this UI controller is independent of its Responsive-mode control.
- Existing #1899 stop feedback and #1913 offline Vosk proof are merged upstream. This new preview requires no model installation.

## NEXT

1. Confirm exact-head CI and independent review.
2. Keep the preview inert until operator approves the installation of an isolated streaming model and trusted handoff into the existing Hospital microphone owner.
3. Benchmark true first hypothesis, final text, CPU/memory and accuracy against Standard Whisper.
4. Preserve a one-click return to Standard, complete STOP/CANCEL teardown and final operator acceptance.

DECISIONS // No local host modifications, merges, production activation,
provider workers or streaming model deployment. Rollback is revert of this
standalone reducer + UI staging, without affecting Whisper dictation.
