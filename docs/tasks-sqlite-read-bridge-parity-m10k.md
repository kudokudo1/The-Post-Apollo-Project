# 🏥💜 PROXY 1 // M10k SQLite Read Probe and Model Parity

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment scope:** Proxy 1, storage engine / read interface prototype.  
**Operator choice:** Option B // SQLite.  
**Source of truth:** GitHub. Hospital registration/ownership is not implied.

## IMPLEMENTATION

M10j established an experimental SQLite backend with versioned JSON model,
transactionally maintained search indexes, stale-revision protection and
startup recovery inspection. M10k verifies the **boundary between the Python
SQLite adapter and the existing JavaScript version-2 task model**, and adds a
**non-mounted, read-only Quickshell status interface**.

Three new components, plus tests and CI:

- `services/projects/TaskSqliteReadProbe.py`: explicit `--db` argument
  required. Loads the M10j adapter and uses its read-only `read()` path.
  A missing database remains absent; it never initializes, migrates or saves
  task data. Only returns bounded JSON metadata: status, revision, project,
  task, operation and blocked-operation counts, and fixed
  `writeReady:false`/`remoteWriteAuthorized:false`. It intentionally never
  outputs task titles, descriptions, custom values, GitHub identifiers or
  local filesystem paths.
- `services/projects/TaskSqliteReadBridge.qml`: a standalone `Scope`
  containing a Quickshell `Process` + `StdioCollector`. Only an explicit
  `requestStatus()` call with a caller-supplied absolute `tasks.db` path
  starts the probe. It has no default path, startup timer, import by live
  widgets, FileView, writer or remote operation. It accepts a tightly
  validated status shape, discarding command stderr and unexpected output.
  **This is source-level wiring only**, not an on-device runtime connection.
- `tests/tasks/fixtures/model_v2_parity_oracle.cjs` plus
  `tests/tasks/test_task_sqlite_read_parity.py`: synthetic fixtures are
  checked by independent Python `validate()` and JS `verify()`. The suite
  checks valid records, NORMAL/GIT identity shapes, timestamps, field types,
  invalid version, missing/extra fields, remote operation state and counters,
  then invokes the CLI against disposable SQLite databases.

The test confirms that after a SENDING operation is locally committed, a
read-only startup probe reports `RECOVERY_REVIEW`; it neither repairs the
journal nor treats SENDING as a GitHub acknowledgement. Damaged database
indexes cause a generic error, not automatic repair or a fabricated empty
dataset.

## HOW TO USE

CI only:

```sh
python3 tests/tasks/test_task_sqlite_read_parity.py
```

The probe can be called by a future **explicitly approved** test host using
its `--db` argument, but no operator local command, database initialization
or live Quickshell test is part of this milestone. There is no actual TASKS
SQLite database installed by merging M10k.

## VERIFY

- Cross-language subset validation of 35+ representative synthetic inputs.
- Explicit-path helper produces only safe bounded metadata.
- No default DB path; absent DB read leaves filesystem unchanged in tests.
- Quickshell bridge is unmounted and explicit-call-only.
- SQLite committed normal/pending/SENDING states appear as READY or
  RECOVERY_REVIEW appropriately.
- Corrupt index, malformed path and future/unsupported schema fail closed.
- Existing M10j SQLite transaction, M10h model and TimeW database regressions
  run alongside this suite.

## WATCH OUT FOR

These fixtures establish parity **only for the tested subset**. The Python
and JS validators are not formally equivalent for every Unicode edge case,
numeric edge, string length, or future schema extension; unknown records
remain blocked. JS imposes a character-size limit while the Python storage
boundary additionally enforces UTF-8 bytes. Complete parity, native Qt/QML
runtime acceptance and deployment checks are still outstanding.

SQLite in WAL mode may use SQLite-managed `-wal`/`-shm` sidecar behavior.
Read-only at the *application API* level does not promise that every
filesystem metadata operation is absent. This implementation does not
write user task records or intentionally open a writable TASKS connection.

The existing `ApolloHubTodoStore.qml` is the live task writer. The
experimental Python module has no active Quickshell caller. The QML probe is
unmounted, has no database-path default, and supplies no write API. No
`tasks.db` on the operator's machine is touched. The chosen durable SQLite
schema remains a **snapshot plus indexed projections**, not the final
normalized record-oriented design.

Neither the presence of `PENDING` nor a valid GitHub-shaped remote ID
authorizes a remote write. Future M10+ work must explicitly verify identity,
permissions, current remote baseline, conflict outcome and remote read-back.

## CHECKLIST

- [x] Inspect current main and merged M10j PR #644
- [x] Isolate read-only CLI / metadata contract
- [x] Add standalone unmounted Quickshell Process seam
- [x] Test shared JS/Python schema acceptance on synthetic fixtures
- [x] Verify pending/uncertain operation startup visibility and fail-closed errors
- [ ] Confirm CI and independent review
- [ ] Operator-authorized merge
- [ ] Full Unicode/number/size cross-language parity
- [ ] Test real QML runtime in isolated disposable storage
- [ ] Design final record-level schema and backup/restore
- [ ] Separate operator-authorized production migration

## NEXT

M10l can prototype record-oriented SQLite mutations and Python/JS parity
hardening, followed by isolated QML runtime acceptance. Preserve the legacy
store as the sole active writer until a reviewed single-authority cutover
and reversible backup/restore test passes.

## DECISIONS

Option B remains adopted. No edits to live
`ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`, `TasksW.qml`,
`TaskPlannerPane.qml`, `shell.qml`, GitW, TimeW or Hospital-owned files.
No local-machine write, Quickshell restart, migration, Hospital registration
or production activation permission is inferred.
