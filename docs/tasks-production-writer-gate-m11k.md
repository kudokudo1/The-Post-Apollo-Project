# 🏥💜 TASKS M11k // Production JSON writer gate preflight

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / Assignment:** TASKS storage continuity, Proxy 1 → Proxy 2 succession  
**Status:** **PROPOSAL ONLY**, no active writer patch or activation  
**Baseline:** `main` at `de90effc094381117de0127eada0d4c444a207e2` (October 26, 2026)  
**Evidence:** [M11j observed native test](./tasks-native-acceptance-production-readiness-m11j.md), [M11d single-writer inventory](./tasks-sqlite-live-stage-integration-m11d.md)

## IMPLEMENTATION

The current production `services/hub/ApolloHubTodoStore.qml` contains one JSON FileView. Nine task/project mutation methods converge at `stage(result)`, which immediately assigns `pendingDocument` and calls `todoFile.setText()`. The current `onSaved` publishes `pendingDocument` without independent host-side source readback. TASKS, TODAY, PLANNER and Hub share this writer.

M11g's observed native test protected **only** a private synthetic fixture. Its OS lock is not authority for the real task file. The M11f mock is similarly not a production authorization mechanism.

### Proposed exact integration sequence (not installed)

1. **Disabled-by-default mode.** Keep existing legacy JSON behavior untouched while guarded mode is off. Being off does not mean OS-fenced. If guarded mode is requested without verified owner authority, deny all writes without falling back.
2. **Production-specific OS host.** Create a separately reviewed, long-lived host that holds the real advisory `flock`, records a durable owner epoch and journal, and refuses uncertain previous sessions. Never enlarge M11g's fixture-only path filter as a shortcut.
3. **Actual-source preflight.** Verify file identity, stable raw bytes/hash, version 1/2/3 validation, independently readable byte-for-byte backup, and outstanding journal. Missing/changed/ambiguous source must not become an empty writable task list in guarded mode.
4. **Stage admission.** Inside the single `stage(result)` entry, durably reserve exactly one stage ID, source baseline, expected bytes/digest and host epoch **before** setting `pendingDocument` or invoking `FileView.setText()`. Reject stale, duplicate and concurrent requests.
5. **Native callback.** Treat `onSaved` only as a save notification. Defer the post-save `FileView.reload()` with `Qt.callLater`, because M11g demonstrated that synchronous reload can race the native completion. Correlate all callbacks with the current stage and owner epoch.
6. **Independent settlement.** The host reads and validates the actual source bytes itself and durably settles exactly the reserved stage. **Only then** can the store publish `pendingDocument` as confirmed. On error, source mismatch or host exit, preserve the last confirmed task document and enter RECOVERY_REVIEW.
7. **Reload and freeze.** Fence `onLoaded`, `onLoadFailed`, `onSaved`, `onSaveFailed` and `reloadFromDisk()` by owner epoch. Persist closed admission before acknowledging freeze; drain only already-admitted work. Restart with uncertain authority always requires RECOVERY_REVIEW.
8. **Rollback.** Save the exact previous program/configuration revision and verify the source/backup independently before activation. Restoring code must **never** overwrite live JSON data, silently reset the operator's dirty Quickshell tree, restart unrelated services, or allow dual JSON/SQLite writers.

**Shared UI constraint:** `TodoPolicy.view()` knows six public states: loading, saving, ready, empty, error and unsupported. New asynchronous reservation/recovery progress cannot simply introduce a new storage-state string: unknown states currently display as an error/empty view. The exact UI representation and the synchronous mutation-return contract need review before any real patch.

## HOW TO USE

No visible TASKS behavior changes with M11k. Existing **TASKS → PLANNER → SCHEDULE**, TODAY and Hub continue to use the current JSON singleton. Repository-only review:

```sh
python3 tests/tasks/test_task_production_gate_review_m11k.py
python3 tests/tasks/test_task_native_acceptance_m11j.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

There is no workstation setup, `git pull`, stash/reset, Quickshell reload or local test file operation in this proposal.

## VERIFY

The machine-readable requirements and failure matrix are in `tests/tasks/fixtures/task_production_gate_review_m11k.json`. A source-only Python test verifies the proposal's status and current single-writer boundaries. GitHub CI should rerun that check and M11j/M11d regressions. CI success would show a consistent **review contract**, not a production gate, native failover proof or SQLite migration.

A later approved runtime matrix must test lock contention, wrong file identity, unsupported schema, conflicting external change, crash before/after save, stale callbacks, failed FileView save, deferred readback mismatch, host death, freeze while saving, restart review, and rollback without task-data changes.

## WATCH OUT FOR

- The six-state public snapshot and existing `stage()` return value are shared with multiple widgets. A hurried asynchronous integration could hide tasks or falsely report success.
- Legacy FileNotFound currently permits an initial empty document. That behavior cannot be copied to **uncertain guarded ownership** without review.
- Advisory OS locks do not constrain uncooperative external writers; preflight/readback and source identity checks remain necessary.
- Local Quickshell may contain unrelated modified/untracked files and could be behind GitHub. Do not reset or overwrite it.
- The production-specific host, exact source diff, native failure tests and independently tested rollback have **not** yet been delivered.

## CHECKLIST

- [x] Reconstruct M11j merge, current writer and current GitHub ownership
- [x] Record the ordered writer gate, callback and restart contract
- [x] Record fail-closed and backup/rollback requirements
- [x] Pin six-state public-view integration hazard
- [x] Add machine-readable design checks and GitHub CI
- [ ] GitHub CI and independent review
- [ ] Separate approval for exact production source patch
- [ ] Draft new real-source host and disabled-by-default QML integration
- [ ] Native failure, backup and rollback acceptance
- [ ] Separate operator approval before activation or SQLite migration

## NEXT

After review, build a separate **draft**, disabled-by-default production writer patch on a fresh reviewed head. Verify one OS owner, ordered admission/readback/settlement, shared snapshot compatibility, freeze/restart behavior and rollback. Ask for separate approval before merging or operating it against real data.

## DECISIONS

This M11k increment is a **proposal**, not a canonical activation decision. JSON FileView remains the only live writer; SQLite and remote GitHub Project writes remain untouched. Operator acceptance, merge, live-data access and active guarded mode each have distinct approval boundaries.
