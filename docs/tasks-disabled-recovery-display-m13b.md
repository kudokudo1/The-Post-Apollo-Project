# 🏥💜 TASKS M13b // Disabled Read-Only Recovery Display Compatibility

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Integrate synthetic M13a fresh-owner recovery decisions with existing M12o/M12p four-consumer UI semantics without activating production recovery  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor, no verified live Hospital registration  
**BASELINE //** GitHub `main` `cf5f0fca7c2668a83583aa360d7e07421bf5ff90`, 2026-11-02  
**AUTHORITY //** Bounded repository-only continuation; no local machine mutation, production UI/writer change or merge authorization.

## IMPLEMENTATION

The operator confirmed continued TASKS work after M13a. [PR #1060](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1060) was verified merged into `main` at `00d4357a6817c21cd029edd6a9c184d5527c39f5`. The previous M12x operator test proved the existing legacy FileView saved and reloaded one synthetic task. **Neither result establishes an authenticated production recovery source or ticket.**

Current mechanisms inspected:

- `TaskRestartReviewM13a.cjs::reopen()`: pure synthetic fresh-owner restart inspection with prior stage/session/epoch, source classification, confirmed rows, and draft. Even a previously marked `SETTLED` candidate remains `RECOVERY_REVIEW` and nonwritable.
- `TaskSaveTicketContractM12o.js`: real future ticket policy for HUB, DETAILS, PLANNER and PROJECTS; a `REVIEW_REQUIRED` event retains the draft and is terminal. A `CONFIRMED` event in a test only clears when expected full snapshot and `SYNTHETIC_READBACK_RECEIPT` agree.
- `TaskHubTicketPresenterM12p.js`: Hub-specific future presenter, currently unmounted by `ApolloHubTodoMini.qml::ticketUiEnabled=false`. It returns `KEEP_DRAFT_FINAL` on `REVIEW_REQUIRED` and ignores stale/late terminal events.
- `ApolloHubTodoPolicy.js::view()`: the six public state names are `loading`, `saving`, `ready`, `empty`, `error`, `unsupported`. The current production error state deliberately hides rows; **M13b does not rewrite that policy or mount an alternative view**.

M13b adds a **pure, unmounted** `tests/tasks/fixtures/TaskRecoveryDisplayM13b.cjs::project()` function. It takes a validated *synthetic* M13a review, a M12o ticket, and an explicit fake `stageId/session/epoch/ticketId/surface/method` link. It refuses:

1. An unsafe/invalid review, prior/fresh owner identity inconsistency, or any authorization flag set true.
2. Tickets whose M12o baseline task/project rows or captured draft differ from the M13a last-confirmed review.
3. Foreign or mismatched stage/ticket association and unsupported UI surface or mutation route.
4. Malformed counts, incorrect Hub pending presenter state or any reducer that unexpectedly claims to clear a draft.

On a valid synthetic review, it creates a **separate read-only overlay** with the established view fields: `state:error`, `writable:false`, `error:RECOVERY_REVIEW`, total/remaining/completed, last-confirmed items and projects. The original M12o reducer processes `REVIEW_REQUIRED`. For Hub, M13b uses the existing M12p presenter's `advance()`; other three consumers use M12o directly. Every result remains `KEEP_DRAFT_FINAL`, `REVIEW_REQUIRED`, with the original draft preserved and all source/restore/replay/clear permissions false. A later `CONFIRMED` event cannot reverse terminal review in M12o.

The stage-ticket binding here is **an explicit, fake test link**, not verified OS provenance. It proves that the proposed presentation **refuses an inconsistent linkage** but cannot prove a caller cannot forge a consistent tuple. Real source authority, durable journal, UI draft storage policy, and executable trust remain separate before any production use.

## HOW TO USE

**No desktop action or live UI change.** This is a GitHub CI test only:

```sh
node --test tests/tasks/test_task_recovery_display_m13b.cjs
```

The test creates no real task files, does not run Quickshell, and does not persist any user drafts. The test fabricates v3 task documents and uses the actual pure TASKS policy and existing M12o/M12p JS reducers in an isolated Node VM. All source/doc changes are restricted to new test-only files.

## VERIFY

M13b tests all four supported UI surfaces across prior `RESERVED` and `SETTLED`; missing, unconfirmed, changed or existing source classifications; exact last-confirmed row counts; draft preservation; and late/conflicting events. Negative cases include foreign tickets, incorrect stage/owner association, mismatched baseline, changed draft, malformed view and unexpected writable status. CI also reruns M13a independent-process, M12o ticket, M12p Hub, M12a memory-only recovery and M11d one-authoritative-writer source guards.

**Known proof boundaries:**

- M13b is **not** a native QML panel, production UI integration, replay engine, authenticated journal, independent source verifier, or user-visible feature.
- M13a's fixture is caller-provided synthetic evidence. No real user draft is stored by M13b.
- M12o's synthetic `CONFIRMED` is not an OS save certificate. No process or source authority is granted by this adapter.
- This may be used as a compatibility and acceptance contract when a separately authorized, real recovery presentation is designed.

## WATCH OUT FOR

The production `TodoPolicy.view(error)` currently hides rows; M13b builds an **isolated** display for prospective recovery semantics. Do not copy an untrusted checkpoint's rows into a real UI as confirmed truth without independently verifying the backup/source and ownership chain. Do not derive real ticket IDs from guessable stage IDs. No automatic clearing, recovery writes, retries or installs.

## CHECKLIST

- [x] Verify M13a PR #1060 merged; Syntagma and ownership current
- [x] Inspect existing M12a/M12o/M12p policies and live four-consumer sources
- [x] Add unmounted read-only recovery display composition and explicit fake linkage
- [x] Test last-confirmed rows and all four consumers' drafts on owner restart
- [x] Test terminal review against late receipt and reject foreign/mismatched ticket
- [x] Maintain one FileView and all production disabled flags
- [ ] GitHub CI and independent review
- [ ] Operator review/merge
- [ ] Separate authorized real persistent stage/snapshot identity and UI wiring

## NEXT

Once reviewed, the next bounded contract should address **trustworthy, versioned recovery evidence and draft retention/expiration** for a single application coordinator. Before touching actual TASKS UI, decide whether drafts persist beyond process death, where they are stored, retention/deletion permissions, and how a real source/backup/owner identity is independently established. Do not enable `ticketProducerEnabled` or claim M13b protects real task data.

## DECISIONS

M13b is **compatibility testing only**. Production source, task data, old legacy methods, six-state policy, error-state display, ticket/UI flags, Quickshell session, and operator local worktree all remain unchanged. No verified Hospital registration, PR merge, activation, migration or user acceptance claimed.
