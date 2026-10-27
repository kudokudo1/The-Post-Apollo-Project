# 🏥💜 TASKS M11p // Durable Stage Replay Ledger and Abrupt-Exit Recovery

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS shared JSON writer continuity, following merged M11o  
**Worker:** OPEN AI // CHATGPT, external Hospital-compatible; not live registered  
**Scope:** GitHub-only **disposable** M11l/M11m OS owner/test rig, no production integration  
**Base:** `5a7ba5f73b8eda5004336fd6f3cb7b1a51004b9e`  
**Acceptance:** Source and GitHub Actions test evidence only, *not* production/native complete

## IMPLEMENTATION

M11o had one pending stage slot in its SQLite journal. After a successful `verify`, it erased that slot, so a later request could reuse a previously accepted stage ID. M11p adds a never-pruned **v2 journal** in the disposable `services/projects/TaskJsonGateCandidateM11l.py` owner.

- `stage_history`: `stage_id TEXT PRIMARY KEY`, original reservation epoch, intended SHA-256 digest, prior confirmed source digest and `state=RESERVED/SETTLED`.
- A `reserve` transaction first verifies no previous history row, then **atomically inserts the stage tombstone and records the pending stage**. The unique constraint remains after successful settlement. Reuse returns `STAGE_ID_REPLAY` even with different candidate bytes.
- `verify` first independently hashes the actual disposable JSON file. **In one durable transaction** it transitions the exact pending, original-epoch `RESERVED` history row to `SETTLED`, clears the pending stage and records the new confirmed source hash. A stale stage/epoch, changed bytes or missing history is denied.
- The owner checks that pending journal row and `RESERVED` history agree. A missing or orphaned history row fails closed and never triggers FileView.
- Bootstrap of a fresh synthetic test folder creates v2 from the start; the initial journal's parent directory is fsynced. The journal uses `PRAGMA synchronous=FULL` as before.
- **v1 compatibility is recovery-only.** On reopening an old synthetic v1 journal, migrate its pending ID (if any) to v2 `RESERVED` history, set `history_complete=0` and `phase=RECOVERY_REVIEW`. Historical *settled* v1 stage IDs cannot be reconstructed; therefore this fixture may never rearm. A fresh v2 authority alone has `history_complete=1`.
- No pruning, rebootstrap, automatic rearm, replay or rollback of user task data. No production CLI or new host writer.

### Crash windows

`tests/tasks/fixtures/task_stage_crash_probe_m11p.py` is a disposable subprocess with explicit abrupt `os._exit` (bypassing Python cleanup). It terminates **before reservation**, **after durable reservation**, **after a synthetic atomic file replacement but before settlement**, or **after durable settlement**. Tests reopen the journal under a fresh process owner and verify `RECOVERY_REVIEW`, preserved pending/tombstone state and unchanged synthetic source bytes. They specifically distinguish “file bytes changed” from “host settled stage.”

Two additional SQLite transaction-abort injections verify that an exception during reservation or settlement rolls back both changes atomically, leaving no half-committed ledger. Missing history rows and orphaned pending rows fail closed.

**Separate actual OS SIGKILL test:** a disposable child announces three precise checkpoints (reservation committed, file replaced before verify, or settlement committed). The CI test kills that child using `SIGKILL`, confirms Linux released the owner's lifetime file lock, and then checks the SQLite ledger/source bytes under a new owner. The new owner must enter `RECOVERY_REVIEW`, preserving unsettled vs settled distinctions. These are genuine killed subprocesses, still **not** a physical power-loss test.

**Important:** `os._exit` tests skip process cleanup but do not simulate kernel panic, real disk power loss, fsynced hardware write-cache semantics, or adversarial filesystem corruption. Those boundaries remain unproven.

## HOW TO USE

No new TASKS controls and no operator workstation commands. GitHub Actions test:

```sh
python3 tests/tasks/test_task_stage_replay_crash_m11p.py
python3 tests/tasks/test_task_json_policy_parity_m11o.py
python3 tests/tasks/test_task_json_gate_transport_m11m.py
python3 tests/tasks/test_task_json_gate_candidate_m11l.py
python3 tests/tasks/test_task_native_evidence_m11n.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

Each test uses new temporary `m11l-tasks-copy/todo-copy.json` files. **Do not** run `--bootstrap-test` on the operator's previous M11n fixture or treat its old v1 journal as current writable authority. The operator's local working tree, Quickshell instance and prior private test folder remain untouched.

## VERIFY

Tests require a unique ID after settlement, no silent re-arm after process exit, crash-safe pending/reserved vs settled distinction, and total prevention of stage acceptance on any incomplete legacy journal. They read the synthetic SQLite history directly, without trusting QML view state.

M11m standalone `TaskJsonGateHostBridgeM11m.qml` is still **unmounted** from `shell.qml`; its request IDs and stage tokens are not production authorization.

## WATCH OUT FOR

- Do not confuse **durable stage tombstones** with a guarantee of end-to-end exactly-once execution under disk power loss. Native FileView/OS crash windows and hardware durability still need acceptance.
- A full-lifetime registry requires unbounded on-disk growth for each accepted ID; future quota/compaction must retain a permanent anti-replay property and cannot silently delete tombstones.
- The v1 journal upgrade is deliberately irreversible and recovery-only. It cannot prove already-settled historical IDs. M11p does not authorize recovery re-arm or deletion/recreation of ambiguous test data.
- Source verification and stage ID claims are only for the disposable owner; the real `ApolloHubTodoStore.qml` retains its single JSON FileView with `guardedWriterEnabled: false`.
- Native callback traces for all failures, backup restore/rollback and production OS authority have not been accepted.
- No local machine, GitHub Projects, notifications, calendar or live Hospital record is modified.

## CHECKLIST

- [x] Verify latest GitHub `main`, M11o merge, source and no competing TASKS PR
- [x] Implement journal v2 durable stage history and exact-stage atomic settlement
- [x] Deny reused and corrupt stage IDs before FileView effects
- [x] Legacy v1 transition must enter recovery-only, with incomplete-history marker
- [x] Abrupt process exits at four boundaries plus explicit SQL transaction aborts
- [ ] GitHub Actions and regression checks pass on latest PR HEAD
- [ ] Independent review of journal schema/race/backup failure modes
- [ ] Native Quickshell crash-window evidence on disposable user-approved test fixture
- [ ] Distinct production QML+OS host integration with operator-approved change scope
- [ ] Separate operator authorization for activation, restore plan or SQLite cutover

## NEXT

Validate CI, adjust only real defects, and preserve this implementation as a draft PR until explicitly authorized to merge. Next review should focus on **proving journal durability and callback fencing end-to-end** without changing the production singleton's writer contract or enabling its guarded path.

## DECISIONS

A production JSON writer replacement remains **unimplemented and disabled**. M11p protects synthetic stage IDs, not the user's tasks. No SQLite task migration, local machine writes, production activation or Hospital registration is implied.
