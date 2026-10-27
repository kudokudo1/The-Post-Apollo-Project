# 🏥💜 TASKS M11t // Production host trust, guarded-writer acceptance, and rollback contract

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS JSON writer continuity, successor to M11s  
**Provider:** OPEN AI // CHATGPT, external Hospital-compatible; **not** live registered  
**Inspected source baseline:** `main` at `481f9f603818b78bd4da72cf2f643e0481b731e8` (2026-10-27). Recheck HEAD at any later implementation.  
**Classification:** **PROPOSED CONTRACT ONLY**. No production patch, live data, deployment, migration, or activation.

## IMPLEMENTATION

M11t **extends**, rather than replaces, [M11k's eleven-step production JSON writer preflight](./tasks-production-writer-gate-m11k.md) and [M11q's disabled-only integration inventory](./tasks-native-callback-preflight-m11q.md). It records the new M11s operator evidence and specifies independently reviewable acceptance gates for the remaining **production** boundary. Source-of-truth code remains unchanged.

### Evidence actually observed, and its limits

The operator exercised four separate, standalone M11m/M11q Quickshell fault runs on **private synthetic task copies**, supplied the native panel screenshots in conversation, and ran M11r's read-only disk/journal inspector both before and after `EXISTING` attempts. All final per-case inspections printed `expectationMet: true`. The `AFTER_SETTLEMENT` case passed on a **new one-off replacement fixture** after an earlier fourth-case test was interrupted at the wrong point. Accordingly, do not claim that the original four-case M11s aggregate suite itself returned `complete: true`.

| Native synthetic stop | Before fresh owner | After `EXISTING` | Meaning |
| --- | --- | --- | --- |
| `AFTER_RESERVE` | counter 0, pending `RESERVED`, source matches journal | epoch 1, `RECOVERY_REVIEW` | Reservation is not a FileView save |
| `AFTER_SAVED` | counter 1, pending `RESERVED`, source differs from journal | epoch 1, `RECOVERY_REVIEW` | Saved callback is not durable settlement |
| `AFTER_READBACK` | counter 1, pending `RESERVED`, source differs from journal | epoch 1, `RECOVERY_REVIEW` | Readback callback alone cannot settle |
| `AFTER_SETTLEMENT` | counter 1, `SETTLED`, no pending stage, source hash matches | epoch 1, `RECOVERY_REVIEW` | Durable commit may precede UI acknowledgment |

The standalone QML panel's in-memory callback trace and the **separate** read-only inspector are complementary evidence, not one authenticated transcript. The inspector always reports `nativeCallbackTraceObserved: false`. Raw screenshots are not attached to this repository; no source path, task content, journal file, or private identity belongs in the report. These observations do **not** prove hardware power-loss ordering, a production host, an executable trust chain, native callback provenance, rollback safety on user data, or a production TASKS integration.

### Production trust chain (must be independently implemented and verified)

1. **Explicit production scope.** A future production-only host must be a **different**, reviewable adapter. It must not relax the `m11l-tasks-copy/todo-copy.json` restriction of `TaskJsonGateCandidateM11l.py`, reuse `TaskJsonGateTransportM11m.py` as a production CLI, or mount the isolated M11m test QML. The actual source, if separately authorized, is `Quickshell.dataDir + "/apollo-hub-todo-v1.json"`.
2. **Executable provenance.** Define a pinned and trusted interpreter/script deployment path with ownership and permission checks, no untrusted `PATH` lookup or symlink escape, and content identity verified at launch (or a stronger operating-system-specific mechanism). Prove how a TOCTOU replacement and an altered local checkout are rejected. Never trust host-supplied strings, its self-reported PID or a freshly echoed nonce as proof of executable identity. Explicitly document the same-user adversary limit.
3. **Process + session + owner binding.** Tie one observed OS process lifecycle to one host session, one durable journal owner epoch, one canonical source identity and one active stage. M11r's random per-process `sessionId` blocks accidental cross-session frames but **does not authenticate the child program**. Deny forged, replayed, reordered or late stdout; host exit or uncertainty must revoke QML admission.
4. **Real source and backup.** Before an authorized guarded write, independently validate exact source bytes and v1/v2/v3 schema, safe path/permissions/link count and file identity, an independently rereadable byte-for-byte backup, source digest, journal generation and absence of ambiguous pending stages. Never map missing, damaged, unsupported or changed real data into an empty *writable* document. Advisory `flock` does not block unrelated processes that ignore it; verify source identity and content again at settlement and explicitly test external-writer races.
5. **Single write admission.** Preserve all nine public task/project mutation methods through `ApolloHubTodoStore.qml::stage(result)` and its single `FileView`. A guarded stage may write **only after** one OS-host reservation is durably committed for the exact expected candidate bytes, current source baseline and epoch. No legacy fallback if guarded admission fails, no simultaneous JSON/SQLite writers, no second QML save route, no automatic restart/replay of a pending stage.
6. **Native callback and UI contract.** `FileView.onSaved` is notification, never final proof. Deferred `Qt.callLater` reload must be scoped to the live generation/epoch/stage/path; actual host reread and journal settlement alone permit publication. Handle unsolicited, duplicated or late native callbacks as untrusted: if unique correlation cannot be demonstrated, enter review rather than infer success. The nine mutation methods currently return a synchronous Boolean, whereas a real reservation is asynchronous. Specify exactly what “request accepted”, “save pending” and “durably confirmed” mean to TASKS, TODAY, PLANNER and Hub *before* UI wiring. Preserve the six `TodoPolicy.view()` public states: `loading`, `saving`, `ready`, `empty`, `error`, `unsupported`.
7. **Crash, freeze and review.** Durable journal replay tombstones must survive process death and reject reused IDs. Close stage admission before freeze acknowledgment; only drain an already-reserved stage. A fresh owner must enter `RECOVERY_REVIEW` even if the previous stage was durably settled but the UI acknowledgment was lost, as observed in the synthetic `AFTER_SETTLEMENT` run. Do not auto-promote to writable just because the source hash matches.
8. **Reversible deployment, not data rollback.** Before any separately approved local test or activation, record the exact prechange source/config versions and restore route; prove independent backup readback and operator-readable reconciliation output. Recovery/rollback must quiesce both writer paths, preserve actual task JSON, backup and journal **byte-for-byte**, and restore code/config without restoring stale task data. Replacing live JSON from a backup is a distinct, **explicit, operator-authorized** data recovery action after source comparison. Do not `git reset`, clean, stash, pull into the modified live checkout, kill other Quickshell processes, or silently change app startup.
9. **Separate permissions and final authority.** Require distinct operator decisions for a real-source host patch, writer integration patch, merging that patch, any local installation/restart, inspecting actual task data, native local acceptance, activating guarded writes, data restoration, and any later SQLite migration. A draft/CI pass is not any of these approvals.

### Acceptance matrix / source gates

The source-only machine-readable companion is `tests/tasks/fixtures/task_production_trust_review_m11t.json`. Its gates are all **OPEN**, even with the four synthetic native faults accepted.

| Gate | Required evidence before a production activation proposal |
| --- | --- |
| `TRUST_EXEC` | Verified executable/script provenance, restricted launch and replacement/failure tests |
| `PROCESS_BINDING` | OS process identity tied to session, journal owner, epoch; malicious/replayed transport denial |
| `SOURCE_BACKUP` | Exact authorized-source identity, independent backup/readback, external-write race refusal |
| `STAGE_CALLBACK` | One writer; stage admission before save; no misattributed native callback or false UI success |
| `UI_CONTRACT` | Nine mutation return semantics and six public states verified across TASKS/TODAY/PLANNER/Hub |
| `RECOVERY_FREEZE` | Crash, settle-without-ack, replay, freeze/drain/restart always fenced correctly |
| `ROLLBACK` | Code-only rollback rehearsed with preserved source, journal, backup; conflicting data never overwritten |
| `RUNTIME_ACCEPTANCE` | Operator-authorized test in an isolated, production-shaped scope with repeatable redacted evidence |
| `ACTIVATION_APPROVAL` | Separate exact operator approval after all gates; no implicit SQLite or remote-write switch |

## HOW TO USE

No operator-local commands or UI changes. This document is for code review and future assignment/ownership negotiation, not a set of live TASKS instructions. On an isolated repository checkout or in GitHub Actions, the read-only source contract test is:

```sh
python3 tests/tasks/test_task_production_trust_contract_m11t.py
```

Normal **TASKS**, **TODAY**, **PLANNER** and the Apollo Hub To-do controls continue using the pre-existing JSON singleton. No guarded mode control exists or is installed by M11t.

## VERIFY

- Verified by source inspection at the documented GitHub baseline: `services/hub/ApolloHubTodoStore.qml` still has `readonly property bool guardedWriterEnabled: false`, nine mutators, one `FileView`, a single `stage(result)` write route, and legacy publication on `onSaved`.
- The operator's four isolated native cases had on-screen traces and separate pre/post restart read-only inspector outcomes matching M11r expectations. This **is not** a CI-executed native test and does not assert a passing original M11s batch aggregate.
- This M11t milestone adds **documentation, one JSON review record, one pure source/contract test and one read-only GitHub Actions job only**. Passing the static tests means source-boundary consistency, not production safety or authorization.

## WATCH OUT FOR

- Existing `M11k` and `M11q` are earlier proposed preflights. Do not silently amend their historical `nativeObserved: false` facts; M11t is the later acceptance record.
- An unpredictable nonce or valid `flock` does not prove child program integrity or exclude noncooperating same-user writers.
- A `SETTLED` journal is not proof that a replaced QML session received the acknowledgment. The precise fresh-owner behavior is intentional.
- The final `AFTER_SETTLEMENT` pass used a separate private replacement fixture. Keep the accidentally interrupted earlier fourth-case journal unchanged.
- Local Quickshell and GitHub may differ. Review all shared TASKS/Planner callers and concurrent changes again before implementation.
- Neither a SQLite task migration nor a real guarded production writer is present. This is **not** a full-system power loss test.

## CHECKLIST

- [x] Inspect M11k, M11q, M11r, M11s and current production singleton
- [x] Record native operator evidence with its actual provenance limits
- [x] Specify host trust, exact-source, callback, UI and rollback gates
- [x] Preserve one-writer, disabled-only and separate approval boundaries
- [ ] Independent review of M11t source contract and CI
- [ ] Separate operator-approved production host and writer **implementation** scope
- [ ] Trust-chain, real-source backup, interleaved native event and rollback test evidence
- [ ] Separate operator-controlled merge, local deployment and activation decisions

## NEXT

After review, define the **smallest disabled-by-default, production-shaped integration patch** against a newly inspected HEAD. First prove host executable provenance and safe source identity in a synthetic harness. Do not touch actual task bytes, the dirty local checkout, or `guardedWriterEnabled` without a newly scoped operator authorization.

## DECISIONS

**Operative:** M11s four-case **synthetic native fault matrix passed** as observed by the operator, with separate read-only journal inspections. `AFTER_SETTLEMENT` passed on the replacement fixture. Existing JSON FileView is still the live writer and the guarded flag stays false.

**PROPOSED, not operative:** Production host trust chain, integration, rollback acceptance sequence and M11t gate matrix. No merge, live Hospital registration, local writes, production activation, SQLite migration or remote GitHub write has been authorized by this contract.
