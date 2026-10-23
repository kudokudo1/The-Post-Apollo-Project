# 🏥💜 Proxy 1 // M10i Durable Edit Transactions

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1 (external development assignment, not a live Hospital registration)  
**Dependency:** M10h draft PR #635 (`feat/tasks-proxy1-m10h-typed-model-timestamp-edits-20261023`), currently not merged at branch creation.  
**Scope:** Synthetic, CI-only Node transaction integration. Not deployed desktop storage.

## IMPLEMENTATION

M10i composes two previously reviewed pieces **without modifying either**:

- M10h `UnifiedProjectModelV2.js` validates and produces immutable local edits, timestamps and same-envelope GIT pending operations.
- M10f `single_writer_gate_fixture.cjs` uses an exclusive cooperative lock and validates expected revision and full source hash before a same-directory atomic-replacement test write.

New `tests/tasks/fixtures/durable_edit_transaction_fixture.cjs` introduces `transact(lease, expected, command, model, stopAt)`:

1. Reads and validates the current committed envelope while the caller owns an M10f test lock.
2. Requires the originally observed revision and complete SHA-256 to match. Rejects stale data before proposing an edit.
3. Calls exactly one reviewed M10h edit function: `editTask`, `editCustomValue`, `renameProject`, or `addLocalField`.
4. Encodes the **entire candidate envelope** including the edited task and any GIT pending journal operation. Computes its expected complete-file hash.
5. Passes that single new envelope through the existing M10f simulated atomic commit.
6. Reports `LOCAL_COMMITTED` and `localSaved:true` **only** after successful committed-file readback matching candidate revision and hash. Always reports `remoteSent:false` and `remoteWriteAuthorized:false`.
7. If a simulated interruption or commit error prevents verification, reports `COMMIT_UNCERTAIN` and `localSaved:false` instead. Caller must inspect and reconcile, not auto-resubmit.
8. `reconcile(lease, intent, model)` distinguishes exact already-applied local data, exact unchanged baseline, or unknown/conflicting local state using hash and revision. It is not a GitHub remote acknowledgement.

The test caller owns lock acquisition and release. It does not auto-release after uncertain outcomes, does not attempt stale-lock stealing, and does not implement asynchronous/background writes.

## HOW TO USE

Only GitHub CI, or isolated development fixtures explicitly controlled by a tester:

```sh
node tests/tasks/test_durable_edit_transaction.cjs
```

All writes happen in OS-created, disposable `mkdtempSync` directories. No live TASKS files, Quickshell data directory, network service or GitHub account is accessed.

## VERIFY

- GIT task edit commits **local content, timestamp, one stable pending operation and next-operation counter together**.
- A second sequential GIT edit creates a different operation; a stale baseline refuses replay.
- NORMAL edits, local-only GIT custom values, project renames and custom field definitions do not create accidental GitHub operations.
- Fault injection before and after candidate creation, file fsync, rename and directory fsync yields complete old or new envelopes in the current process simulation.
- Ambiguous outcomes remain unacknowledged until a separate reconciliation read; no automatic duplicate sends.
- Unknown external rewrites, unexpected versions and corrupt source fail closed.
- M10h schema, M10f writer-gate and M10e backup/restore suites run in the scoped CI workflow.

## WATCH OUT FOR

**This does not create a production durability guarantee.** Node exception injection is not an OS crash, physical power cut, or Quickshell runtime acceptance. `M10f` is a *cooperative* lock on disposable files; it cannot prevent noncooperative processes racing between check and rename, and is not connected to the live `ApolloHubTodoStore.qml` writer.

`COMMIT_UNCERTAIN` is a conservative local state. Even when an inspection observes the candidate file after rename, pre-directory-fsync physical durability remains unproven. A live implementation must not automatically release ownership and retry an ambiguous local or remote write.

**An offline intent is not a GitHub operation authorization.** Project and item identity shape checks are not authentication. The future sync adapter needs verified identities, baseline reads, conflict handling, operator-approved permissions, and remote readback before claiming a remote ACK.

The v2 schema introduced by M10h is itself still an unapproved prototype, and this branch is **stacked on PR #635**. It must not be landed as an independent production storage feature. The resulting PR is review-only until its dependency is merged or the branch is appropriately retargeted.

## CHECKLIST

- [x] Compose M10h immutable edit with M10f guarded commit
- [x] Require expected revision + source hash under test lock
- [x] Keep task data and pending GIT intent in one candidate envelope
- [x] Distinguish verified local commit from uncertain local outcome
- [x] Verify reconciliation and stale retry protection
- [x] Synthetic CI tests, no desktop or remote writes
- [ ] GitHub CI success / independent source review
- [ ] M10h dependency merge or reviewed retarget
- [ ] Operator-authorized M10i merge
- [ ] Actual Quickshell-compatible storage adapter + restart/power-loss acceptance

## NEXT

After review, specify the actual single-writer QML/service integration and durable startup recovery. Then build an isolated, read-only GitHub ProjectV2 adapter for verified remote identities, followed by conflict testing. Do not activate remote writes or migrate the user's task file without separately scoped operator approval.

## DECISIONS

No edits to `services/hub/ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`,
`widgets/TasksW.qml`, `shell.qml`, GitW, `GitHubProjectsService.qml`,
Proxy 2's PLANNER files, or local-machine data. GitHub is source of truth;
Hospital role registration, merge and deployment permissions are unchanged.
