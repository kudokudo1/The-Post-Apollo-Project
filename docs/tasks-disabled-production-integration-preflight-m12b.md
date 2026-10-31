# 🏥💜 TASKS M12b // Disabled Production Integration Preflight

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Production-shaped trust/source/host/UI preflight review, no live integration  
**DOCTOR //** External ChatGPT worker; not registered in live Hospital  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED BASE //** GitHub `main` `b81c52d7e30a2ab9a3c03ce621cdff2d52838814` (2026-10-31). Recheck before implementing any later milestone.  
**CLASSIFICATION //** **PROPOSED, DISABLED-ONLY ARCHITECTURE CONTRACT**. Not a production executable, launch or activation.

## IMPLEMENTATION

M11x defined the broad production architecture; M11y tested signed *synthetic* release verification against caller-provided key/fingerprint/generation; M11z tested *synthetic* source backup and code-marker rollback; M12a tested a pure queued → reserved → settled UI model. None provides a live, independently trusted executable, an authorized real-source preflight, a durable OS owner linked to FileView, or verified native stage provenance. Treat these as useful independent mechanisms, not interchangeable approval credentials.

M12b creates a **machine-readable production integration evidence inventory** and a read-only source audit. Its `tests/tasks/fixtures/task_disabled_integration_preflight_m12b.json` is an evidence checklist, not an installable configuration. The `tests/tasks/test_task_disabled_integration_preflight_m12b.py` checks source invariants and deliberately refuses to mark any real production gate passed.

### Actual production baseline

- Only `services/hub/ApolloHubTodoStore.qml` owns the live TASKS JSON writer. `FileView` is exactly one. Nine public mutation routes converge on `stage(result)`. The guarded-mode switch remains **literal `readonly property bool guardedWriterEnabled: false`**.
- Its `stage(result)` currently returns a synchronous Boolean. `true` means legacy `todoFile.setText` was called, **not** durable settlement. Its `onSaved` currently publishes `pendingDocument` before any independent host readback. The earlier tests do not change this.
- The current source identity is `Quickshell.dataDir + "/apollo-hub-todo-v1.json"`; **M12b never reads it**. Do not accept a guessed source path, an attacker-supplied path, or a self-reported process environment as source authorization.
- M11l remains restricted to `m11l-tasks-copy/todo-copy.json` and M11z to `m11z-synthetic-copy`. **Do not widen these test-only restrictions**.
- The existing `TodoPolicy.view()` hides previously confirmed task rows in the public error view. M12a's read-only last-confirmed overlay is still *synthetic* and not mounted. A real review state must retain confirmed rows and drafts without accidentally making an empty list writable.

### Ten evidence topics; all OPEN

M12b splits M11t's nine broad production gates into ten narrower *review topics*, **not** newly satisfied gates:

| Evidence topic | Minimum production evidence required |
| --- | --- |
| `RELEASE_TRUST` | Independently maintained approved signing root, interpreter/module provenance and rollback-resistant generation |
| `OS_HOST_OWNER` | Authenticated executable/process, durable owner epoch/session, lifetime lock and non-replayable host protocol |
| `REAL_SOURCE_AUTHORIZATION` | Explicit operator permission to inspect exact real file, path/inode/schema validation; missing source cannot be treated as writable empty data |
| `INDEPENDENT_BACKUP` | Exact authenticated source baseline and independently rereadable, retained backup; external edits refused |
| `NATIVE_STAGE_ATTRIBUTION` | Durable stage reservation before the **sole FileView write**, callback ambiguity denial, OS readback and settlement |
| `ASYNC_UI_ACCEPTANCE` | Selected async API and all four caller reconciliation tests; last-confirmed readonly overlay, retained drafts |
| `RESTART_AND_FREEZE` | Native fault stages, new-owner `RECOVERY_REVIEW` and no replay of settled-but-unacknowledged stages |
| `CODE_ONLY_ROLLBACK` | Actual writer quiescence, verified code rollback, preservation of live JSON, journal and backups, separate data-restoration consent |
| `NATIVE_RUNTIME_ACCEPTANCE` | Separately authorized isolated native acceptance with redacted repeatable evidence |
| `ACTIVATION_DECISION` | Final separate operator approval after every previous independent gate |

All ten remain **OPEN** even after the M12b GitHub job passes. M11t's original **nine production gates likewise remain OPEN**.

### Required integration ordering

The future, separately authorized host/store patch must observe this sequence:

`TRUSTED_RELEASE → AUTHENTICATED_OS_HOST → EXACT_SOURCE_PERMISSION → SOURCE_AND_SCHEMA_PREFLIGHT → BYTE_EXACT_BACKUP_READBACK → JOURNAL_OWNER_ATTACH → CANDIDATE_VALIDATE → DURABLE_STAGE_RESERVE → SINGLE_FILEVIEW_WRITE → NATIVE_DEFERRED_READBACK → DURABLE_OS_SETTLE → CONFIRMED_UI_PUBLISH`.

Freeze/review and code-only rollback must be separately handled. No second JSON or SQLite task-data writer may be introduced. A callback such as `onSaved` is a notification, **not** the stage ID and not a commit certificate. The later implementation must prove callback attribution, fence generation/epoch/path and fail closed when callbacks are duplicated/reordered or host evidence is lost.

### Decisions needed before an executable integration patch

1. **Trust-root owner and release policy.** Decide who owns the independently distributed signing/verifying root, protects rollback-resistant generation state, and authorizes host/interpreter versions. M11y test keys and local CI self-hashes are not credentials.
2. **Source permission boundary.** Record an explicit real-file inspection scope and explain how it is separated from release verification. An external host must never be permitted to scan arbitrary home files.
3. **Async mutation semantics.** M11x Option A preserves existing public Booleans but means **queued only**, never saved; Option B uses structured request tickets and explicit completion. Neither is canonical. The four mutation UI callers and read-only TODAY/Planner/Hub views must be reviewed together.
4. **Last-confirmed and recovery display.** Decide how an error/review can preserve confirmed data and drafts while remaining nonwritable within the existing six public state names.
5. **Actual callback and recovery evidence.** Choose how a real native `FileView` readback gets tied to the right durable stage without timing-based guesses, with fresh-owner `RECOVERY_REVIEW` on ambiguous restart.
6. **Rollback authority.** A code-only rollback must preserve task source, backup, journal and any independently observed newer data; restoring task data needs a **different, explicit** operator decision.

### Future work ordering, proposals only

- **M12c // Independent trust-root ownership decision:** Authority/threat model and authenticated release provenance, no activation.
- **M12d // Synthetic production-shaped host/source boundary:** A separate new host, still explicitly denied access to live TASKS data; do not modify the M11l/M11m disposable source permissions.
- **M12e // Disabled-only QML integration proposal:** After decisions and isolated native proof, a separately approved patch to the sole writer, with no default activation.

These are **proposals, not created Hospital assignments**. No production integration may be inferred from this draft or its CI status.

## HOW TO USE

There is no new Post-Apollo control, runtime service, test-harness activation button or desktop command. Read the manifest and design in the GitHub PR. The read-only source check runs automatically through CI, or in a separate checkout:

```sh
python3 tests/tasks/test_task_disabled_integration_preflight_m12b.py
```

It reads repository text only. It does **not** access the real JSON file, SQLite journal, backup directory, Quickshell runtime, user local checkout or live Hospital record.

## VERIFY

- At initial review, current GitHub `main` is `b81c52d7e30a2ab9a3c03ce621cdff2d52838814`, M12a merged, no competing open TASKS PR or M12b branch found.
- M12b changes only a new JSON evidence fixture, a read-only Python contract test, this documentation and a GitHub Actions workflow; production QML, shared policy, UI callers, M11l/M11m and shell remain unchanged.
- CI runs the M12b source guard and previous M12a/M11z/M11y/M11x/M11t/M11d checks. Success means **source consistency**, not authenticated production safety, native callback proof, local installation, or user acceptance.

## WATCH OUT FOR

- `testTrustCheck:true`, `testBackupReadback:true`, `journalSettled:true`, a nonce, a `pidfd`, and a passed GitHub check are not independent production security evidence. The future trust inputs need independently controlled provenance.
- `FileView.onSaved` lacks durable stage identity. The real QML code still promotes pending data immediately and `TodoPolicy.view()` still hides error-state rows; **M12b does not fix either**.
- Missing/damaged source must never become a writable blank task list in guarded mode. Current legacy missing-file behavior must be reviewed before enabling a host.
- Advisory `flock` cannot force unrelated processes to honor the lock. Production external edits need conflict detection, source reread and safe review.
- There is no verified live Hospital assignment or role registration. Current GitHub state is not evidence that a local modified worktree is synchronized.

## CHECKLIST

- [x] Read current GitHub repository, Syntagma entry rules and relevant OPERATE guidance
- [x] Verify M12a merge, inspect production single-writer seam, check competing work
- [x] Specify explicit real-source authority, release trust, backup, stage, UI and rollback evidence
- [x] Preserve pending M11x UI choices and all nine M11t production gates
- [x] Add machine-readable disabled-only acceptance record and source CI
- [ ] Verify CI and independent review
- [ ] Operator review and merge
- [ ] Separately authorize any production host source, real-file access, QML change, local test or activation

## NEXT

Review M12b CI. Before a real host implementation, choose and document who owns the trusted release credentials and the exact async public mutation API. A following **separately scoped** synthetic host/provenance test can then be built without expanding the existing disposable harness privileges.

## DECISIONS

**Verified:** M12a is merged; one live JSON FileView remains; guarded writer still hard-coded false; existing async production host is not connected.

**Proposed, OPEN:** Independent trust anchor, actual source authority, host process/owner binding, callback attribution, async API, last-confirmed view, rollback and activation design.

**Not authorized:** Real task-file access, production host integration, shared singleton or UI mutations, local Fedora changes, Quickshell restart, signing key installation, SQLite task migration, data recovery, PR merge, or live Hospital registration.
