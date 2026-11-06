# 🏥💜 TASKS // M14a Live Native Save Observation

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Source Integrity / Encrypted Draft Recovery  
**STAFF ROLE //** DOC, external Hospital-compatible OPEN AI // CHATGPT; no live Hospital registration verified  
**ASSIGNMENT //** Connect real, read-only Quickshell save lifecycle **observation** to the already-merged M13z operator review, without treating it as authenticated source evidence  
**BASE //** `main` `eeaad9ea2788eb48eb0b898ea0c17f7a1b054cbb` on November 6, 2026  
**SCOPE / PERMISSIONS //** GitHub repository QML/JS/tests/CI/docs only, no local Fedora changes, live Quickshell restart, real TASKS data read, external storage service, keyring/Connections host edit, writer migration, recovery activation or automatic merge.

## IMPLEMENTATION

M13z PR #1388 is merged with three operator-facing examples and a hardcoded **LIVE // SOURCE REVIEW NOT CONNECTED** guard. M13y is a **synthetic-only** SQLite/JSON source inspector. Neither can establish the state of a real interrupted save, because the live TASKS application currently has no independently authenticated journal/source-readback service.

A smaller useful next step is possible without inventing a trust root: **observe the existing Quickshell FileView lifecycle and describe exactly what was observed.**

### 1. Metadata only, in the current sole writer

In `services/hub/ApolloHubTodoStore.qml` M14a adds three narrowly scoped in-memory fields:

- `nativeSaveEventM14a`, initial `NOT_OBSERVED` and updated only at the existing `stage()`, `FileView.onSaved`, and `FileView.onSaveFailed` boundaries.
- `nativeSaveRequestsM14a`, a bounded session-local count of accepted `stage()` write requests. It is **not** a durable revision number, task identity or monotonic cross-process ledger.
- `nativeSaveObservationM14a`, a read-only projection of the two fields plus the already-existing `storageState`. It has no text, task ID, credentials, source pathname, expected hash, saved bytes or receipt payload.

When the existing `stage()` accepts a mutation, M14a records `WRITE_REQUESTED` before the same single `todoFile.setText()`. The original native `onSaved` handler records `FILEVIEW_SAVED_HINT` if `storageState` is `saving`, otherwise `UNATTRIBUTED_SAVED_HINT`. `onSaveFailed` records `FILEVIEW_SAVE_FAILED`. **The original save behavior, callback branches, source writer, ticket gates, reload handling, returned booleans and error handling are unchanged.**

This event tracking is *not* a source stage-to-callback binding. A callback while saving does not prove it belongs to the latest accepted mutation. An external same-UID process can modify the source, and the JSON may not be durable even though the callback was observed.

### 2. Honest live callback section in existing UI

`widgets/tasks/TaskLiveNativeSavePolicyM14a.js` maps a strict object containing only `phase`, `requestCount` and `sourceState` into finite UI strings. Invalid or extra input becomes `NATIVE SAVE // OBSERVATION UNVERIFIED`. Even a valid native callback cannot enable a grant, report an independently verified source, acknowledge a durable save, replay, capture, restore, clear a draft, or release a key.

`TaskRecoveryReviewPaneM13z.qml` gets a new **LIVE // NATIVE SAVE SIGNAL** section above the existing **POST-CRASH SCENARIOS // EXAMPLES ONLY** rail. `TaskRecoveryStatusPaneM13q.qml`, already under **TASKS → SYNC → RECOVERY**, supplies `nativeSaveSignals: ApolloHubTodoStore.nativeSaveObservationM14a`. The original M13s editor-dirty section, C2 keyring presence probe, and all M13z examples remain in the same screen.

The M13z live *source verification* status remains **LIVE // SOURCE REVIEW NOT CONNECTED**, and the M14a callback section always displays **CALLBACK PROVENANCE AND SAVED BYTES // NOT VERIFIED**. This separation is crucial: actual FileView callbacks are now observed, **but not independently trusted or interpreted as a source receipt**.

### 3. Boundaries

There is no new `FileView`, no new writer, process, socket, SQLite connection, Python fixture import, file read, keyring lookup, secret client, timer, automatic retry or draft capture. The single writer continues legacy behavior and has `guardedWriterEnabled:false`, `ticketProducerEnabled:false`, `encryptedRecoveryEnabled:false`; shared Connections continues `credentialActionsEnabled:false`.

## HOW TO USE

After a separate approved merge and desktop deployment, open **TASKS → SYNC → RECOVERY**.

The new **LIVE // NATIVE SAVE SIGNAL** box shows one of the following bounded statuses from *this running Quickshell session*:

| Status | Meaning | NOT proved |
|---|---|---|
| NO CALLBACK OBSERVED THIS SESSION | No FileView save callback recorded since process startup | Older saves / correct disk state |
| WRITE REQUESTED | Current singleton passed its existing write admission | Actual file updated |
| CALLBACK OBSERVED / UNVERIFIED | The existing `FileView.onSaved` ran while storage was saving | Correct stage attribution, saved bytes, OS durability |
| UNATTRIBUTED CALLBACK | A callback arrived outside recognized saving state | Ownership of any pending save |
| FAILURE CALLBACK OBSERVED | `onSaveFailed` ran | A safe restore or replay path |

Below the live box, the **UNCHANGED / UNSETTLED / SETTLED** tabs remain **examples only**, not an interpretation of the current file. Live editor draft presence remains above the review panel. All outputs say the draft must be kept.

No user action beyond viewing the status is required. Opening the status page does not initiate a save, keyring query, filesystem scan or auto-refresh.

## VERIFY

- `tests/tasks/test_task_live_native_save_observation_m14a.cjs`: all five valid finite native event phases, all six source states, zero-request unattributed callback, malformed/forged metadata denial, no raw task/source/credential fields, exact QML signal binding, one existing FileView / one setText, false recovery gates.
- Existing M13z scenario semantics, M13q keyring UI, M13s live dirty editor metadata, M13w keep-draft policy, M12o ticket gates, M11d source writer inventory and C2a shared Connections fail-closed suites run in CI.
- `qmlformat` validates syntax of the changed singleton and both recovery panes. This is **syntax testing only**, not a real Quickshell runtime or actual save experiment.
- Exact final GitHub CI must be verified before independent Nurse 2 review and operator merge/acceptance.

## WATCH OUT FOR

**No independently authenticated native source evidence has been implemented.** M14a is a real in-process callback observation, not an integrity check or source readback. It cannot recognize the M13y post-crash classes after a restart; the in-memory counters and last callback status deliberately reset on process restart. Do not read `FILEVIEW_SAVED_HINT` as “this edit is safely committed to disk.”

The existing legacy writer currently publishes pending documents on `onSaved` without independent readback; M14a deliberately does not revise that production semantics or attempt a risky silent storage migration. A separate future milestone must evaluate and authorize a correctly fenced/serialized readback, choose a realistic threat model under M12l, and test real native Quickshell lifecycle plus crash boundaries. Only then could the app consider more authoritative user-save ACK semantics.

A malicious same-UID process and uncooperative source write remain outside the accepted M12l security guarantee. Actual encrypted draft recovery requires separate explicit opt-in consent, independent Connections principal/key authorization and native source/restart acceptance.

## CHECKLIST

- [x] Read canonical Syntagma/Hospital working rules and verify main/M13z merge/current competing work
- [x] Inspect the real singleton FileView callbacks, existing UI source state, M13z review and accepted M12l architecture
- [x] Add bounded real callback metadata only within the existing writer
- [x] Add live status projection into the existing RECOVERY screen while preserving illustrative scenarios
- [x] Test no source read/write duplication, no grant, no saved-draft-clear and unchanged shared Connections
- [x] Add targeted CI and this Hospital handoff
- [ ] Exact-head CI, independent review and operator merge decision
- [ ] Actual Fedora/Quickshell read-only visual and callback test after a separate authorized deployment
- [ ] Independently authenticated source readback/receipt and journal comparison
- [ ] Real opt-in encrypted recovery, consent, unlock and native crash acceptance

## NEXT // M14b

Design a separately authorized, **read-only independent native source-evidence path** with a clear, explicitly selected trust model. Reuse the one logical TASKS coordinator and preserve the live source writer unless an operator explicitly chooses a different architecture. Tests must reproduce a normal save, interrupted save, stale callback, source mismatch, same-UID interference and restart, while never auto-replaying or deleting a draft. Do **not** enable the existing disabled ticket or recovery paths merely because M14a callbacks show up.

## DECISIONS

Continue with M12l accepted local-first single logical owner and read-only default. GitHub changes only; no workstation access, no production activation, no separate privileged broker, no shared Connections owner mutation, no PR auto-merge, no claim of live Hospital registration, and no operator final acceptance implied by passing CI.
