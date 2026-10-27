# 🏥💜 TASKS M11r // Session-bound test-host transport and native fault acceptance kit

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room:** TASKS guarded JSON continuity, following M11q  
**Worker:** External Hospital-compatible ChatGPT doctor, not live Hospital registered  
**Branch dependency:** M11r is *stacked on the unmerged M11q PR #862*; review and merge in order. No new production or local approval inferred.  
**State:** GitHub test-only protocol hardening; **native Quickshell fault cases remain awaiting operator observation**.

## IMPLEMENTATION

M11q added an in-memory QML generation guard for stale callbacks and four explicitly armed synthetic faults. It left the M11m host protocol tied only to small request IDs and writer ID, which is insufficient to distinguish independently launched host processes. M11r adds **test-only** session binding:

- `TaskJsonGateTransportM11m.py` creates a cryptographically random 48-character lowercase hex `sessionId` on each successfully attached disposable owner process with `secrets.token_hex(24)`. It includes that ID in the initial `hello` and **all** following replies.
- **Every** follow-up request (`status`, `reserve`, `verify`, `fail`, `freeze`) must have the **exact** session ID and exact request-key set, in addition to the existing monotonic request ID. A missing, altered or earlier process's session ID causes a closed response and terminates the protocol without a test write.
- `TaskJsonGateHostBridgeM11m.qml` accepts and stores the initial process's session ID only during the current expected `hello`. Before consuming subsequent replies, it checks the returned session ID against the stored value. It clears the ID on any rejection, STOP or host exit.
- The owner remains `m11l-tasks-copy/todo-copy.json`-restricted, single-`flock`, durable `stage_history` v2, independently hash-verified, and **incapable of writing the JSON copy itself**. The only `FileView.setText` is in the standalone test harness.
- `TaskNativeFaultInspectorM11r.py` adds a read-only inspector for one *new*, private synthetic fault fixture. It opens the journal in SQLite `mode=ro`, validates the source/backup identity, compares observed JSON counter, owner digest and stage tombstone against the requested fault, and reports a small path-/task-/stage-ID-redacted result. It never initializes, resets, erases, upgrades or writes a journal.

### Exact expected native fault matrix

| Fault armed on M11q standalone panel | Test JSON | Owner stage history | Source matches settled hash? | Fresh owner |
| --- | --- | --- | --- | --- |
| `AFTER_RESERVE` | synthetic counter 0 | one `RESERVED`, pending | yes | `RECOVERY_REVIEW` |
| `AFTER_SAVED` | synthetic counter 1 | one `RESERVED`, pending | no | `RECOVERY_REVIEW` |
| `AFTER_READBACK` | synthetic counter 1 | one `RESERVED`, pending | no | `RECOVERY_REVIEW` |
| `AFTER_SETTLEMENT` | synthetic counter 1 | one `SETTLED`, no pending | yes | `RECOVERY_REVIEW` |

The **first inspection is before reopening the owner** and normally reports `JSON_ACTIVE` as the last durable phase. The second inspection, after an `EXISTING` attempt in a new standalone host process, should report `RECOVERY_REVIEW`. The inspector never converts either state to success or makes data writable. An ordinary successful FileView callback and a host-verified durable commit are different events.

**Observed acceptance:** The M11n successful synthetic save/recovery evidence exists. The four M11q/M11r *new* native fault runs have **not** been observed in this milestone. CI simulates equivalent isolated source/journal states only.

## HOW TO USE

**No local machine action in this PR.** For a future explicitly approved native test, take a **new separate clone** of the stacked changes or the eventual merged M11q/M11r source. Never `git pull`, reset, clean or checkout the operator's existing dirty `~/.config/quickshell` tree.

For **each** of the four faults, create an independent, new, private parent folder; use `TaskJsonGateSeedM11m.py --private-parent /absolute/private/parent` exactly once; open `TaskJsonGateHarnessM11m.qml` standalone. Enter its new `.../m11l-tasks-copy/todo-copy.json` path, click **NEW TEST**, cycle **ARM FAULT** to the target, then click **INCREMENT** exactly once. The armed synthetic fault is explicitly opt-in. Do not reuse one interrupted journal for another case or touch actual TASKS.

Once the host has stopped, use this **read-only** command from the separate clone, replacing the two placeholders:

```sh
python3 -B -I tests/tasks/fixtures/TaskNativeFaultInspectorM11r.py \
  --test-file "/ABSOLUTE/PRIVATE/m11l-tasks-copy/todo-copy.json" \
  --fault AFTER_RESERVE
```

For the same fixture, separately launch a fresh standalone harness and choose **EXISTING**. It should refuse admission with recovery review. After stopping the fresh host, repeat the inspector command with `--after-existing`. Use `AFTER_SAVED`, `AFTER_READBACK` or `AFTER_SETTLEMENT` as appropriate, always in a *different* private folder. Share only the sanitized status line and the panel's redacted event summary, not task JSON, private paths, database files, or screenshots of unrelated apps.

The inspector's `expectationMet: true` describes only **read-only durable copy inspection**. Its `nativeCallbackTraceObserved: false` deliberately does not claim to have witnessed QML callbacks. CI cannot substitute for human-observed native display events or exact failure timing.

## VERIFY

Run source-only and temporary-directory CI tests on GitHub:

```sh
python3 tests/tasks/test_task_json_gate_transport_m11m.py
python3 tests/tasks/test_task_native_fault_inspector_m11r.py
node tests/tasks/test_task_native_callback_guard_m11q.cjs
python3 tests/tasks/test_task_production_preflight_m11q.py
python3 tests/tasks/test_task_stage_replay_crash_m11p.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

The transport matrix verifies an unpredictable per-process session token, missing-token denial, token-echo consistency, and cross-process replay refusal, while preserving prior M11m reserve/verify/freeze behavior. The read-only inspector's test matrix checks all four synthetic journal outcomes, refuses wrong source content and wrong path, and never includes private paths or stage IDs in stdout.

**This is correlation fencing, not endpoint authentication.** A fresh nonce exchanged over the same unauthenticated stdout/stderr transport cannot prove the Python executable's identity or protect against a malicious replacement process. Real production integration requires verified executable identity, startup trust chain, source owner scope, process lifetime and a separately reviewed protocol/rollback plan.

## WATCH OUT FOR

- **Do not merge M11r ahead of M11q.** It is intentionally a stacked PR; M11q is a separate unmerged review/acceptance boundary.
- `M11M_TEST_0` sample data is only a synthetic fixture; the inspected path must have the exact private owner-only folder and filename.
- Existing M11n v1 test journals are incomplete-history `RECOVERY_REVIEW` and cannot be safely rearmed, reset or treated as new experiments.
- A nonce does not authenticate the host if an attacker controls both host and output. `FileView` callbacks themselves lack durable stage identity and real live data must not be used for M11r.
- No production `ApolloHubTodoStore.qml`, task policy, `shell.qml`, live source path, startup option, migration, GitHub Projects writer or active Hospital service is changed.
- The SQLite database is a disposable **admission journal**, not a SQLite TASKS-data migration.
- Freezing while an actual native save is in flight, live rollback, power-loss durability and production host identity are **still pending**.

## CHECKLIST

- [x] Current `main` and M11q draft ownership verified before branching
- [x] Stack M11r on M11q instead of omitting unmerged callback improvements
- [x] Bind every disposable host request and response to a fresh session ID
- [x] Reject earlier-session, missing-session and replayed test protocol frames
- [x] Add privacy-safe read-only inspection for all four new native fault cases
- [x] Preserve M11p stage tombstones, earlier M11m transport semantics and M11q callback gates
- [ ] Green M11r CI on final head
- [ ] Independent source review of nonce, OS process identity and response checks
- [ ] Operator-observed native fault cases, each on a **new** private fixture
- [ ] Authenticated production host and guarded asynchronous `stage()` contract, separately approved
- [ ] Separate approval for production deployment, rollback, merging and SQLite task migration

## NEXT

Finish CI, then obtain synthetic native callback observations without altering the operator's current Quickshell installation. A future milestone must design an actual **production host trust chain**, independently validated backup and UI mutation-return contract before touching the real writer. Do not promote transport nonce evidence alone to production readiness.

## DECISIONS

M11r is GitHub-only, stacked, and a draft. **No merge, no local machine modification, no production authorization, no live Hospital registration.** Production TASKS continues using its existing JSON FileView, `guardedWriterEnabled: false`, and six-state public snapshot. The four fault observations remain unproven.
