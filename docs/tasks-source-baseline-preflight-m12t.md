# 🏥💜 TASKS M12t // Source Baseline and Existing Backup Evidence Integration

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Correlate planned ticket baseline with source and committed backup evidence in disposable fixtures  
**WORKER //** External Hospital-compatible ChatGPT doctor; no verified Hospital registration or live room attachment  
**BASELINE //** GitHub `main` at `3d6c4541e4643d5a2efb7a717ce93b2c0ce73eeb`, November 2, 2026  
**CLASSIFICATION //** **CI-ONLY TEST FIXTURE AND READ-ONLY OBSERVATION. NO PRODUCTION WRITER AUTHORIZATION.**

## IMPLEMENTATION

### Why this is worth doing, and what already exists

The accepted [M12l ADR](../MODEL/contracts/tasks-storage-ownership-adr-m12l.md) keeps one in-application logical coordinator and explicitly defers a privileged broker unless an observed requirement justifies it. [M12r](./tasks-disabled-ticket-admission-m12r.md) repaired the future hard-disabled ticket admission; [M12s](./tasks-real-store-native-smoke-m12s.md) added a standalone operator-driven native smoke for the **existing legacy** store, which is **not yet confirmed as run** by the operator. These steps alone don't prevent a future ticket from being planned against stale task bytes.

We **already** have a capable byte-exact capture/verify fixture from [M10e](./tasks-verified-backup-restore-m10e.md) and synthetic code-only rollback/failure tests in [M11z](./tasks-synthetic-backup-code-rollback-m11z.md). Another backup engine, daemon or storage service would duplicate mechanisms and add operational risk.

M12t therefore adds only two test-only files: `tests/tasks/fixtures/TaskSourcePreflightM12t.cjs` and `tests/tasks/test_task_source_preflight_m12t.cjs`. The new helper performs **read-only observation** of a deliberately named private `m12t-disposable` fixture:

1. Require an explicit expected SHA-256, a valid M12q ticket plan in the `WRITING` state, and the real TASKS v3 policy.
2. Refuse paths outside an absolute `m12t-disposable` folder; validate owner-private folder, backup root, regular single-link source, and no symlink source.
3. Read the source as raw bytes, refuse oversized or changed initial hashes, and use the **existing M10e `verifyBackup`** for an already committed backup; require matching source filename, SHA-256 and **byte-for-byte content**.
4. Parse source through the actual `ApolloHubTodoPolicy.js` and compare its entire projected view to the *ticket's planned baseline*. Check the planned candidate parses.
5. Reread the exact source bytes after inspecting the backup and ticket. Refuse if changed. Return an explicitly `writeAuthorized:false` result, even when the observation matches.

This does **not** create a backup. The existing M10e `capture` creates committed backups in the test suite only, under `mkdtemp` roots. It does **not** replace [M11z](./tasks-synthetic-backup-code-rollback-m11z.md), and M12t does not call M10e's restore method.

### Proof boundary

A positive result says only **"the disposable source, previously committed backup and intended in-memory ticket baseline matched when independently read"**. It does **not** mean a stage is reserved, a real TASKS write is allowed, the source cannot change after the check, the backup is authenticated against a hostile same-UID process, or SQLite and JSON are one atomic transaction. It is not a lock or compare-and-swap operation. The helper is deliberately not imported into Quickshell.

## HOW TO USE

No visible menu, new service, local installation, backup creation, data-file inspection, Quickshell restart or activation. GitHub CI runs:

```sh
node --test tests/tasks/test_task_source_preflight_m12t.cjs
```

Native M12s validation, when separately approved, still follows its own disposable test runbook. This M12t suite cannot substitute for that observation.

## VERIFY

The M12t suite checks valid synthetic source+backup+ticket alignment; missing/invalid external baseline pin; source edited after capture; a freshly computed spoofed pin that no longer matches the original backup; corrupted backup; ticket based on a different source document; unsupported document; missing, symbolic-link and hard-linked source; and no production writer/import/flag changes. Existing M10e/M11z/M12q/M12r/M11d/M11t safety checks run alongside it in scoped CI.

**Pending:** CI on final commit, independent code review, native M12s observation, authentic production source identity and permission boundaries, backup retention, crash/restart handling and operator acceptance.

## WATCH OUT FOR

- **Do not put a real task path in this fixture.** Only `m12t-disposable/apollo-hub-todo-v1.json` and its synthetic backup are accepted. There is no production API and no launch path.
- **Same-UID writer:** an uncooperative process can replace bytes *after* readback. M12k proved this boundary. A read-only preflight and verified SHA do not fence such a process.
- **No durable authorization:** `writeAuthorized:false` is intentional. M11t/M12b's production evidence gates remain open; the accepted M12l ADR must be used to reconcile their privileged-host assumptions rather than claiming a synthetic check passes a real gate.
- **First-run absent data:** the fixture refuses missing source, including a genuinely empty initial installation. That initial-creation case needs a separately specified explicit and safe bootstrap contract before any future production gate is enabled.
- **No automatic restore:** a mismatch retains data for investigation. Code rollback must not overwrite task JSON or a later valid revision.
- **Schema and provenance:** current v3 policy parsing is the existing application policy; it is not an independently authenticated OS read, proof of absence of duplicate JSON keys, or a power-loss durability test.

## CHECKLIST

- [x] Reverify M12s merged into `main`, no competing open TASKS PR and existing disabled flags
- [x] Inspect M10e verified backup, M11z synthetic rollback, M12q producer, M12l ADR and source policy
- [x] Reuse M10e instead of implementing another backup engine
- [x] Add fixture-only source/backup/ticket observation and negative tests
- [ ] GitHub CI green and independent review
- [ ] Operator review/merge
- [ ] Separate native M12s data-path and callback observations
- [ ] Real source authorization, initial-creation policy, backup retention, crash/restart and compatible trust evidence
- [ ] Explicit final approval before changing any production writer or ticket UI flag

## NEXT

Review M12t CI and merge only on operator acceptance. Obtain native M12s results independently. Then design a **bounded in-application pre-write revision check and manual recovery contract**, with genuine source authority and a safe initial-creation case. Do not duplicate M10e/M11z, add an always-on broker, or enable tickets just because a synthetic preflight returned green.

## DECISIONS

**Accepted architecture:** M12l local-first one writer, separate synchronization adapters, no automatically required privileged service.

**Implemented in this candidate:** only a CI-only read-only observation bridge reusing M10e and the real v3 policy. Every result explicitly denies write authority.

**Not implemented or authorized:** live task access, local workstation changes, native Quickshell test execution, autonomous restore, real backup/rollback, production ticket activation, GitHub task synchronization or live Hospital registration.
