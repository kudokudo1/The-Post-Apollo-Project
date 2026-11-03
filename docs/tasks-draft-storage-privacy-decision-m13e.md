# 🏥💜 TASKS M13e // Draft Storage, Privacy, and Recovery Decision Dossier

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Establish operator-reviewable privacy and persistence choices before any real recovery draft storage  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible doctor, no live registration verified  
**GITHUB BASE //** `337a38f53fccca5254b9a9a9f914d9dd2a04854c`, November 3, 2026  
**AUTHORITY //** Repository-only decision dossier and source-level tests; no local workstation edits, new production persistence, UI activation or PR merging  
**DECISION STATUS //** **PROPOSALS ONLY. No production policy has been chosen or approved.**

## IMPLEMENTATION

### Current mechanism and checkpoint

- M13d [PR #1084](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1084) is **merged** at `337a38f53fccca5254b9a9a9f914d9dd2a04854c`. Its fake KEEP/EXPORT/DELETE choices and fake second gestures never execute actions.
- M13a persists a *synthetic* record to an isolated test directory across a new test process, including a last-confirmed document, uncommitted candidate, stage and fake draft. That test file is not a user-facing draft store, secure journal or approved format.
- M13b creates an unmounted, read-only recovery overlay for Hub, Details, Planner and Projects. The live `TodoPolicy.view(error)` still hides rows; M13b is not installed.
- M13c compares synthetic recovery bytes to a caller-supplied fake pin. `sourceTrusted:false` is intentional. Review-age labels never expire or delete drafts.
- Production `services/hub/ApolloHubTodoStore.qml` remains the one FileView writer using the established task JSON. `guardedWriterEnabled:false`, `ticketProducerEnabled:false`, and `independentlyAuthenticatedTicketReceipt:false` are still source literals. No new local TASKS file, service, key store or draft store was introduced.

### The privacy problem we must solve

An unfinished task draft may contain a title, private description, date, project name or operational context. Keeping it **in process memory** while Quickshell runs does not automatically write another file, but it disappears on process exit. A **persistent recovery draft** survives a restart by storing bytes somewhere; those bytes may be readable by other local programs with equivalent permissions, included in backups, copied to a sync provider, or exposed by export, logging and crash diagnostics.

A SHA-256 digest helps compare exact bytes to a prior reference. It does **not** encrypt data, certify the reference is trustworthy, or authenticate who approved storage. OS `0600` permissions likewise do not, by themselves, fence a malicious process running as the same user. A proposed encryption mode is not an implemented or tested encryption system.

### Options for operator decision

| Decision | Option A | Option B | Proposed engineering preference, not accepted |
| --- | --- | --- | --- |
| **Should unfinished drafts persist?** | **Memory only:** no new persistent draft bytes; drafts can be lost after crash | **Opt-in encrypted local:** drafts may survive restart after separately verified encryption and unlock | Choose B **only if** recover-after-crash is worth added privacy/key/recovery complexity. Keep A until approval |
| **Who may see a recovered draft?** | Show only a neutral `Recovery available` indicator while locked | Show draft title/contents before unlock | A until real user/owner identity and unlock mechanisms are established |
| **Where could draft data live?** | Current process memory only | Separately reviewed private local recovery path, distinct from canonical `apollo-hub-todo-v1.json` | Do not select a path without verifying Quickshell/XDG behavior, ownership, symlink handling, filesystem and backup interactions |
| **At-rest protection** | None needed for memory-only persistence (because nothing new is written) | Real authenticated encryption under a reviewed key provider, with authenticated metadata and key rotation/recovery plan | Never label plaintext or a hash as encrypted. No key provider has been selected or verified |
| **Retention after restart** | Session only (memory proposal) | Keep pending recovery draft until manual review, optionally mark overdue | Overdue means *review*, not deletion. No automatic deletion schedule |
| **Exports** | Disabled | Explicit per-draft export to reviewed destination/format with disclosure warning and independent permission | No automatic sync, default location, or silent plaintext export |
| **Delete/undo** | End memory session, subject to source state | Explicit, separately confirmed draft-only deletion, handling backups/exports independently | No automatic purge; never delete canonical tasks, confirmed source or source backup as a side effect |
| **Backups/key loss** | No new draft backup | Explicit encrypted backup/recovery policy; document failure when key unavailable | Do not back up uncommitted draft bytes silently, and do not promise recoverability without key recovery tests |
| **Remote sync** | Off | Future separately designed adapter | Off in M13e, as required by M12l local-first ownership |

**No item in this table is an operator-selected configuration.** The intent is to make tradeoffs concrete, not to smuggle a storage policy into a commit.

### Source-only M13e privacy policy gate

Add `tests/tasks/fixtures/TaskDraftPrivacyDecisionM13e.cjs`, a pure, unmounted reviewer. It accepts two *synthetic proposal shapes*, each with `operatorApproval:"NOT_GRANTED"`:

1. `MEMORY_ONLY`: `storageLocation:NONE`, no drafts persisted, session-only retention, no export, no sync or content logging. This does not meet cross-restart recovery.
2. `LOCAL_ENCRYPTED_OPT_IN`: storage path, key provider, backup model, export format/target and actual encryption remain **unselected/unverified**. It can only return `ENCRYPTED_LOCAL_DESIGN_REVIEW_CANDIDATE`, listing open decisions. Configurable `reviewAfterMs` is an advisory test threshold, not a deletion clock.

It refuses invented plaintext persistence, cloud sync, automatic deletion, full-content logging, whole-TASKS deletion scope, unreviewed export destinations, fabricated verified encryption and any claim `operatorApproval:"GRANTED"` inside test data. No real persistence or encryption API is present, and no user data is accessed.

Its `decisionBoundary()` consumes fake M13d KEEP/EXPORT/DELETE intent or fake second-gesture results and confirms that **even an apparently complete choice plus policy cannot authorize any action**. All paths return:

```text
policyApproved=false
readAuthorized=false
writeAuthorized=false
persistAuthorized=false
exportAuthorized=false
deleteAuthorized=false
clearDraftAuthorized=false
replayAuthorized=false
restoreAuthorized=false
syncAuthorized=false
productionActivation=false
sourceTrusted=false
```

The gate is a **contract test**, not an authentication, permission or cryptographic implementation.

## HOW TO USE

No Quickshell UI or local installation is added. GitHub CI runs:

```sh
node --test tests/tasks/test_task_draft_privacy_decision_m13e.cjs
```

This command is for developer test environments only. It uses fabricated drafts and verifies policy proposal shapes in memory. Running it does not choose the user's privacy settings.

**Operator decisions before a real implementation PR:**

1. Select memory-only or separately consented persistent local recovery. The former cannot recover uncommitted drafts after a crash.
2. For persistence: identify an actually available key provider, unlock behavior, storage path, permissions and backup/key-loss recovery.
3. Decide whether a locked recovery screen may reveal titles/counts, and whether drafts are stored per widget, installation or operating-system account.
4. Select manual retention and optional *review* reminder interval. Specify whether any future deletion should be possible and how explicit action/undo will work.
5. Set export format and destination authorization, with explicit disclosure and no automatic cloud upload.

These decisions should be recorded by the operator and followed by a separate security review and **native disposable tests** before production implementation.

## VERIFY

Test M13e's two proposal candidates, no-choice refusal, wrong fields, unprotected plaintext, automatic deletion, logging, sync, forged operator approval, missing encryption decisions, review-period range, and all three fake M13d choices. Regress M13d/M13c/M13b/M13a/M12o/M11d. No production source files are changed. CI success only validates fixture semantics; it does not establish the actual system's ability to encrypt or persist recovery drafts.

## WATCH OUT FOR

- **No persistence approval exists.** Neither a test proposal nor this report means the user wants drafts on disk.
- Never store recovery snapshots or draft descriptions in general operation logs, Git commits, GitHub CI artifacts, automatic crash reports or remote adapters.
- A separate encrypted draft file plus task JSON plus a journal is *not* one atomic transaction by default. A future design needs an explicit consistency/recovery protocol or one transaction owner.
- A locked display must not expose sensitive draft titles by accident. Distinguish OS-user restrictions from a real unlock.
- Secure deletion of SSD data, filesystem snapshots, backup copies and previously exported plaintext cannot be promised solely by deleting one filename. A future UI should describe actual deletion scope precisely.
- Under the M12l accepted architecture, a local-first coordinator retains single authoritative task write ownership; no special broker is being installed automatically.
- No local Git pull/reset, permission edits, Quickshell restart, real task inspection, OS keyring access, or production ticket enablement occurred.

## CHECKLIST

- [x] Verify M13d merge and current GitHub HEAD, Syntagma and no TASKS PR collision
- [x] Confirm live store is still sole FileView writer and ticket modes disabled
- [x] Record actionable memory-only vs opt-in encrypted-local alternatives
- [x] Keep actual path/key/backup/expiry/export/privacy decisions operator-owned
- [x] Add unmounted pure privacy proposal validator and negative tests
- [x] Ensure M13d fake gestures never promote to storage/export/delete rights
- [ ] GitHub CI complete and independent source review
- [ ] Operator review/merge of this *proposal*, not approval of any listed option
- [ ] Operator chooses actual draft persistence, visibility, key, backup, review, export and deletion rules
- [ ] Verified native encryption/permissions, user-controlled retention and trusted source ownership tests
- [ ] Separate permissioned production integration and explicit user acceptance

## NEXT

After reviewing M13e, the productive next step is **operator selection of the actual privacy/storage policy**. The follow-on implementation should start with a disposable encrypted-storage capability test under the chosen key provider and OS environment, not with a live draft dump. Independently settle real source/epoch provenance, authenticated receipt and final producer admission before installing a recovery UI.

## DECISIONS

**This milestone decides only the boundary:** do not persist real drafts by default; do not equate operator-choice proposals with execution authorization; never auto-delete or silently export. **Those are conservative safety requirements of this test**, not a selected production retention policy.

**Awaiting operator approval:** whether to persist, encryption/key/unlock provider, exact path, account visibility, backup/key recovery, review cadence, manual deletion/export semantics, and production activation.

**Unchanged:** real TASKS data, live UI/error-state behavior, M12l single-writer architecture, disabled ticket gates, and absence of live Hospital registration.
