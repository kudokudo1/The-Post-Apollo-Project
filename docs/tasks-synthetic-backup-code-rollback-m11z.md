# 🏥💜 TASKS M11z // Synthetic source, exact backup and code-only rollback preflight

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M11z disposable backup, source-conflict and code-only rollback rehearsal  
**PROVIDER //** OPEN AI // CHATGPT, external Hospital-compatible (not live Hospital-registered)  
**SOURCE BASELINE //** GitHub `main` at `58f342893ec67a1136aaacafdecf26e23facaabc` (2026-10-31); recheck before further changes  
**CLASSIFICATION //** **TEST-ONLY, DISPOSABLE SYNTHETIC COPY**. No real production host, task-file access, installation, rollback or activation.

## IMPLEMENTATION

M11y tests cryptographic integrity of a synthetic release against separately supplied trust arguments; M11x documents production architecture. M11z tests a different boundary: **the backup and code-rollback procedure must not silently overwrite source task bytes or a journal**.

New `TaskSyntheticBackupRollbackM11z.py` is an **import-only** fixture module with no CLI, QML component, installer, production path, auto-start or application import. It accepts only an explicitly named absolute owner-private `m11z-synthetic-copy` directory. Tests create that directory under `tempfile.TemporaryDirectory`; there are no production data sources.

- `prepare_backup` independently rereads the source using the **existing M11l stable-source checks and v1/v2/v3 task document parser** (without granting any M11l owner/writer authority). A caller supplies an exact expected SHA-256 baseline, which the function cannot prove was obtained independently; tests derive the hash from the **synthetic** fixture only.
- Before write it rechecks source bytes; creates `source-before-rollback.bak` once with `O_EXCL`, `O_NOFOLLOW`, owner-only permissions, `fsync`; rereads the copy from disk and the source, checks byte-for-byte equality and directory metadata durability. A second bootstrap refuses. The backup is **not** an automatic restore source.
- Test-only injection points simulate external editor modifications before backup, between backup creation and readback, and corruption of the backup itself. The function refuses and **preserves the created backup as forensic evidence** when a post-copy check fails. No automatic deletion or replacement of the original task document.
- `inspect_code_rollback` requires exact preserved source/backup hashes, owner-private metadata, a strict *synthetic JSON* `QUIESCED` + `pending=false` journal record, and independently supplied expected synthetic code v1/v2 digests. It is read-only.
- `rollback_synthetic_code_only` requires separate explicit `approved=True` **for this disposable fixture only**, and an exclusive synthetic advisory `flock`. Rechecks source, backup, journal and current/previous code before constructing one private fsynced temporary code marker. Rechecks before atomic replacement. The **only** intended changed path is `active-code.ref`. The source, backup and journal bytes must remain exactly equal after rollback; it never writes either actual task JSON or a SQLite task database.
- If a conflicting source edit, unquiesced journal marker, wrong code pin, corrupted backup, missing approval, lock contention or second replay is observed, the operation refuses. Explicit refusal and evidence retention are more important than manufacturing a green recovery status.

### What this does and does not establish

**What successful CI establishes:** In one **cooperative disposable Linux test environment**, a pinned synthetic v3 task source can be read and validated, copied once to an independently rereadable byte-exact backup, and a separate synthetic code marker can be reverted after quiescence checks without changing the source, backup or journal. Artificial external edits and invalid metadata trigger refusals.

**What CI does NOT establish:** Durable protection against a noncooperating same-user writer, a truly independently trusted source digest or code hash, production source identity, a long-lived OS-owned host, authentic quiescence, active-process shutdown, crash/power-loss ordering, real SQLite journal reconciliation, native FileView callback attribution, safe user-file rollback, backup retention policy or actual deployment. The injected `QUIESCED` marker is **test data**, not evidence of a stopped process; `flock` is advisory. Filesystem rereads are bounded checks, not a transactional guarantee against malicious writers between final check and rename.

### Required test matrix

| Test | Expected outcome |
| --- | --- |
| Valid disposable v3 source, correct external *test* digest | One private byte-for-byte backup and read-only plan |
| Wrong digest / unsupported schema / missing source | Refuse without new backup |
| Source edited before copy | Refuse, never create stale backup |
| Source edited after backup but before independent readback | Refuse; preserve backup and changed source as evidence |
| Backup content corrupted after copy | Refuse; never restore older data over original |
| Backup already present | Refuse; do not overwrite |
| Symlink, hardlink, weak permissions, wrong directory name | Refuse |
| Strict synthetic journal is not `QUIESCED` or is pending | Refuse code change |
| Wrong journal source or backup hash | Refuse |
| Explicit synthetic-only approval absent | Refuse |
| Current/previous code digest mismatched | Refuse |
| Exclusive rollback lock held | Refuse |
| Source/code changes before final code replace | Refuse |
| Successful test-only code marker rollback | Change only `active-code.ref`; original task source, backup and journal unchanged |
| Repeating an already applied rollback | Refuse; no implicit replay |
| Production writer/shell source audit | One existing `FileView`, `guardedWriterEnabled: false`, no M11z mount |

## HOW TO USE

No actions on the operator's Fedora machine. GitHub CI or a **separate disposable test checkout** can run:

```sh
python3 tests/tasks/test_task_synthetic_backup_rollback_m11z.py
```

No `git pull`, reboot, Quickshell restart, actual backup/restore, source migration, key installation or task-data inspection is involved.

## VERIFY

- GitHub source preflight verified M11y already merged; no competing open TASKS PR or M11z branch; current production store remains the single existing `FileView` and hard-disabled guarded flag.
- M11z has only new test-only fixture, tests, this report and the scoped read-only GitHub workflow. Earlier production/store files and M11l's fixture restriction are unchanged.
- CI should rerun this private fixture matrix, M11y signed-release tests and M11x/M11t/M11d source-only checks. CI success will be reported only once confirmed and will **not** close any of M11t's nine production acceptance gates.

## WATCH OUT FOR

- The synthetic `journal.json` is **not** the actual M11p SQLite journal. This tests a rollback policy decision and byte-preservation property, not real host/journal integration.
- The code rollback marker is an isolated fake reference, **not** Fedora configuration or an executable; the helper is not a safe production deployment procedure to copy into the live system.
- A backup is potentially stale as soon as another program edits source; the test **never restores it automatically**. Authentic writer quiescence and external-writer race prevention remain separate work.
- A valid script signature (M11y) does not make a backup or source safe, and a read-only backup hash does not authenticate a script. Keep those ownership boundaries distinct.
- The current TASKS UI `onSaved` still publishes before OS-host settlement, and error snapshots may hide confirmed rows. These are **unresolved future production issues**, not fixed by M11z.
- No real task data, local workstation state, production writer, QML caller, SQLite task-data file, remote TASKS sync, power-loss test or Hospital room record was changed.

## CHECKLIST

- [x] Confirm prior M11y merge and fresh source/ownership baseline
- [x] Reuse existing M11l synthetic schema check
- [x] Implement private exact backup with independent readback and retained evidence
- [x] Test external source change, corrupted backup, invalid paths and permissions
- [x] Rehearse one explicitly approved synthetic **code-only** rollback
- [x] Guard against unquiesced marker, wrong hashes, competing lock and replay
- [ ] GitHub CI verification and independent review
- [ ] Operator review/merge
- [ ] Separately resolve real trust anchor, source and data-backup permissions, authentic journal quiescence, guarded UI and native callbacks
- [ ] Separately authorize live implementation, installation, activation, data recovery or migration

## NEXT

Review the PR and CI. After M11z, the next useful boundary is an **isolated production-shaped preflight design**, combining previously tested trust/root, independent actual-source authorization (without reading live data yet), legitimate journal quiescence, and UI completion semantics. Any runtime implementation requires a fresh assignment and explicit permissions; do not relax disposable source restrictions.

## DECISIONS

**Implemented:** Synthetic source/backup integrity checks and synthetic code marker rollback rehearsal.

**Open:** Real source and trust authority, backup lifecycle, hostile-writer policy, journal quiescence, production host deployment, UI asynchronous confirmation and exact acceptance/rollback procedure.

**Not authorized:** Production task-data access, Fedora changes, actual code rollback, signed production releases, merge, guarded writer activation, SQLite task-data migration, automatic data restore or live Hospital registration.
