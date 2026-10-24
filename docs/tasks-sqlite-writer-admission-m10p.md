# 🏥💜 Proxy 1 // M10p Disposable Writer Admission & Durable Ownership

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1 (external development work; no assumption of live Hospital registration).  
**Operator choice:** SQLite is the future TASKS backend; **JSON remains the live authority**.  
**Scope:** New, disposable, Python test fixture only. No existing QML store changes or local desktop writes.

## IMPLEMENTATION

M10o's pure `TaskSqliteWriterHandoffPolicy.js` specifies phases and fails closed,
but deliberately does not enforce ownership. M10p adds a concrete **test
fixture**, `tests/tasks/fixtures/TaskSqliteWriterAuthorityFixture.py`,
that combines:

- Linux `fcntl.flock(LOCK_EX|LOCK_NB)` on an OS-owned lock file with
  SQLite WAL, `synchronous=FULL` and an atomic, schema-versioned authority
  row. The test path must be supplied explicitly, end with
  `handoff-test.db`, and reside inside an existing private directory.
- Explicit test-only initialization into `JSON_ACTIVE`. A new owner may
  not bootstrap over an existing DB, and opening an existing DB always
  advances its epoch and persists `RECOVERY_REVIEW`, even when the previous
  process left a `JSON_ACTIVE` record behind.
- `admit_stage(token)` as a **simulation** of an admission decision. It
  records at most one outstanding stage token while JSON_ACTIVE. A second
  stage cannot be admitted until that token is settled.
- `freeze(expected_epoch)` persists the frozen admission phase in one SQL
  transaction. If an old `FileView` save is still outstanding, its token
  is retained so a matching simulated `onSaved` or `onSaveFailed` can
  resolve it, but **no new stage** can enter.
- `settle_stage(token,saved=bool)` rejects stale or duplicate callbacks;
  failed saves force RECOVERY_REVIEW.
- `record_quiescence(first_read,second_read)` refuses pending writes,
  unequal/empty source bytes, or non-frozen authority. Matched synthetic
  bytes set JSON_QUIESCED and store a SHA-256. This is not proof that the
  real Quickshell file is physically frozen.
- `close()` relinquishes the file descriptor and flock. Process termination
  releases the OS lock automatically. Reopening the DB **always** enters
  RECOVERY_REVIEW, blocking admission until a separately designed, reviewed
  recovery method exists.

The test fixture has no CLI, `tasks.db` target, default storage path,
Quickshell importer, GitHub operation, `SQLITE_ACTIVE` phase or production
activation function. Every response reports `sqliteWriteAuthorized:false`
and `liveChangePerformed:false` where applicable.

## HOW TO USE

CI or an authorized developer's disposable test environment only:

```sh
python3 tests/tasks/test_sqlite_writer_authority_fixture.py
```

The test creates its own `tempfile.TemporaryDirectory` roots. No operator
desktop command, live QS restart, migration or task-file modification.

## VERIFY

- A distinct OS process attempting to acquire the same flock receives
  `OTHER_PROCESS_OWNS_HANDOFF`.
- One pending FileView-like token is admitted; a second is refused.
- A freeze is persisted while the first token is pending; no further stages
  can enter. Invalid epoch, mismatched token and save failure are rejected.
- Two synthetic byte buffers must match after draining.
- A new owner after graceful closure or `os._exit()` is forced into
  RECOVERY_REVIEW, including a crash with an in-flight save and frozen state.
- An old epoch cannot be reused to re-freeze or resume the writer.
- Non-private directories, symlinks, missing DBs and implicit creation are
  refused.
- Existing M10o contract, M10n backup/rollback and M10l SQLite task
  transaction suites rerun in CI.

## WATCH OUT FOR

**Do not mistake this fixture for a live writer gate.** The current
`services/hub/ApolloHubTodoStore.qml` still writes
`Quickshell.dataDir + "/apollo-hub-todo-v1.json"` and never calls this
fixture. Changes here do not stop TASKS, TODAY, PLANNER, Apollo Hub or other
legacy callers from invoking `stage()` in the real process.

- `flock` is advisory. Noncooperative writers that ignore the lock remain
  possible; real protection requires guarding **every** existing writer
  entry point, including startup paths and save callbacks.
- A privately created `handoff-test.db` is deliberately not the real
  SQLite TASKS database. The fixture must never open an actual
  `tasks.db` or issue a remote API mutation.
- The test's caller-provided byte buffers do not prove stable disk content,
  physical power-loss durability, real QML writer quiescence or backup
  validity. SQLite lock ownership alone does not protect JSON bytes.
- A new process always refuses to resume stage admission. A real runtime
  will need an explicit, operator-reviewed rearm/recovery path, so it
  does not unnecessarily lock users out after ordinary Quickshell restarts.
- This prototype permits only one in-flight stage token, consistent with
  the current `storageState==="saving"` guard. The future host needs
  verified token generation and callback wiring instead of trusting
  supplied strings.

Before any approved QML integration: (1) freeze every actual JSON
`stage()` entry including direct calls from TODAY/PLANNER, (2) drain
`FileView.onSaved/onSaveFailed`, (3) re-read and hash source bytes through
an authorized source-file reader, (4) enforce durable owner epoch in
the SQLite process service rather than UI booleans, (5) prove all existing
task/project/agenda operations, (6) preserve standalone rollback/backup
authority, and (7) add isolated actual Quickshell runtime acceptance.

## CHECKLIST

- [x] Verify M10o PR #665 merged and active JSON writer unchanged.
- [x] Add disposable OS-backed exclusive ownership and SQLite epoch.
- [x] Refuse new stage requests after durable freeze.
- [x] Test in-flight save drain and failed callbacks.
- [x] Fail closed after process exit, abnormal termination, or stale tokens.
- [ ] GitHub CI / independent source review.
- [ ] Operator-authorized M10p merge.
- [ ] Actual QML admission-gate integration, live runtime test and safe rearm.
- [ ] Separately authorized migration/SQLite activation.

## NEXT

A follow-on **M10q** should design/verify the real Quickshell host interface
that transports durable authority decisions to
`ApolloHubTodoStore.stage()`, with initial deployment in a fail-safe,
non-activating mode. The actual QML singleton change, local pull/restart,
and live cutover require specific operator approval.

## DECISIONS

Option B SQLite stays selected; **legacy JSON remains live**. M10p tests
ownership in disposable files and makes no modifications to the existing
UI, Proxy 2's PLANNER, GitW, Hospital, or remote GitHub Projects. No
live Hospital registration or desktop write authorization is inferred.
