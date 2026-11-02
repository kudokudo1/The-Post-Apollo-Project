# 🏥💜 TASKS M12y // Missing Source and First-Run Recovery Classification

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Separate absent initial storage from missing historical task data in a read-only, synthetic preflight  
**WORKER //** External Hospital-compatible doctor, OPEN AI // CHATGPT, no verified Hospital registration  
**BASELINE //** GitHub `main` `20c3c9aa92c57ee896465fba04d7e092ebbf3bb6` (2026-11-02)  
**STATUS //** Test-only read-only contract. No production creation, restore or activation.

## IMPLEMENTATION

### Why this follows M12x

The operator ran merged M12x against a newly created disposable native Quickshell fixture and reported `M12u // PASS // NATIVE_AND_DISK_AGREE`, four ordered native stages, v3 data, exactly one synthetic task and SHA-256 `6841302a6ce0782ab74b7197845ec71645a04e9d34b43679b3f199d0304e21e3`. That closes the limited native legacy-save smoke checkpoint. It does **not** establish a safe first-run production bootstrap or enable the dormant ticket producer.

M12t's existing test-only `TaskSourcePreflightM12t.cjs::inspect()` verifies **existing** source bytes against a committed M10e backup and planned M12q ticket baseline. It correctly refuses a missing source, but cannot distinguish normal initial installation from accidental deletion of an earlier task file. Blindly treating absence as an empty writable document would risk overwriting recoverable history.

### Scope of the change

Add `classifyAbsent()` to the **existing M12t test-only fixture**. It is not imported by `shell.qml`, Quickshell, an app process, or production storage. It accepts only an absolute normalized caller-owned private `m12t-disposable` folder, a real TASKS v3 empty policy and an explicitly Boolean `declaredFreshInstall`. It checks:

1. Existing v3 policy has a valid empty document.
2. Synthetic source/backup directories are private, nonsymlinked and current-user-owned.
3. A source that **exists, even as a broken symlink**, never qualifies as initial absence. Existing-source inspection remains M12t's separate `inspect()` path.
4. A missing source with any backup entry, committed, malformed or pending, goes to `MISSING_SOURCE_REVIEW`. Never delete or auto-restore that history.
5. A missing source without backup history but without an explicit first-run declaration also goes to `MISSING_SOURCE_REVIEW`.
6. A missing source with empty backup directory and a declared first install is only `POSSIBLE_FRESH_INSTALL`. The result **always** requires `INDEPENDENT_INSTALL_PROVENANCE_REQUIRED`. A caller Boolean is not a trusted install identity.

All outcomes have `ok:false`, `writeAuthorized:false`, `bootstrapAuthorized:false` and `restoreAuthorized:false`. There are **no writes**, stage reservations, locks, data restoration, filesystem creation or retry paths in the helper. Synthetic tests create private temporary files only on a GitHub runner.

This is **not** proof that an uncooperative process cannot create or delete a source immediately after inspection. M12l explicitly defers same-user hostile-writer fencing unless the threat model justifies it. A real future coordinator must establish authoritative install identity, exact real-source permissions, a first-create/no-clobber operation and confirmed native readback before granting any write.

## HOW TO USE

No user action or local installation. CI runs:

```sh
node --test tests/tasks/test_task_absent_source_review_m12y.cjs
node --test tests/tasks/test_task_source_preflight_m12t.cjs
```

These test only synthesized `m12t-disposable` storage. No command is provided to create, inspect, delete or recover a real TASKS file, because that would require separate authorization and verified provenance.

## VERIFY

- **Operator native evidence preserved:** M12x disposable legacy save/reload complete; **not** production writer validation.
- **M12y synthetic tests:** candidate first install is always denied write authority; absent without declaration, existing source, dangling symlink, source backup with committed M10e manifest, incomplete backup and unexpected history all avoid automatic creation. Unsafe paths and damaged policy refuse. Source contents and backup bytes are left intact.
- **Existing regressions:** M12t source+verified backup, M12q ticket planning, M12r hard-disabled admission, M11d single writer, M12u/M12x source smoke. CI must pass before review.
- **Native:** Not necessary for the read-only synthetic classification; no live TASKS migration or native write is exercised by M12y.

## WATCH OUT FOR

- A claimed fresh install **is not proof** that data never existed. Positive-looking classifications are still denied. Never use `POSSIBLE_FRESH_INSTALL` as a reason to flip `ticketProducerEnabled`, create JSON, or restore a backup.
- Backup-directory emptiness is only an observation of one directory. Unknown backups, other devices, other paths or prior installs are not ruled out. The helper cannot provide an independent installation identifier.
- `M12t::inspect` for already-existing data remains unchanged. No new store, FileView, host, OS authority or sync adapter.
- Only synthetic fixtures may be supplied to these routines. Do not pass real user paths or relax the hardcoded `m12t-disposable` requirement.
- No automatic deletion, cleanup, backup creation, restore or task-file replacement beyond the preexisting test suite's private `mkdtemp` fixtures.

## CHECKLIST

- [x] Recheck GitHub `main`, Syntagma authority, M12l/M12t plans and open TASKS PRs
- [x] Preserve M12x native PASS as a bounded legacy FileView acceptance result
- [x] Extend existing read-only M12t fixture rather than add a service or second writer
- [x] Explicitly distinguish absence, existing file, backups, ambiguous history and refused paths
- [x] Always return `writeAuthorized:false`, even for declared first-run
- [x] Add negative synthetic tests and scoped CI
- [ ] GitHub CI and independent source review
- [ ] Operator review/merge
- [ ] Separately agree on trusted first-install provenance and actual exclusive-create strategy
- [ ] Future durable recovery/idempotency work; all production activation gates remain open

## NEXT

After source/CI review, the next scoped coordinator milestone is an **in-application, still-disabled bootstrap admission contract**: a trusted installation-state signal, actual exclusive-create/no-overwrite semantics, and independent source readback after deferred native completion. It must explicitly refuse missing files with backups/history and must never replace data on an ambiguous restart. Do not automatically implement a broker, JSON-to-SQLite migration, GitHub sync, or production ticket activation.

## DECISIONS

**Accepted existing design:** M12l single local authority with future sync adapters.  
**This PR only:** synthetic no-write absence classification and tests.  
**Not authorized:** local machine modifications, real TASKS data inspection, first-run source creation, unactivated producer enablement, production migration, PR merge, or live Hospital registration.
