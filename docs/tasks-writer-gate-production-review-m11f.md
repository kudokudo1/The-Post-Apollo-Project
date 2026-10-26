# 🏥💜 TASKS // M11f Production Writer Gate Design and Mock Acceptance

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuity, authorized Proxy 2 successor  
**State:** Pure test-only acceptance model and reviewed implementation contract  
**Source of truth:** GitHub; live `ApolloHubTodoStore.qml` remains the JSON writer  
**Live Hospital registration:** Not established or asserted

## IMPLEMENTATION

M11e PR #788 is merged. M11d maps every currently known
TASKS/TODAY/PLANNER/Hub writer into the one
`ApolloHubTodoStore.stage()` entrypoint; M11e has a standalone
synthetic `FileView` but no durable OS ownership. M11f now formalizes the
**future host ↔ FileView handshake** without patching the real singleton.

New `services/projects/TaskWriterGateMockM11f.js` is a **pure,
unmounted, deliberately forgeable mock**. It cannot read or write files.
Its synthetic owner receipt models an OS-owned epoch, session ID,
source hash and a drained callback queue. This is **not** a real
`flock` token or evidence of ownership.

The reviewed future call sequence is:

```text
OS-owned host starts; production gate is independently operator-enabled
  -> inspect actual owner epoch, legacy source and pending callback journal
  -> stage() asks host for DURABLY RESERVED stage ID and source baseline
  -> reserve receipt matches session, epoch, stage ID and source hash
  -> ONLY THEN assign pendingDocument and call FileView.setText()
  -> FileView.onSaved => readback VERIFYING, not "saved"
  -> compare actual disk bytes to staged bytes through safe OS-owned host
  -> host durably records matching stage settlement
  -> ONLY THEN publish confirmed document and "ready"/"empty" state
  -> freeze persists closed stage admission before any acknowledgment
  -> already-reserved save finishes or enters RECOVERY_REVIEW
  -> new OS owner starts in RECOVERY_REVIEW, never silently rearms
```

The current live `ApolloHubTodoStore.qml` has asynchronous
`onSaved`/ `onSaveFailed` callbacks, but does **not** yet reserve a
durable stage with an OS owner, verify the exact written bytes and
durably settle one epoch-specific operation before publishing it.
Replacing `onSaved` with blind trust in an injected QML boolean is
not an acceptable shortcut.

M11f's mock models every handshake phase:
`BOOT_LOCKED`, `MOCK_READY`, `MOCK_RESERVING`,
`MOCK_SAVING`, `MOCK_VERIFYING`, `MOCK_SETTLING`,
`MOCK_FREEZING`, `MOCK_FROZEN` and `RECOVERY_REVIEW`.
A freeze requested during any stage immediately closes **new**
admission, and actual completion must occur before mock-freeze
acknowledgment. Interrupted or stale responses enter recovery review.
Even a successful mock receipt only returns `mockStageEligible:true`
for a synthetic fixture. All outputs keep
`productionWriteAuthorized:false`, `sqliteWriteAuthorized:false`,
`migrationAuthorized:false` and `remoteWriteAuthorized:false`.

A machine-readable implementation checklist exists at
`tests/tasks/fixtures/task_writer_gate_review_m11f.json`.
It explicitly requires a separate approval to modify any live writer,
a native Quickshell test, backup/rollback, and further approval to
migrate/activate SQLite.

## HOW TO USE

Run the repository-only acceptance suite:

```sh
node tests/tasks/test_task_writer_gate_mock_m11f.cjs
python3 tests/tasks/test_task_writer_gate_design_m11f.py
node tests/tasks/test_task_fileview_gate_policy_m11e.cjs
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

No local desktop or GitHub Projects action is involved.
`TaskWriterGateMockM11f.js` is **not imported anywhere in
production QML** and must not be wired into TASKS.

## VERIFY

Tests exercise normal synthetic two-save ordering, durable reservation
receipt and settlement expectations, readback evidence, freeze requests
during all five pre-freeze phases, stale epochs, wrong stage IDs,
fabricated receipt fields, invalid synthetic source, duplicate
callbacks and restart into review. They assert every reply
**denies production authority**.

Separate source auditing confirms the actual production singleton and
its current FileView callbacks remain unchanged, all existing task
mutation routes still converge on the current writer, and M11e/M11d/
M11c/M10p regressions continue to pass.

**CI cannot prove real owner identity**, no matter how many booleans
the mock checks. Those synthetic receipts can be forged. Proof must
come from an OS-enforced lifetime lock, durable stage journal and
independently verified native host/Quickshell acceptance.

## WATCH OUT FOR

There are two **distinct** approvals, neither given by merging this PR:

1. Permission to run the separate M10z and M11e native Quickshell
   acceptance on private synthetic fixture files on the operator's PC.
2. Permission for an exact audited patch to the production
   `ApolloHubTodoStore.qml` gate and its durable host service.
   Subsequent activation/migration requires another explicit approval.

A production patch must leave normal TASKS operations unchanged while
the new gate is **disabled by default**. An enabled but unverified gate
must fail closed without replacing the last confirmed document or
automatically opening an empty writable store. Any rollback must
restore the exact prior program/configuration and **not** silently
overwrite task data or introduce a second concurrent writer.

The tentative production patch footprint is limited to a host-owned
admission/settlement protocol, explicit enabled-by-operator setting,
one `stage()` interception point, and matching
`onSaved/onSaveFailed/onLoaded/onLoadFailed/reloadFromDisk`
callback fencing. The exact implementation is still subject to
on-device acceptance and independent review, with no work underway
on the user's local Quickshell checkout.

The mock does **not** solve remote GIT identity, custom field parity,
unified journal versioning, process failure after a checkpoint or
physical power-loss durability.

## CHECKLIST

- [x] Verify M11e merged and inspect current store/policies/authority
- [x] Define mock host reservation, save, readback, settlement and freeze
- [x] Deny stale receipts and callback/restart ambiguity
- [x] Add source preflight to prohibit importing mock into real TASKS
- [x] Add standalone acceptance tests and regression CI
- [ ] All GitHub checks and independent source review complete
- [ ] Operator approves PR merge
- [ ] Separate permission for native disposable Quickshell acceptance
- [ ] Exact production patch reviewed and explicitly authorized
- [ ] Native ownership, source backup, restart and recovery verified
- [ ] Separately approved migration and SQLite activation

## NEXT

M11g should either consume **real M10z/M11e native runtime acceptance
evidence** (if operator-authorized and available) or continue with
an isolated OS-owned host-to-FileView bridge fixture. It must not
activate production TASKS and must preserve current assignment boundaries.

## DECISIONS

The active JSON FileView remains the sole task authority. SQLite
remains inactive. No desktop processes, user files, production
services, real TASKS records, GitHub Project writes or live Hospital
assignments were modified for M11f.
