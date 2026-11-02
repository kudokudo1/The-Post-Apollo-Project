# 🏥💜 TASKS M12m // Isolated Local Ticket Coordinator

> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
> **ROOM //** TASKS JSON writer continuity  
> **ASSIGNMENT //** Implement M12l Phase 1 + isolated portion of Phase 2: explicit local completion tickets and serialized disposable JSON writes  
> **DOCTOR //** External Hospital-compatible ChatGPT worker; **not** registered in live Hospital  
> **PROVIDER //** OPEN AI // CHATGPT  
> **INSPECTED GITHUB MAIN //** `86403682853b501a7493920e2606c6bde958de6d`, November 2, 2026; recheck later  
> **CLASSIFICATION //** ISOLATED TEST MODEL, **NOT** PRODUCTION TASKS INTEGRATION OR TRUSTED HOST  
> **AUTHORITY //** Operator approved the immediately preceding bounded Phase 1 + isolated Phase 2 assignment. No local machine writes or production activation were approved.

## IMPLEMENTATION

### Existing production boundary (left untouched)

`services/hub/ApolloHubTodoStore.qml` is the current singleton owner of the `apollo-hub-todo-v1.json` source, with exactly one Quickshell `FileView`, nine `stage(TodoPolicy.*)` mutation entrypoints, and the hard-disabled flag `guardedWriterEnabled: false`. `services/hub/ApolloHubTodoPolicy.js` contains the real v1/v2-compatible v3 task/project schema and mutation policy.

This M12m patch **adds no second live writer** and does not change `shell.qml`, widgets, QML, existing source files, M12b preflight gates or the M12l architecture ADR.

### New isolated test-only components

1. `tests/tasks/fixtures/TaskLocalTicketCoordinatorM12m.cjs` is a pure asynchronous ticket/coordinator model. It accepts an explicitly injected storage interface and policy, not a real TASKS path. It maintains last-confirmed document and exact serialized bytes, admits FIFO mutations, validates candidates, serializes writes and independently reads back the returned source before emitting `CONFIRMED`.
2. `tests/tasks/fixtures/TaskPrivateFixtureAdapterM12m.cjs` is a constrained **real filesystem** adapter for **only** `/tmp/m12m-*/m11e-fileview-test/fixture-only.json`, with private directory/source permissions and no symlink acceptance. It uses a private temporary file, file `fsync`, rename, parent-directory `fsync`, bounded stable reads, and a baseline recheck. It does **not** touch the historical M12j fixture or the current live TASKS path.
3. `tests/tasks/test_task_local_coordinator_m12m.cjs` uses the **actual production `ApolloHubTodoPolicy.js`** in a Node VM for validation and task creation, but never loads QML or the live singleton. Tests exercise real disposable JSON writes, pending tickets, FIFO serialization, policy refusals, external edit detection, uncertain commits, missing or unsupported data refusal, readback mismatch, restart inspection, observer isolation and unchanged production boundaries.
4. Scoped GitHub Actions tests run on disposable test files only.

### Ticket state and meaning

```text
attach existing valid fixture
  -> READY
submit mutation
  -> QUEUED (ticket given to caller immediately)
  -> PREPARING (policy validation)
       -> REJECTED (invalid; no write, other valid requests continue)
  -> WRITING (check baseline, replace disposable file atomically)
  -> VERIFYING (independent stable readback against expected bytes)
       -> CONFIRMED (exact readback + validated document)
       -> REVIEW_REQUIRED (uncertain commit / unexpected bytes)
            -> block subsequent queued and new work, retain last confirmed
               plus last attempted draft, do not retry automatically
```

A ticket result is `{ticketId, state, reason}`. The ticket is **session-local** and not a durable cross-process idempotency key. `CONFIRMED` means the disposable file adapter returned and the coordinator independently reread the exact expected content. It does **not** mean native Quickshell `FileView` callback attribution, authenticated writer origin, a production durability certificate, a remote GitHub push or a durable user-visible acknowledgment across a crash.

`attach()` never creates missing or malformed files. On a bad source it enters `RECOVERY_REVIEW` and refuses writes. If a crash occurs after rename but before the coordinator observes completion, the original session's ticket is **unknown/review required**, while a fresh instance may read and present the current file for inspection. It must **not** infer completion of the lost ticket or auto-replay it.

### Internal API in this model

```js
const core = new LocalTicketCoordinatorM12m({
    store: explicitlyConstructedPrivateFixtureAdapter,
    policy: currentTaskPolicy,
    onStatus: status => { /* UI observes, never certifies persistence */ }
});
await core.attach();    // Existing validated fixture only.
const {ticketId, completion} = core.submit(
    current => currentTaskPolicy.create(current, "Synthetic", 1000)
);
const final = await completion; // CONFIRMED / REJECTED / REVIEW_REQUIRED / BLOCKED
const view = core.snapshot();   // Defensive copy; lastConfirmed + lastDraft
```

The public TASKS API and all four consumer UIs are **not yet changed**. The `onStatus` callback cannot approve a write and exceptions in the observer are ignored so they do not corrupt the persistence result.

## HOW TO USE

**GitHub only, no operator local setup:**

```sh
node --test tests/tasks/test_task_local_coordinator_m12m.cjs
```

The test suite automatically creates and cleans new owner-private `/tmp/m12m-*/m11e-fileview-test/fixture-only.json` files on the CI runner. It does not start Quickshell, run a live host, use GitHub credentials or read real tasks.

## VERIFY

The M12m suite must prove:
- A ticket ID exists before the asynchronous write and a task is confirmed only after full expected readback.
- Two queued mutations change the one confirmed document **in order**, with no second concurrent writer.
- A second ticket arriving during an in-flight write stays queued and does not write concurrently.
- Bad model changes refuse without rewriting; a later good change can proceed.
- Invalid/missing source never silently becomes an empty document.
- External baseline change, mismatched readback or uncertain post-rename reply causes `RECOVERY_REVIEW`, preserves confirmed content plus draft, blocks new/queued requests and does not retry.
- Fresh-instance inspection of a changed file does **not** retroactively certify the previous ticket.
- Writable snapshot objects and UI observer exceptions cannot change the internal confirmed data or override the result.
- Production singleton still has exactly one FileView and `guardedWriterEnabled: false`; QML never imports these fixtures.

**CI passing proves the model under a real disposable Linux filesystem. It does not prove any production native FileView event sequence or persistence under abrupt power failure.**

## WATCH OUT FOR

- The model does not implement production `stage(result)` replacement or an OS-trusted host. Integrating it into the real app requires a separate reviewed implementation, explicit API compatibility and four caller reconciliations.
- No durable intent journal exists for this M12m model. A crash after the filesystem rename and before publication remains ambiguous and must be inspected; **never auto-replay**.
- Advisory baseline checks, atomic rename, fsync and exact digest/byte comparison cannot fence malicious same-UID writers or prove who wrote the content. See [M12k external writer tests](../../tests/tasks/test_task_uncooperative_writer_m12k.py).
- `fsync` semantics depend on filesystem/storage and do not justify claiming power-loss durability for Quickshell. The test's ordinary atomic-path checks are not crash injection at the native `FileView` boundary.
- Status IDs are not selected production QML API names; future durable stage IDs must be collision-safe across processes.
- The archived M11t nine requirements and M12b ten preflight evidence gates remain **OPEN**. M12l's accepted architecture direction does not bypass an unreconciled old requirement.
- Last-confirmed data plus draft are separate from planned GitHub sync state. No data is uploaded, migrated or backed up here.

## CHECKLIST

- [x] Verify latest GitHub/ownership and M12l decision
- [x] Keep production singleton, one FileView, current guard, real user data untouched
- [x] Define ticket acknowledgment semantics and fail-closed transitions
- [x] Add isolated FIFO coordinator using actual task policy
- [x] Add private real-filesystem fixture adapter
- [x] Test failure/restart/queue/observer cases and production source invariants
- [ ] Verify GitHub CI and scoped diff
- [ ] Operator review and merge
- [ ] Future approved disabled-only QML adapter with four caller reconciliation tests
- [ ] Operator-approved real-source backup, native verification, and activation
- [ ] Separately design offline GitHub/other-format synchronization

## NEXT

After the M12m suite is reviewed and merged, define a **disabled-only TASKS public API integration contract** and an isolated native test that verifies acknowledgment timing with one real Quickshell FileView. Choose an implementation that does not introduce a second authoritative writer. Do not start on a live task source without separate permission and backups.

## DECISIONS

**Chosen for this patch:** Session-local tickets; one serialized mutation pipeline; exact-readback acknowledgment only in a disposable test; fail closed and retain draft on uncertain results; no automatic retry.

**Not chosen:** New privileged broker, storage migration, production source path, persistent ticket journal, real API/UI changes, GitHub adapter, activation or old security gate waivers.

**Acceptance classification:** Test-model implementation awaiting independent CI and operator merge/review. No live Hospital registration was verified.
