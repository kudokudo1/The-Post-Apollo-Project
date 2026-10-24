# 🏥💜 PROXY 1 // M10o Single-Writer TASKS Handoff Contract

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Canonical authority:** `Meta-Apollo-Logos-Syntagma/AGENTS.md`. User/operator decides activation.  
**Worker:** Proxy 1 for TASKS storage only; no assumption of a registered live Hospital Assignment or Session.  
**Status:** Pure, unmounted JavaScript handoff model with synthetic tests. SQLite Option B remains the target, **not** the live writer.

## IMPLEMENTATION

M10n PR #656 is merged. `ApolloHubTodoStore.qml` remains the sole active task writer. It uses `Quickshell.Io.FileView` with asynchronous `onSaved`/`onSaveFailed`, `atomicWrites:true`, `watchChanges:false`, and `blockWrites:false`, writing
`Quickshell.dataDir + "/apollo-hub-todo-v1.json"`.

M10o adds **`services/projects/TaskSqliteWriterHandoffPolicy.js`**, a pure state machine for a *future* single-writer host. This is not that host and does not change the current singleton. The contract's phases are:

| Phase | Contract meaning | New legacy staging in hypothetical host | SQLite writing |
| --- | --- | --- | --- |
| `JSON_ACTIVE` | Original writer still serves tasks | Permissible by *simulated* gate only | **Forbidden** |
| `FREEZE_REQUESTED` | Prevent new `stage()` entries, let already scheduled save finish | Forbidden | Forbidden |
| `JSON_QUIESCED` | Save callbacks settled, source raw bytes read twice with same SHA-256 | Forbidden | Forbidden |
| `SHADOW_VERIFIED` | Frozen source hash and separate SQLite candidate/backup model hashes agree | Forbidden | Forbidden |
| `AWAITING_OPERATOR` | All *review notes* present, but no production handoff performed | Forbidden | Forbidden |
| `RECOVERY_REVIEW` | Save failure, invalid session, crash/restart or uncertain transition | Forbidden | Forbidden |

All returned actions include `writeReady:false`,
`sqliteWriteAuthorized:false`, and `liveChangePerformed:false`.
`JSON_ACTIVE` only reports that the **hypothetical future QML caller's**
legacy `stage()` gate would permit its existing writer. It is *not* a
permission token; today the live `ApolloHubTodoStore.qml` does not consult
this policy.

The state machine's transition functions:

- `begin(sessionId,writerId)`: create an in-memory, bound-session review.
- `requestFreeze(state,sessionId,expectedSequence)`: advance into a freeze
  request. A real host must *atomically close admission to stage()* before
  acknowledging this transition. The M10o function itself does not do so.
- `observeDrain(..., evidence)`: refuse while a FileView save remains
  pending, callbacks have not settled, stage gate is not confirmed closed,
  store reports error, writer instance differs, or repeated raw-file hash
  reads differ. Explicit save failure transitions to recovery review.
- `verifyShadow(..., evidence)`: require frozen source SHA-256, identical
  candidate/backup SQLite model SHA-256, version-zero SQLite revision, zero
  blocked remote operations, and a still-quiesced legacy writer.
- `prepareReview(..., evidence)`: record reviewed owner/backup/runtime/
  recovery/rollback gates. **All values are self-attested planning notes,
  never authorization or proof of exclusive access.** The terminal phase is
  `AWAITING_OPERATOR`, *not* `SQLITE_ACTIVE`.
- `fault()` and `restartFromCheckpoint()`: enter
  `RECOVERY_REVIEW` and deny both writers. Even a serialized
  `JSON_ACTIVE` checkpoint never silently grants rights after restart.
- `checkpoint()`: only returns serializable text for a hypothetical
  durable handoff registry. It does not persist files.
- `gate()`/`inspect()`: return summary/simulated stage decision, never
  an active SQLite writer capability.

Every transition is copy-based and checks the explicit session identifier,
sequence and expected phase. Stale async callbacks, wrong writer instances,
unknown fields, forged `SQLITE_ACTIVE` phase and corrupt checkpoints fail
closed.

## HOW TO USE

Only synthetic Node CI:

```sh
node tests/tasks/test_sqlite_writer_handoff_policy.cjs
```

No Quickshell restart, local commands, live data migration or configuration
changes are needed to merge the PR. The new module is not imported by
`shell.qml`, TASKS, Apollo Hub or PLANNER.

## VERIFY

- Current legacy `stage()` is permitted *in the abstract* only while the
  protocol is `JSON_ACTIVE`.
- Beginning freeze immediately disallows new hypothetical staging, while
  an already-running FileView save is modeled as draining.
- Failed onSave callback, unclosed stage gate, mismatched writer generation,
  unsettled callback, error state or changed source readback refuse progress.
- M10n-compatible shadow/backup hashes, revision-zero and recovery blockers
  must agree before marking shadow verified.
- All self-attested review flags may be true but SQLite cannot be activated.
- All states recover to `RECOVERY_REVIEW` on simulated process restart.
- No transition or checkpoint carries an executable writer permission.
- The M10n cutover review and M10l SQLite mutation suites rerun in CI.

## WATCH OUT FOR

**M10o is a model, not enforcement.** A true single-writer guarantee cannot
be obtained from QML booleans or JS handoff states alone. The live singleton
still accepts `stage()` calls. The future integration must:

1. Introduce an actual admission barrier *inside*
   `ApolloHubTodoStore.stage()`, not just a disabled button. Every task
   mutation from TASKS, TODAY, PLANNER, Hub, and other clients uses that seam.
2. Disallow new legacy edits, then drain existing `FileView.onSaved` or
   explicitly stop on `onSaveFailed`. `blockWrites:false` does not itself
   prove an outstanding write has finished.
3. Check the original file's **byte** SHA-256 after callbacks settle. Read
   again while ownership is held; `watchChanges:false` requires deliberate
   external synchronization and source verification.
4. Persist the handoff barrier/epoch in a separately reviewed durable
   authority, enforce it across process restarts and competing OS writers,
   and prove lock ownership. The current pure checkpoint string is **not**
   persistent and a caller-provided `writerId` is **not** authentication.
5. Shadow-import only to a different private DB path, compare actual
   M10n migration parity, verify SQLite online backup, and rehearse restore.
6. Only under *separate* operator-approved deployment may one actual writer
   take over. Before its first edit, ensure JSON cannot resume while SQLite
   owns the task model, including after Quickshell restarts and crashes.
7. Never auto-restore an old JSON snapshot after SQLite accepts edits.
   Reconciliation must preserve new local changes and any uncertain remote
   state. This contract has no automatic rollback or Github sync.
8. Prove actual task-create, edit-details, schedule, assign-project, delete,
   and restore behaviors, not merely one `edit_task` operation. The M10l
   prototype still lacks several old writer APIs.

The model deliberately has **no** `SQLITE_ACTIVE` phase or activation
callback, so passing tests cannot be confused with a production switch.

## CHECKLIST

- [x] Confirm M10n PR #656 merged, current `main`, and owner boundaries.
- [x] Map actual async `FileView` save state and shared writer seam.
- [x] Specify serial session-bound freeze / drain / shadow / review protocol.
- [x] Reject stale callbacks, unsafe recovery and unsupported activation.
- [x] Add synthetic race/crash/restart/dual-writer tests.
- [ ] GitHub CI and independent source review.
- [ ] Operator-authorized M10o PR merge.
- [ ] True OS/durable writer ownership, QML host implementation and tests.
- [ ] End-to-end disposable desktop acceptance and separately authorized
      real-data migration.

## NEXT

**M10p candidate:** isolated QML admission-gate prototype and disposable
filesystem-backed ownership evidence design, with a complete old TASKS API
compatibility plan. Preserve current live singleton unchanged until
approved to modify the actual writer.

## DECISIONS

SQLite remains the chosen future backend. JSON remains authoritative today.
Proxy 2 retains PLANNER control. No source edits to the active
`ApolloHubTodoStore.qml`, current TASKS interfaces, Hospital, TimeW,
GitW, or remote GitHub Projects. No local-machine mutations and no
live Hospital registration or staff role inferred.
