# 🏥💜 TASKS M12e // Isolated Native Callback Attribution and Ambiguity Lab

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** TASKS JSON writer continuity  
**ASSIGNMENT:** M12e isolated callback-stage attribution experiment, no production integration  
**WORKER:** External Hospital-compatible ChatGPT doctor, no verified live registration  
**PROVIDER:** OPEN AI // CHATGPT  
**INSPECTED BASE:** GitHub `main` `5e255fc6358803044fd8f19bec9c3bee83846461`, October 31, 2026; recheck before further work  
**CLASSIFICATION:** **SYNTHETIC SOURCE TESTS + OPT-IN, UNMOUNTED NATIVE OBSERVATION SURFACE**. No live TASKS or production authority.

## IMPLEMENTATION

### Actual starting point

- M12d was merged on `main` and tested an Ed25519-signed **synthetic** release, kernel-observed sealed Linux child, disposable `m11l-tasks-copy` journal owner, and process-restart recovery review. This was **not** live TASKS integration.
- `services/hub/ApolloHubTodoStore.qml` still owns the sole live JSON `FileView`, with `guardedWriterEnabled: false`. Existing `onSaved` publishes the candidate in legacy mode, not after OS-host durable settlement.
- Native FileView work already exists. `services/projects/TaskFileViewHostBridgeM11g.qml` owns an **isolated** FileView and synthetic OS host for `m11e-fileview-test/fixture-only.json`; `TaskJsonGateHostBridgeM11m.qml` has later synthetic stage/epoch callback tickets; `TaskJsonNativeCallbackGuardM11q.js` checks those deferred readback tickets; `TaskFileViewNativeEvidenceM11i.js` records privacy-sanitized event tags. M11j's native acceptance record was based on *operator-provided* observations, not a rerun here.
- Reusing those components is safer than constructing another native writer or widening M11l/M11m's disposable paths. **M12e does not modify any of them.**

### The attribution gap

A native `FileView.onSaved` notification says the FileView reported a save, **but carries no independently authenticated stage ID, source epoch, host session, source digest or journal commitment**.

Two possible physical histories may produce the identical observable event transcript:

| World | Physical origin (not in event) | Native event transcript |
| --- | --- | --- |
| A | Current stage A | `FILE_SAVED → FILE_READBACK_OK` |
| B | Earlier stage B or differently attributed save | `FILE_SAVED → FILE_READBACK_OK` |

The callback transcript alone cannot distinguish A from B. A locally remembered `stageId` attached by QML after the fact is a *correlation claim*, not stage provenance. Deferred reload reduces the known Quickshell timing hazard, but only an exact independently observed source readback plus a durable, authenticated and session-bound host settlement can justify publishing a particular pending stage. An external editor or adversarial same-user process still needs detection/fencing. This is an architectural **negative finding**, not proof of a particular native race reproduced on today's machine.

### Added files and boundaries

1. **`tests/tasks/fixtures/TaskCallbackAttributionM12e.cjs`**: pure Node.js synthetic observer model. A specific pending stage is queued then reserved with stage/session/epoch/generation/hash. Native callbacks alone never publish. A *deferred* readback requires the correct ticket and exact candidate raw bytes, followed by a separately matching *synthetic* durable-settlement receipt to promote confirmed data. Duplicate or early callbacks, bad tickets, mismatched raw, native failures, host loss and mismatched settlement enter `RECOVERY_REVIEW`; retain last confirmed rows and deny new writes. Mock `journalSettled:true` is NOT genuine journal evidence.
2. **`tests/tasks/test_task_native_callback_attribution_m12e.cjs`**: negative tests including two indistinguishable native event worlds, callback-only nonpromotion, exact positive simulated settlement, wrong raw bytes, stale stage/session/epoch/generation, duplicate early/late callbacks, host loss, freeze and no-production mount/source invariants.
3. **`tests/tasks/fixtures/TaskNativeCallbackLabM12e.qml`**: an **unmounted standalone visual observation surface**, reusing the existing `TaskFileViewHostBridgeM11g`. It creates **no additional FileView or Process**. It displays sanitized existing `nativeSummary` and `nativeRecent` with explicit `NATIVE STAGE ATTRIBUTION: NOT PROVEN`. Buttons require a human to supply the existing private `m11e-fileview-test/fixture-only.json` path and a test writer ID, then explicitly start the disposable M11g host. No auto attach, no production path, no QML startup import in `shell.qml`.
4. A scoped read-only CI workflow reruns the M12e model, prior M11q callback/source audit, M11 deferred readback static checks, M12d signed owner, M12a completion, M11t/M11d single-writer safeguards.

**Important:** a test-only forged `settlement` object can satisfy the pure model if the caller controls it. It is merely exercising the *policy logic*, **not authenticating a real OS process, native callback, or durable SQLite transaction**.

## HOW TO USE

No change or action is needed on the operator's Fedora installation. GitHub CI runs:

```sh
node --test tests/tasks/test_task_native_callback_attribution_m12e.cjs
```

The QML observer is **not automatically started by CI or the live shell**. A native Quickshell acceptance would require a separately approved, manually prepared private synthetic fixture and explicit invocation of the standalone lab. The existing M11e/M11g manual fixture pathway can be reused; do not assume the operator's local checkout is clean or start a second shell without approval. If run later, record the Quickshell build/version and sanitized `nativeRecent` event sequence, check exact fixture source and the disposable host journal *after the test*, compare against expected events, and retain a clear **native-observed vs source-only** evidence boundary.

No command in this PR inspects or writes real TASKS, restarts Quickshell, installs a host, or sets up signing credentials.

## VERIFY

- **GitHub source preflight:** M12d merged; no competing open TASKS PR or M12e branch; existing M11g/M11m/M11q native test bridges and old synthetic acceptance records inspected. M11g already implements `Qt.callLater` after `onSaved` before `fixtureFile.reload()`; never claim it grants callback provenance.
- **CI:** pure model test, static QML observer/source checks and inherited tests. A passing run is a **synthetic/source PASS**, not an executed native FileView run.
- **Production unchanged:** `ApolloHubTodoStore.qml` has one live `FileView`, nine `stage(TodoPolicy.*)` mutations, literal `guardedWriterEnabled: false`; no M12e component mounted.
- M11t's **nine production gates** and M12b's **ten independent evidence topics** remain OPEN, including native callback attribution and production signing-key authority.

## WATCH OUT FOR

- M12e does not give callback tags new cryptographic fields. The **negative attribution ambiguity is structural**. To claim exact attribution, a separately audited host would need to bind its journal stage to exact OS source-byte readback, stage/session/epoch/generation, external-writer detection and durable settlement.
- Existing M11g's host and FileView are **not** the M12d signed synthetic process. This milestone does not combine either into one production executable, nor is M12d's test trust root approved.
- Native observation cannot be claimed from GitHub CI alone; optional manual native acceptance is **not executed by this milestone**. No screenshots or source identities are fabricated.
- Native callbacks can be duplicate, late or emitted during freeze/restart. Old confirmed rows and operator drafts must survive uncertainty; no automatic stage replay or empty writable recovery.
- The test QML takes an operator-supplied filename and writer ID only for the **pre-existing disposable M11g bridge**. Do not enter the live TASKS JSON path, install a host or mount this component in `shell.qml`.

## CHECKLIST

- [x] Recheck current GitHub `main`, M12d merge, TASKS PR collisions and Syntagma/Hospital source
- [x] Audit existing native FileView callback/host/evidence mechanisms before designing a new test
- [x] Prove two-world callback transcript ambiguity in a deterministic test
- [x] Require deferred matching raw readback plus separately matching synthetic settlement before publication
- [x] Test stale/duplicate/failure/freeze and last-confirmed preservation
- [x] Add unmounted observer reusing M11g, plus source-only CI and seven-part handoff
- [ ] CI verification and independent review
- [ ] Operator review and merge
- [ ] Separate operator-authorized native observation on disposable fixture, with result provenance
- [ ] Production trust, source, UI API, callback and activation decisions

## NEXT

Review CI and draft. The next useful work is **operator-approved isolated native acceptance** of the M12e observation surface, with a preserved build/version, event transcript and disposable journal audit. Then design an **independent source-byte stage attribution mechanism** that does not trust `onSaved` as an identity oracle. A production QML adapter, trust-root enrollment and real task-source access require separate scope and authority.

## DECISIONS

**Implemented:** isolated synthetic callback ambiguity tests and a manual-only, unmounted observation surface built on the existing M11g test harness.

**Verified in source only:** the live TASKS singleton remains untouched; old M11g deferred readback and host settlement path exists.

**Not yet accepted:** any claim that current `FileView` callbacks identify a durable stage, external executable trust root, native acceptance of this new observer, task-source permissions, asynchronous production API or rollback policy.

**Not authorized:** production writer changes, real TASKS data reads/writes, Fedora local changes, Quickshell restart, release signing keys, SQLite task-data migration, PR merge, automatic recovery, or live Hospital registration.
