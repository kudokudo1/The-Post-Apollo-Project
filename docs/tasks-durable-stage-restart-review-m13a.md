# 🏥💜 TASKS M13a // Fresh-Owner Stage Identity and Last-Confirmed UI Recovery

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Cross-process, synthetic stage identity and read-only UI/draft handoff after a lost acknowledgment  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible; **not** registered with live Hospital  
**GITHUB BASE //** `5b02eb1fea1155861c9da0503ad7c447ce6bf380` (2026-11-02)  
**SCOPE //** GitHub-only pure fixture, fake checkpoint files and tests; no production writer, Quickshell runtime, local machine changes or activation

## IMPLEMENTATION

### Recovered previous decisions and concrete sources

- **M12x** passed the operator's real-Quickshell native smoke on a new disposable copy: `INITIAL_EMPTY`, `TICKET_DISABLED`, `NATIVE_SAVE`, `NATIVE_RELOAD` and `NATIVE_AND_DISK_AGREE`. That is **legacy** FileView evidence, not native ticket authentication.
- **M12y PR #1046** merged; missing-source review never grants write authority without independent first-install provenance.
- **M12z PR #1049** merged at `babb7851331b970b83817cbdf94ac906fda9f501`; test-only Linux O_EXCL no-clobber and lost acknowledgment are covered. No real first-create authority exists.
- **Existing M12a model** already keeps last-confirmed rows when a simulated host exits during `RESERVING` or `RESERVED`; M12o contracts cover **all four UI consumers** and retain drafts until receipt and snapshot agree; M12p is an inert Hub presenter. M13a does not replace those.
- **Existing production store** `services/hub/ApolloHubTodoStore.qml` remains one FileView, one `setText`, nine synchronous legacy methods, `ticketProducerEnabled:false`, `guardedWriterEnabled:false` and `independentlyAuthenticatedTicketReceipt:false`.

### What M13a adds

M12a is memory-only; when a process ends its model is gone. M13a demonstrates a **test-only process handoff**:

1. Build a fake stage record containing session ID, owner epoch, generation, stage sequence/ID, `RESERVED` or `SETTLED` classification, **last-confirmed v3 JSON**, candidate v3 JSON, exact SHA-256 hashes and a UI draft scoped to one of HUB/DETAILS/PLANNER/PROJECTS.
2. Persist that record using `O_CREAT|O_EXCL|O_NOFOLLOW`, fsync the file and its private parent directory **inside an explicitly synthetic CI fixture only**. Duplicate record creation fails with `EEXIST`.
3. Independently start a **new Node process** that rereads the checkpoint and current synthetic source, loads the **actual TASKS v3 policy**, and evaluates a fresh owner epoch/session.
4. The review classifies source as `SOURCE_AT_LAST_CONFIRMED`, `SOURCE_AT_CANDIDATE`, `SOURCE_MISSING` or `SOURCE_MISMATCH`; **every** fresh-owner case enters `RECOVERY_REVIEW`, shows old confirmed items and the uncommitted draft, and sets `writable:false`, `replayAuthorized:false`, `clearDraftAuthorized:false`, `restoreAuthorized:false`.
5. A fake `SETTLED` marker plus exact candidate bytes never automatically promotes those bytes to confirmed UI state after process death. Review is required because this checkpoint is **not an independently trusted durable journal or authenticated saved callback**.
6. Reject stale/same-owner identity, incorrect epoch, corrupted baseline/candidate hashes, foreign stage IDs, unsupported phase or document, malformed draft and unknown record fields. Never retry or repair a source automatically.

The reusable `tests/tasks/fixtures/TaskRestartReviewM13a.cjs` is **pure**. It does not contain filesystem APIs, processes, credentials, path traversal, host calls or actual TASKS I/O. The file creation, fsync and subprocess exist **only in** `tests/tasks/test_task_restart_review_m13a.cjs`, which uses disposable `mkdtemp` paths under the GitHub runner.

## HOW TO USE

There is no desktop control and no reason for an operator to rerun a native smoke. GitHub CI executes:

```bash
node --test tests/tasks/test_task_restart_review_m13a.cjs
```

The test writes only synthesized M13a strings to a temporary CI directory and starts a throwaway Node child to prove a **fresh-process** review. No real data is read, no local Quickshell is restarted, and no system setting or production file is modified.

## VERIFY

Expected regressions on the PR:
- M13a fresh-process synthetic `RESERVED` before-write, after-write, missing, foreign-source; fake `SETTLED` before/after source; all protect the same last-confirmed row and draft.
- Duplicate exclusive checkpoint attempt fails; stage ID across restart is unchanged.
- All four UI surface drafts survive a failed/restarted save.
- Tampered record, old/same owner and missing draft fail closed.
- M12a guarded completion, M12o four-consumer ticket semantics, M12p Hub presenter, M12y absence triage, M12z first-create and M11d one-writer inventory remain green.
- Native M12x checkpoint already observed; **M13a does not exercise native FileView**. CI fsync is not evidence of physical power-loss survival or cross-resource atomicity.

## WATCH OUT FOR

- **Synthetic durability only.** These bytes are written to CI test files, not the real TASKS storage. A checkpoint's `SETTLED` field is caller-authored fake data, not proof of an OS settlement or authenticated stage. `M13a` cannot provide production restart safety, actual stage ownership, anti-tamper protection, or hostile same-UID fencing.
- The fixture retains a copy of last-confirmed task bytes and an uncommitted UI draft in **plaintext synthetic files** to test whether a future coordinator could display them. A production design must separately determine if/how sensitive real drafts should be persisted, encrypted, retained and discarded, and who may see them; M13a never opts the user into persistent draft logging.
- Stage IDs are structurally scoped to session and owner epoch. This does not make them unforgeable or create a durable generation counter in a live app.
- A settled-but-unacknowledged operation is not equivalent to a failed operation; a fresh process must inspect source and journal evidence before operator recovery. Never auto-replay or overwrite.
- `TodoPolicy.view()` currently hides rows during production error. The M13a display is an isolated *proposed read-only overlay*, not a changed production UI. The four existing consumers remain on their legacy paths.

## CHECKLIST

- [x] Recheck current GitHub, M12z merge and Syntagma authority
- [x] Inspect M12a, M12o, M12p and current single writer before design
- [x] Add fake stage/session/epoch identity and last-confirmed/draft checkpoint
- [x] Add actual temporary-file sync and independent process reload tests
- [x] Fail closed on cross-session stale identity, ambiguous source and false settlement
- [ ] PR CI complete, independent review
- [ ] Operator approval / merge
- [ ] Actual protected persistent owner epoch and source provenance design
- [ ] Actual four-consumer UI recovery wiring, native acceptance and explicit operator activation

## NEXT

After review/merge, the next useful step is a **disabled one-coordinator recovery display contract** that reuses M12o and M12p's draft retention with real snapshot shapes, subject to actual source/backup and epoch owner verification. Do not wire it into live TASKS or enable producer flags without separately passing real-source, native stage-attribution and UI permission gates.

## DECISIONS

**Implemented:** test-only cross-process synthetic checkpoint and read-only review; one writer remains unchanged.  
**Not verified:** actual crash durability, real task-data recovery, authenticated OS journals, native guarded ticket callbacks or production UI draft persistence.  
**Not authorized:** local source pulls/resets, real TASKS inspection/migration, production ticket activation, new permanent service, privileged broker, automatic restore, merge or final user acceptance.
