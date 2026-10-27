# 🏥💜 TASKS M11q // Native callback fault acceptance preparation and guarded production preflight

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS JSON storage continuity, Proxy 1 → Proxy 2 succession  
**Worker:** OPEN AI // CHATGPT, Hospital-compatible external doctor, **not** a live registered Hospital worker  
**Base:** `main` at `564dd1987cee54bb6cb8701e3cf674e882a4aa3d` after merged M11p PR #858  
**Classification:** Source-only **disposable native test harness hardening** and **disabled production-integration preflight**, not an active or installable production writer

## IMPLEMENTATION

The M11p disposable Python host now durably records every stage ID. Its subprocess tests cover committed reservation, changed JSON source before settlement, and host termination. Those tests do **not** prove the native Quickshell `FileView.onSaved/onLoaded` event order or detect every late callback after QML shutdown.

M11q improves the **standalone**, unmounted M11m Quickshell test harness. It does not modify `services/hub/ApolloHubTodoStore.qml` or any production task file path.

1. **Reuse evidence, do not create a second recorder.** `TaskJsonGateHostBridgeM11m.qml` now imports the existing pure `TaskFileViewNativeEvidenceM11i.js` chronology/summary and maps its event names. It stores bounded, in-memory event tags and phases **without** source JSON, private file paths, stage IDs or process stdout.
2. **Session-bound delayed callback.** The QML bridge increments `sessionGeneration` on attach, rejection, STOP and host exit. Deferred `Qt.callLater` readback must match the original generation, host-running flag, owner epoch, pending stage, exact test file path and `VERIFYING` state. The actual pure helper is `TaskJsonNativeCallbackGuardM11q.js`, covered by Node tests.
3. **No premature publication.** The `verify` host response must match the active stage, prior owner epoch and `SETTLING` state before advancing the displayed confirmed counter. A valid freeze response must advance the owner's epoch by exactly one. A missed response leaves the display at the last confirmed value.
4. **Four explicitly armed native faults.** An added **ARM FAULT** control cycles `NONE → AFTER_RESERVE → AFTER_SAVED → AFTER_READBACK → AFTER_SETTLEMENT → NONE` in the synthetic test harness. The next INCREMENT interrupts **only the test** at that checkpoint, fences the QML state and terminates the disposable host, leaving any reservation/tombstone journal unchanged for fresh-owner review. Nothing arms automatically.
5. **Visible, redacted acceptance indicators.** The standalone panel shows native save-chain count, freeze/recovery event summary and bounded recent event tags. Its count is strictly an **observation trace**, not a proof of live-writer authority.
6. **Production preflight only.** `tests/tasks/fixtures/task_production_preflight_m11q.json` inventories the exact real-source seams needed for later authorization: `stage(result)`, five FileView callbacks, `reloadFromDisk()`, the fixed guarded flag, existing six-state `TodoPolicy.view()`, and a **separate production-only** OS host with real-source identity/backup/epoch checks. None are implemented here.

### Four native fault expectations

| Explicit standalone test fault | Test file write | Durable stage history | After fresh-owner reopen |
| --- | --- | --- | --- |
| `AFTER_RESERVE` | Not requested | `RESERVED` | `RECOVERY_REVIEW`, pending |
| `AFTER_SAVED` | Save callback already occurred | `RESERVED` | `RECOVERY_REVIEW`, pending |
| `AFTER_READBACK` | Exact FileView readback observed, but verify not sent | `RESERVED` | `RECOVERY_REVIEW`, pending |
| `AFTER_SETTLEMENT` | Independently verified and settled | `SETTLED` | `RECOVERY_REVIEW`, no pending |

These are **expected outcomes for a future native test**, not observed results. QML event completion, process timing, source readback and persisted journal remain to be checked by the operator. The `AFTER_SETTLEMENT` injected stop occurs **before the QML test counter is published**, deliberately modeling a lost UI acknowledgment after an already durable commit.

## HOW TO USE

**No local action is necessary for this PR.** Source-only and model tests are run on GitHub.

A future operator-approved native acceptance should use a **new, private synthetic folder per fault case**, following the one-time M11m fixture seeder and standalone `TaskJsonGateHarnessM11m.qml` procedure. Never rebootstrap or erase the M11n journal. For each new fixture: NEW TEST → select desired fault with **ARM FAULT** → INCREMENT once → observe the safe error and record event tags → exit → use **read-only** SQLite inspection for phase/epoch/pending/history and independent source hash → EXISTING should enter `RECOVERY_REVIEW`. The trigger is not active without explicit interaction; do not run these tests against actual TASKS JSON.

Because every fault interrupts the synthetic authority, **do not** try all four cases on one reused test folder. Starting from an ambiguous journal is not an allowed test reset. A new isolated directory is required for each fresh case.

## VERIFY

The M11q Node test calls the **exact pure JS helper imported by the QML bridge**. It exercises a valid readback and settlement, then rejects mismatched generation, stage ID, owner epoch, target path, missing pending bytes, wrong state, host death, malformed settlement, stale receipt, and unsupported order. It also checks M11i event-chain rejection after save failure or host exit, and static ensures M11q code has no production mount.

CI also reruns M11m transport, M11p durable OS host/crash tests, M11o JS/Python parity, M11k production gate preflight, and M11d single-writer inventory. These are **unit, source, and disposable subprocess tests**. None can replace actual Quickshell/Sway/Wayland callback evidence.

## WATCH OUT FOR

- A real `FileView.saved()` signal carries **no durable stage ID**, so a QML generation counter can fence delayed closures, but cannot cryptographically authenticate host stdout or prove the origin of arbitrary late native callbacks. Any unexpected signal remains a recovery blocker.
- Production-grade host/QML communication needs an independent OS-owner identity and fresh protocol session nonce with explicit restart/epoch correlation, plus tested host-scope and source-file identity. The M11m test bridge is not sufficient.
- `ApolloHubTodoStore.qml` exposes synchronous nine-method return values and six public storage states. An asynchronous guarded reservation needs a separately reviewed UI contract; it must never return a misleading successful write or publish the speculative document on `FileView.onSaved`.
- The existing `guardedWriterEnabled: false` is hardcoded on purpose. There is **no** approved toggle, production OS host, data backup/cutover or guarded activation.
- The v2 SQLite file is a synthetic **admission journal** and never a production task-data SQLite store. No SQLite task migration, remote GitHub Project write or direct use of the old M11n fixture occurs.
- The operator's local Quickshell worktree is not necessarily synchronized with GitHub; do not pull, reset, stash, edit, restart or delete anything locally without a separately approved exact scope.

## CHECKLIST

- [x] Independently reverify merged M11p, current main, shared singleton and no competing TASKS PR
- [x] Preserve M11i redacted evidence instead of duplicating it
- [x] Session/epoch/stage/path fence for deferred FileView readback and host settlement
- [x] Four opt-in disposable QML fault injection points and visible evidence
- [x] Inventory exact proposed production integration seams; no implementation/activation
- [x] Add deterministic JS tests and CI for callback policy and source boundaries
- [ ] Verify CI on final draft PR head
- [ ] Operator-observe fault traces on **four new** private test folders, with read-only journal comparison
- [ ] Independently review production host authenticity, initial source backup, restore and freeze/drain semantics
- [ ] Separate operator approval to patch the production singleton and native real-source host
- [ ] Separate approval for merging a production patch, local deployment, guarded activation and eventual SQLite migration

## NEXT

M11r should first assess native fault observations and the missing **session nonce / native callback provenance** boundary. Only then propose the exact, separately authorized production-only OS host and guarded asynchronous `stage()` wiring. Stay locked off until full native backup, rollback, restart/freeze, and UI snapshot compatibility acceptance.

## DECISIONS

The production JSON FileView remains the sole active writer, `guardedWriterEnabled` remains `false`, and no live TASKS data, user's computer, local checkout, GitHub Project data or live Hospital service has been changed by M11q. The future guarded mode and SQLite cutover are distinct decisions reserved to the operator.
