# 🏥💜 TASKS M12a // Synthetic guarded completion and last-confirmed view contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M12a source-only model of guarded request, reservation, settlement and recovery UI  
**DOCTOR //** External ChatGPT worker; not live Hospital-registered  
**PROVIDER //** OPEN AI // CHATGPT  
**REVIEW BASE //** GitHub `main` at `37c1535dc4e6c91f9dad9e8f76425765715e8882` (October 31, 2026); recheck before implementation  
**CLASSIFICATION //** **PROPOSED PRODUCTION-SHAPED CONTRACT / TEST-ONLY MECHANISM**, no real host or production source patch.

## IMPLEMENTATION

M11t/M11x established the outstanding production trust, callback and UI gates. M11y exercised synthetic signed code-content checks and M11z exercised disposable backup and code-only rollback rules. M12a **does not combine these into a real host**: their independently verified authorities, operator-controlled root and real-data scopes remain unresolved. Instead, M12a isolates one risky **shared UI seam**, providing a pure, deterministic simulated protocol with negative tests.

### State, data and ownership

New `tests/tasks/fixtures/TaskGuardedCompletionModelM12a.cjs` is a Node.js-only, import-only JavaScript state model. It has no filesystem API, subprocess, QML, `FileView`, real path, SQLite journal, deployment flag or mutation caller. Only the tests create synthetic v3 task objects in memory.

- **Default off:** `DISCONNECTED` denies requests until tests explicitly attach a simulated owner. Mock `testTrustCheck`/`testBackupReadback` booleans are not real trust checks or real backup attestations. The code deliberately labels every view `syntheticOnly:true`, `productionWriterAuthorized:false`.
- **Queued:** Valid synthetic policy result + stage ID may become `RESERVING`. The response is `{queued:true, admitted:false, saved:false}`: submitting a request is *not* a durable reservation or save. Only one in-flight request is permitted.
- **Admitted:** A fully matching simulated durable-reservation event (stage ID, owner session, epoch, generation, baseline hash and candidate digest) moves to `RESERVED`. No data is published. This simulates eligibility for a **later** FileView write, but this module cannot write.
- **Native notification:** `onSaved` or `onLoaded` never publishes a document. Native Quickshell callbacks lack their own durable stage ID. Duplicate, stale or early notifications are insufficient as completion proof. Native save/load **failures** during a pending request go to `RECOVERY_REVIEW`.
- **Settlement:** A strictly matching simulated host settlement with the exact independent-readback digest and an asserted durable-journal settlement moves the candidate into the confirmed snapshot. This asserts protocol ordering, **not** the provenance of the host-supplied fields. Actual host authentication/readback and native callback attribution remain future separate work.
- **Error/restart/freeze:** Mismatched reservation or settlement, host exit, or freeze during an in-flight stage enters nonwritable `RECOVERY_REVIEW`. The last confirmed snapshot and uncommitted candidate are not deleted, replayed, or published. A simulated host restart cannot silently rearm the model. Freeze without pending work enters `FROZEN`, with no automatic resume.

### Important public UI distinction

The existing `services/hub/ApolloHubTodoPolicy.js::view()` maps error/unsupported states to an **empty** visible task list. The M12a model deliberately returns an **alternate proposed read-only last-confirmed overlay** with `state:"error"`, `writable:false` and the **previous confirmed rows still visible** during review. It does **not** edit TodoPolicy, add a seventh state, or mount that overlay in TASKS/TODAY/PLANNER/Hub. A production UI decision remains **OPEN**. No visible UI change has happened.

The existing nine public mutation functions return synchronous Boolean values. M12a uses an explicit *test ticket* with `queued/admitted/saved` flags to expose the distinction; **this is not a decision to change their production API**. Future implementations must choose between M11x Option A (Boolean means queued only) and Option B (structured ticket plus completion events) and reconcile all four callers. A matching task snapshot by itself must never be mistaken for the durable settlement of a particular request.

### Failure and acceptance matrix

| Pure simulated condition | Expected evidence |
| --- | --- |
| Unattached synthetic owner | Requests denied; confirmed rows preserved |
| Missing mock preflight flag, stale baseline | Refuse, never writable |
| Valid request queued | `queued:true`, `admitted:false`, `saved:false`; candidate invisible |
| Second concurrent request | Refused without overwriting first |
| Valid reservation | Stage reserved; no confirmed publication |
| `onSaved` before reservation, repeated `onSaved`, delayed `onLoaded` | Cannot publish |
| Exact matching settlement/readback/journal assertion | Publish candidate once |
| Wrong stage, session, epoch, generation, baseline or digest | Enter review; preserve confirmed rows |
| Wrong settlement/readback, missing settlement assertion | Enter review; no false save |
| Native save/load failure | Enter review; previous rows visible |
| Host exit before or after reserve | Enter review; no automatic fresh-owner rearm |
| Fresh owner after previous settlement | Review, not automatic writable |
| Freeze with pending request | Review; no further admission |
| Freeze with no pending stage | Nonwritable `FROZEN` |
| Changed returned snapshot by UI | Internal confirmed data unchanged |
| Production singleton audit | One live `FileView`, nine mutations, guard still false, no M12a mount |

### Trust and verification limitations

The model uses in-memory SHA-256 of `JSON.stringify(document)` for deterministic *synthetic identity*; these hashes **are not canonical byte-for-byte hashes of real JSON files**. The synthetic owner and settlement events are plain JavaScript arguments and may be forged by a malicious caller; this module cannot establish OS or signed-release identity, durable SQLite transactions, actual backup integrity, atomic FileView replacement or crash/power-loss ordering. The test protects state transitions **assuming valid host evidence**, and refuses mismatched evidence. It does **not** satisfy M11t's `TRUST_EXEC`, `PROCESS_BINDING`, `SOURCE_BACKUP`, `STAGE_CALLBACK`, `UI_CONTRACT`, `RECOVERY_FREEZE`, `ROLLBACK`, `RUNTIME_ACCEPTANCE` or `ACTIVATION_APPROVAL` production gates. All nine remain **OPEN**.

## HOW TO USE

No new operator UI, local command, runtime service, backup or activation. GitHub Actions checks the proposed pure state model. A separate disposable checkout may run:

```sh
node --test tests/tasks/test_task_guarded_completion_model_m12a.cjs
```

Production TASKS, TODAY, PLANNER, Hub, the existing legacy JSON source, OS owner and user machine are unchanged.

## VERIFY

- Inspected current GitHub source: `ApolloHubTodoStore.qml` still contains one `FileView`, nine mutations through `stage(result)`, and `readonly property bool guardedWriterEnabled: false`.
- Verified M11z commit is an ancestor of current main; no open TASKS PR or competing M12a branch at initial inspection.
- Expected diff: exactly new M12a pure fixture, Node unit test, this report and dedicated CI workflow. No production code, startup, test-host path restriction or schema mutation.
- CI runs the new failure-order suite and prior M11z/M11y/M11x/M11t/M11d safeguards; a green check establishes test-source consistency, not native acceptance or a real executable trust chain.

## WATCH OUT FOR

- No actual task source or journal is opened. This is not live TASKS registration, production safety proof or a migration mechanism.
- **Simulated `journalSettled:true` is not a durable journal commit.** The real process must independently establish authenticated owner, exact bytes, settlement and no conflicting writers.
- A later production `onSaved` handler cannot simply borrow these in-memory checks and claim callback provenance. Ambiguous native callbacks must fail closed.
- The public read-only confirmed overlay is a **proposal**; existing `TodoPolicy.view()` is unchanged and can still hide error-state rows.
- Neither a merge nor CI run authorizes connecting the synthetic model to Quickshell, changing local files, installing a trust root or accessing actual task data.

## CHECKLIST

- [x] Verify current source, M11z merge and ownership
- [x] Model disabled owner, queued, reserved, settled, frozen and recovery review states
- [x] Model last-confirmed read-only overlay and explicit queued-vs-saved response
- [x] Add failure-order, stale/duplicate callback, owner-exit and snapshot-mutation tests
- [x] Preserve one live writer and existing public UI bindings
- [ ] Review CI and independent source evidence
- [ ] Operator review/merge
- [ ] Separate agreement on production trust anchor and asynchronous UI mutation API
- [ ] Separately authorize real integration, native testing, local changes and activation

## NEXT

Review M12a CI and PR. The next engineering boundary is a **separately scoped, disabled-by-default production-shaped host integration proposal**, with independently trusted real-source authorization and a native callback identity strategy, while retaining a single writer. This **cannot** be inferred safe merely from passing pure model tests.

## DECISIONS

**Implemented:** Synthetic-only state/response protocol and last-confirmed read-only view *proposal*, without user-visible behavior change.

**Open:** Actual production executable trust anchor, source/backup/owner binding, real native callback provenance, Option A vs B public API, UI overlay design, local native acceptance and rollback.

**Not authorized:** Production source modification, actual TASKS file access, live guarded writing, local Fedora change, Quickshell restart, SQLite migration, automatic recovery/data restore, PR merge or live Hospital registration.
