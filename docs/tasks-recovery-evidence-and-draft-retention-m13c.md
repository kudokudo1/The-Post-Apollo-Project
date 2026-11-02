# 🏥💜 TASKS M13c // Separately Pinned Synthetic Recovery Evidence and Draft Review Age

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Compare synthetic restart evidence against a separately supplied baseline and specify nondeleting draft-review age behavior  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible; no verified live Hospital registration  
**BASELINE //** GitHub `main` `31eba0fd86fd19a830a2ccdccd75e77c309abb2b`, November 2, 2026  
**PERMISSIONS //** Repository-only new test/doc/CI files. No local workstation mutation, production recovery, real task-data inspection, UI activation or PR merging.

## IMPLEMENTATION

### Verified prerequisites

- [PR #1071](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1071) M13b was merged at `1f671cc3c43be8bd1555c50cd8f2da8153c7e15e`, after an initial cross-realm JavaScript test assertion was corrected. Its final two workflows passed.
- M13a models a fresh process rereading an untrusted synthetic checkpoint that contains the last-confirmed document, candidate, stage/session/epoch and fake draft. It always returns `FRESH_OWNER_REVIEW_REQUIRED` without replay or draft clearance, even after a self-reported `SETTLED` stage.
- M13b composes that synthetic fresh-owner review with the existing M12o/M12p four-consumer ticket/presenter contracts and builds a read-only `state:error` overlay with old confirmed rows and retained drafts. It is unmounted.
- `services/hub/ApolloHubTodoStore.qml` is still the sole live writer: one `FileView`, one `todoFile.setText`, nine legacy mutation methods. `ticketProducerEnabled`, `guardedWriterEnabled`, and `independentlyAuthenticatedTicketReceipt` remain source-literal `false`.

### M13c test-only composition

New `tests/tasks/fixtures/TaskRecoveryEvidenceM13c.cjs::evaluate()` consumes only caller-supplied synthetic values. It has no I/O, QML dependencies, timers, network, file deletion, storage or process calls.

1. Require an explicit **independently supplied fake test pin** containing a SHA-256 digest of the exact M13a checkpoint bytes, a digest of separately observed source bytes (or an explicit source-missing marker), prior session and epoch, stage ID, new owner epoch, and synthetic draft-captured timestamp.
2. Reject altered checkpoint/source bytes, stale/wrong stage ownership, unexpected source classification or a M13b overlay that differs from the M13a last-confirmed rows/draft.
3. Retain the same `RECOVERY_REVIEW` mode and old read-only rows. A matching SHA-256 from an arbitrary caller proves **equality to the provided test pin**, **not** that the pin was independently trusted. Every return advertises `sourceTrusted:false`; positive results are marked `SYNTHETIC_PIN_MATCH_REVIEW_ONLY`.
4. Evaluate age using an explicitly supplied `nowMs`, test-only `draftCapturedAtMs`, and a caller-selected `reviewAfterMs` (1 ms through 30 days for test coverage). Classify:
   - `REVIEW_RECENT`: review age below threshold.
   - `REVIEW_OVERDUE`: review age at or above threshold.
   - `CLOCK_UNCERTAIN`: the observed clock precedes the claimed capture timestamp.
5. Every one of these statuses holds the draft for operator review; never automatically removes it, claims permanent persistence, clears it on a fake `SETTLED` receipt, retries a write, restores data or treats recovery as a production action.

The **review threshold is not a chosen production expiration policy**. In this test, overdue means highlight for review, *never erase*. Synthetic timestamps are caller-authored and do not establish clock provenance. `draftPersistence:"NOT_APPROVED_FOR_PRODUCTION"` deliberately communicates the unresolved consent/storage decision.

### Future trust and privacy decisions, not silently resolved

The eventual application-owned coordinator needs explicit independent evidence authority: verified exact source identity, approved owner epoch and rollback protection, trusted checkpoint provenance, retained backup receipt, and refusal of same-stage replay/late callbacks. A valid SHA of data copied from the same untrusted file does not satisfy those requirements. The operator must also decide if real drafts should persist across restarts; if yes, identify acceptable encryption/permissions, recovery visibility, retention duration, manual deletion semantics and what should happen when encrypted storage is unavailable. M13c stores **no real drafts** or sensitive TASKS contents.

## HOW TO USE

There is no new menu, local command, permission change, restart or feature activation. GitHub CI executes:

```bash
node --test tests/tasks/test_task_recovery_evidence_m13c.cjs
```

Tests use the actual TASKS v3 policy and existing M13a/M13b/M12o/M12p pure helpers with fabricated task titles and drafts, entirely in memory. No new temp files or production paths are created by M13c. Existing M13a regression tests still use disposable CI fixture paths.

## VERIFY

M13c test vectors cover all four surfaces HUB/DETAILS/PLANNER/PROJECTS, previous `RESERVED` and `SETTLED` states, source at candidate/old/missing/foreign, separately pinned SHA mismatch, fake pin changed session/epoch/stage, altered review/overlay/draft, finite review-window guard, overdue review and clock rollback. In every case write/replay/restore/delete/clear authorities remain false. Regressions rerun M13b/M13a/M12o/M12p and M11d single-writer source inventory. **CI result must be inspected before declaring verification complete.**

This is a *synthetic evidence equality* contract, not authenticated recovery, real clock validation, hardware durability or native UI acceptance. The earlier operator-observed M12x native PASS remains bounded to the isolated legacy save/reload test.

## WATCH OUT FOR

- The test pin is **not a signing root or trustworthy external service**. It is explicitly marked `M13C_SEPARATE_FAKE_TEST_PIN`. A malicious peer capable of changing both source and pin can spoof a matching digest. Do not enable production tickets based on M13c.
- A passing check does not certify the checkpoint's `SETTLED` state, a source owner or the authenticity of its contained draft.
- Retaining real user drafts across restarts could expose task titles, descriptions, due dates, project names and other sensitive context. No persistent draft storage design is accepted yet.
- The existing public `TodoPolicy.view(error)` currently hides normal task rows; the synthetic M13b overlay is still unmounted and **must not be treated as deployed UI**.
- `reviewAfterMs` is a supplied testing threshold, not a default cleanup schedule; no timer, deletion API, service, daemon or background monitor was created.
- No local `git pull`, reset/clean, real task file inspection or Quickshell restart was performed.

## CHECKLIST

- [x] Verify M13b merged and current Syntagma/ownership/current `main`
- [x] Inspect M13a/M13b/M12o and live TASKS writer
- [x] Add pure fake separately pinned evidence comparison and owner-bound review
- [x] Treat overdue and clock rollback as nondeleting review states
- [x] Add synthetic regression tests for all four consumers, prior settlement states and negative cases
- [x] Preserve production disabled gates and source-only scope
- [ ] GitHub CI complete, independent review
- [ ] Operator PR review/merge
- [ ] Operator decision on real-draft persistence, retention period, privacy/permission model and manual deletion
- [ ] Independently authorized real-source/host-stage provenance and actual UI wiring

## NEXT

Following review/merge, develop a **disabled-only operator retention decision model**, not automatic expiration: options should preserve drafts without deleting by default, permit intentional export or deletion only with explicit user authorization and verified target ownership, and refuse a second automatic replay. Then resolve real independent source identity and recovery trust before a production integration PR. Keep the M12l single logical coordinator and future sync adapters separate.

## DECISIONS

**Implemented:** test-only equality checking against fake independent pins and configurable review-age classification.  
**Not yet decided:** real draft storage or retention policy, trusted checkpoint pin issuer, release/epoch authority, security against malicious same-user processes, deletion rights or actual UI display.  
**Not authorized:** production ticket activation, persistent draft logging, local workstation mutation, automatic cleanup or restore, privileged broker, migration, live Hospital registration or PR merge.
