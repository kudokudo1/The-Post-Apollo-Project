# 🏥💜 TASKS // M13y Post-Crash Read-Only Source Review

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS source integrity / opt-in encrypted draft recovery  
**STAFF ROLE //** DOC, external Hospital-compatible provider OPEN AI // CHATGPT; live Hospital registration not verified  
**BASELINE //** GitHub `main` `32c889a49203ee7c890e888bbcbd02b32735d670` (November 6, 2026)  
**ASSIGNMENT //** M13y classification of native-like save outcomes after process exit; test-only GitHub scope, no production integration or local workstation mutation.

## IMPLEMENTATION

M13x PR #1372 merged and Nurse 2 review passed. The accepted M12l single-writer ADR remains selected. The live TASKS store still writes `apollo-hub-todo-v1.json` through its sole Quickshell `FileView` under the desktop user's permissions. M13v already demonstrated durable *synthetic* SQLite stage receipts; M13w keeps the draft when those receipts match the source but lack a genuinely authenticated save acknowledgment.

The remaining practical problem: **after an interruption, the old process and its in-memory ticket are gone**. The saved JSON may still be at its previous bytes; it may contain the intended new bytes without a journal settlement; or the journal may say settled despite the UI never receiving a response. A fresh process must **inspect**, not re-run a mutation or invent a save confirmation.

This milestone adds `tests/tasks/fixtures/TaskPostCrashSourceReviewM13y.py`, an independently executable **read-only fixture inspector**. It reuses the M11g safe source-file reader and M12h/M10p private fixture path and schema. Unlike creating a fresh `DisposableStageReceipt` owner, it does **not construct `Authority`** or cause the M10p restart transition to write `RECOVERY_REVIEW` into the SQLite journal. Instead:

1. Require exact private synthetic `m11e-fileview-test/handoff-test.db` path, owner-private parent, safe regular journal file and existing lockfile; refuse links/missing storage.
2. Acquire a **nonblocking shared lock** on the existing cooperative test lockfile. If a live owner holds an exclusive lock, refuse observation rather than racing a known active writer.
3. Safely read the exact synthetic JSON source using M11g's `O_NOFOLLOW`, owner/mode/inode checks.
4. Open **SQLite `mode=ro`**, set `PRAGMA query_only=ON`, and inspect M10p authority and M12h receipt rows without writing SQL or changing process ownership. The SQLite WAL engine may internally create or update its `-shm` sidecar while opening a read-only WAL snapshot; **this is not a guarantee of zero filesystem metadata changes**, although the inspector never alters application journal rows or source bytes.
5. Verify receipt chain, permitted states, monotonic valid stage metadata, authority pending-stage consistency, expected/actual digests and current source bytes. Reread source during the SQLite snapshot and fail closed if it changes.
6. Return **classification only**, no JSON body, draft text, source digest, task name, stage ID, writer name, journal path, credential, grant or capability.

The relevant classifications are:

| Observation | Inspector result | Allowed action |
|---|---|---|
| No settled receipt | `NO_SETTLED_SOURCE_REVISION` | Retain draft; do not infer initial source ownership |
| Reserved, source remains at baseline | `RESERVED_SOURCE_STILL_AT_BASELINE` | Review; do **not** replay even if the source appears unchanged |
| Reserved, source matches expected new bytes | `RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED` | Review; no save ACK because journal did not settle |
| Settled journal and matching source, but no UI ACK | `SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED` | Review; no automatic draft deletion |
| Failed readback or mismatched source | `FAILED_STAGE_REQUIRES_REVIEW` or divergence code | Review; preserve last-confirmed state |
| Live owner, missing/symlink/unsafe storage, invalid journal | Refusal code | No access or mutation |

**All inspector results always contain `draftDisposition:KEEP_DRAFT`, `lastConfirmedDisplay:KEEP_LAST_CONFIRMED`, `savedAcknowledged:false`, `automaticReplayAuthorized:false`, `taskWriteAuthorized:false`, `clearDraftAuthorized:false` and `nextAction:OPERATOR_REVIEW_ONLY`.**

`tests/tasks/test_task_postcrash_source_review_m13y.py` uses real ephemeral SQLite and private JSON fixture files and launches a distinct interpreter to simulate the process dying with `os._exit(86)` at three post-reservation stages. The independent inspector must read the WAL-backed journal and classify the source **without opening a fresh writer**. It also tests clean close, cooperative lock refusal, failed readback, source rollback, missing file, unsafe symlink, deliberately inconsistent synthetic journal, wrong path, no inadvertent new writer and strict denial of authority. Existing M12h/M13u/M13v/M12i/M13w/M11d/C2a regressions run in GitHub CI.

This is an **actual saved-file and SQLite recovery inspection experiment**, not an authenticated Quickshell runtime test, genuine task journal migration, or a fix to the current UI's unprotected save acknowledgment behavior.

## HOW TO USE

No local Fedora command or desktop action required. GitHub Actions runs:

```sh
python3 -B -m unittest discover -s tests/tasks \
  -p 'test_task_postcrash_source_review_m13y.py' -v
```

The inspector itself accepts only a disposable fixture journal path:

```sh
python3 -B tests/tasks/fixtures/TaskPostCrashSourceReviewM13y.py \
  --db /ABSOLUTE/TEST-ROOT/m11e-fileview-test/handoff-test.db
```

Do not point it at a real TASKS source, another repository, the actual Quickshell data directory or any credential store. A running owner will be refused by the cooperative lock. This code never mounts in `shell.qml` or `ApolloHubTodoStore.qml`.

## VERIFY

- Live `ApolloHubTodoStore.qml` has exactly one `FileView` and one `todoFile.setText`; `ticketProducerEnabled`, `guardedWriterEnabled`, `encryptedRecoveryEnabled` and Connections `credentialActionsEnabled` all remain false.
- M12h journal settlement, M13u source revision evidence, M13v synthetic callback handshake and M13w four-consumer KEEP_DRAFT contract remain unchanged.
- Genuine independent child process death leaves durable reservation or settled receipt; a second process classifies without an M10p fresh-owner mutation, grant or data recovery.
- Every negative branch keeps last confirmed UI state and all production permission flags false.
- No source bodies, real tasks, hashes, paths, writer or stage identities are exposed in result frames.

## WATCH OUT FOR

This inspector does not seal the underlying hostile same-UID threat identified by M12k/M13x. The cooperative lock only excludes a cooperating owner. A malicious process with the user's permissions may change the test source or SQLite journal while it is being read or after the read. Read-only SQLite observation is not an independent trust root. A matching file hash does not establish callback origin, OS fsync ordering, app authenticity or operator consent.

The inspector does not clear a draft or reapply an uncertain mutation. A user may need a future explicit merge/reconciliation workflow if the source contains expected bytes but the UI acknowledgment was lost. Such a workflow needs a native, reviewed and authorized path to show differences and request approval without accidental duplication.

M13y does **not** implement encrypted drafts, native Quickshell lifecycle integration, first-create authorization, keyring unlock, authenticated Connections consent or cross-device sync.

## CHECKLIST

- [x] Reconcile M13x merged; check main, Syntagma protocol and TASKS ownership
- [x] Reuse existing M11g source reader / M12h SQLite journal without creating another owner or writer
- [x] Add read-only postcrash classifier with strict fixture-only path, safe lock and fail-closed states
- [x] Add independent process death scenarios and data-minimization tests
- [x] Add targeted GitHub CI and Hospital handoff
- [ ] PR-head green CI and independent review
- [ ] Operator PR merge and final acceptance
- [ ] Native Quickshell original FileView save/reload and ambiguous callback acceptance
- [ ] Real TASKS source revision and draft-preservation integration, authorized separately
- [ ] Authenticated shared Connections consent, key-release and encrypted draft lifecycle acceptance

## NEXT

Use M13y evidence to design the **operator-visible recovery review** for source-at-baseline, source-at-expected-but-unsettled and settled-but-UI-unacknowledged cases. Reuse existing M13a last-confirmed and M12o/M12p unsaved draft presentation. A separate approved native Quickshell test is required before any save ACK is real. Do not switch on protected writer, ticket producer or encrypted recovery flags based solely on synthetic CI.

## DECISIONS

The accepted local-first single-authority architecture stays in force. This milestone adds a disposable **read-only inspector**, not a daemon, storage migration or production acknowledgment. No local machine write, TASKS JSON access, separate UID migration, shared Connections modification, keyring, live Hospital registration, automatic replay, PR merge or operator acceptance.
