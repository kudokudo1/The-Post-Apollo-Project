# 🏥💜 TASKS M13d // Explicit Operator Draft Choices Without Actuation

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Keep/export/delete *choice contract* after M13c recovery evidence review; no real draft storage or deletion  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible, not verified live registered  
**GITHUB BASE //** `8ab1b0331de9f57db3d17e75c02070c155661605` (Nov 3, 2026)  
**PERMISSIONS //** Repository-only tests/CI/docs. No local machine mutation, live Quickshell control, production file I/O, PR merge or activation.

## IMPLEMENTATION

### Verified prior checkpoint

- [M13c PR #1076](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1076) **merged** on November 2, 2026 at `1b0b80f9757a0a8eda28c284ee9c74d94b6b9262`.
- M13c's `TaskRecoveryEvidenceM13c.cjs::evaluate` checks caller-supplied separately pinned synthetic source/checkpoint evidence, then classifies draft review age `REVIEW_RECENT`, `REVIEW_OVERDUE`, or `CLOCK_UNCERTAIN`. It always preserves drafts and retains `sourceTrusted:false`.
- M13b's unmounted overlay composes four consumer surfaces with actual M12o/M12p ticket semantics. M13a retains last-confirmed task view over process restart, using a fake checkpoint and no source authority. All remain synthetic-only.
- `ApolloHubTodoStore.qml` remains the sole production FileView writer with literal `guardedWriterEnabled:false`, `ticketProducerEnabled:false`, and `independentlyAuthenticatedTicketReceipt:false`. No competing TASKS PR was open at preflight.

### M13d scope

Add the **pure, unmounted** `TaskOperatorDraftChoiceM13d.cjs`. It receives only an M13c-style read-only synthetic recovery result and explicit **fake** operator-choice envelope. It never opens or creates files and offers no real UI controls, cleanup, expiry, export, delete or stage replay.

- `select({review,choice})`: refuse unverified recovery state, inconsistent stage ID, unrecognized choice, changed pinned review digest, stale/faulty gesture or malformed timestamp. `KEEP` yields `KEEP_NOTED_FOR_REVIEW`. `EXPORT` yields `EXPORT_HANDOFF_REVIEW_REQUIRED`. `DELETE` yields `DELETE_SECOND_CONFIRMATION_REQUIRED`. Every result has `draftDisposition:"KEEP_DRAFT"`.
- The choice envelope is `M13D_FAKE_OPERATOR_CHOICE`. It includes the stage ID, test gesture ID, captured digest of the synthetic recovery review, requested action, and caller-provided selected-at time. These are correlators and **not proof of actual operator identity or consent**. Selection produces a metadata-only proposal and intentionally **does not duplicate the draft contents in a new decision journal**.
- `confirm({review,proposal,confirmation})` requires an explicit independent fake second gesture for EXPORT or DELETE, bound to decision ID, stage, exact action, non-reused gesture ID, `DRAFT_ONLY` scope, and an acknowledged uncertain save. It rejects a changed review, forged decision ID, ambiguous whole-database scope, missing second gesture or stale stage. KEEP needs no confirmation.
- Even an accepted fake second gesture returns `EXPORT_AWAITING_EXTERNAL_TARGET` or `DELETE_AWAITING_EXTERNAL_AUTHORIZATION`. This **does not identify a real export target, obtain real deletion permission, or execute a delete**. It is not a durable user preference or persistent idempotency record.
- Every output has `writeAuthorized:false`, `replayAuthorized:false`, `restoreAuthorized:false`, `clearDraftAuthorized:false`, `deleteDraftAuthorized:false`, `exportAuthorized:false`, `productionActivation:false`, `sourceTrusted:false`. A repeated choice or confirmation cannot actuate any operation.

### Architectural boundary

A **choice**, a **second gesture**, an **external authorization**, a **real readback/owner verification**, and an **executed filesystem operation** are different things. M13d models only the first two as fake test data. The actual operator would retain final authority when a future UI and permission design are proposed and separately accepted.

## HOW TO USE

No desktop steps or new controls. CI runs:

```sh
node --test tests/tasks/test_task_operator_draft_choice_m13d.cjs
```

The test uses synthetic v3 data through the existing M13a/M13b/M13c contract chain and M12o/M12p reducers. **This command is a developer test**, not a user command for deleting drafts. The M13d helper does not make writes or spawn processes.

## VERIFY

Test `KEEP`, `EXPORT`, `DELETE` for HUB, DETAILS, PLANNER and PROJECTS; verify the records contain no duplicated draft/snapshot; require separate confirmation gesture, correct stage/decision/action and `DRAFT_ONLY` scope; reject changed hash or stage, invented real authorization, malformed choices, and unclear source state. For `REVIEW_OVERDUE` and `CLOCK_UNCERTAIN`, retention and no-actuation remain unchanged. Rerun M13c/M13b/M13a/M12o/M12p and M11d one-writer protections in CI.

The test's fake gesture tokens are **syntactic validations only**, not proof that the real operator clicked a control. The deterministic decision digest cannot prevent replay without trusted persisted state, and no such state is created by this work.

## WATCH OUT FOR

- A draft may contain personal, confidential, or operationally sensitive content. M13d does **not** persist or export any real drafts. A production feature requires explicit privacy, encryption/permissions, ownership and retention design.
- These routines do not delete drafts, tasks, JSON source files, backup history, checkpoints, or test evidence. Even an old or twice-confirmed draft is retained for review. **No automatic expiration policy has been selected**.
- A choice cannot confer source authority. The actual source, last-confirmed record, backup, stage owner, and authenticated completion evidence still need separate verification.
- `TodoPolicy.view(error)` still hides rows in the real UI. The M13b recovery overlay has not been mounted in production.
- No command to manipulate `~/.config/quickshell`, live To-Do storage, or Quickshell processes is part of this milestone.

## CHECKLIST

- [x] Recheck M13c merged, Syntagma authority, current GitHub `main`, TASKS ownership
- [x] Build pure synthetic selection and second-gesture model
- [x] Bind choices to the same synthetic stage/review digest and `DRAFT_ONLY` scope
- [x] Ensure metadata-only proposal and no actual export/delete authority
- [x] Add four-consumer and negative-path tests; scope CI to existing guards
- [ ] CI, independent source review
- [ ] Operator review/merge
- [ ] Operator decides real draft persistence, privacy, export format/target permissions and deletion semantics
- [ ] Real source/owner provenance and eventual native UI acceptance

## NEXT

After M13d review/merge, prepare an **explicit decision dossier** for operator approval on real draft persistence, visibility, export format/target and deletion scope/retention. Do not implement live deletion or permanent draft logging before those choices are made. Separately close real-source/epoch authentication and native ticket admission gates for the M12l single logical coordinator.

## DECISIONS

**Implemented:** synthetic-only selection and second-gesture review; all real permissions remain denied.  
**Still undecided:** whether user drafts persist across crashes, how long, whether encrypted at rest, export targets, deletion and undo model, authority to erase.  
**Not authorized:** production writes, task deletion, backup modification, live UI activation, service/broker installation, local Git mutation, automated expiry, Hospital registration, PR merge, or final acceptance.
