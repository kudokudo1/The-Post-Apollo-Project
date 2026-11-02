# 🏥💜 TASKS M12z // Disabled Exclusive First-Create and Restart-Ambiguity Contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Demonstrate no-clobber first creation and no unsafe replay after lost acknowledgment, without enabling production writes  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor, no verified live registration  
**GITHUB BASE //** `03b1ba929cec62e9914bc7e12899fa682c31fb5d`, 2026-11-02  
**SCOPE //** Source-only fixture and disposable GitHub CI. No local machine writes, native shell changes, real TASKS inspection, activation or migration.

## IMPLEMENTATION

### Established evidence and dependency

The operator's M12x native result was `M12u // PASS // NATIVE_AND_DISK_AGREE` for the existing **legacy** one-FileView synthetic add and reload. It included `INITIAL_EMPTY`, `TICKET_DISABLED`, `NATIVE_SAVE`, and `NATIVE_RELOAD`, plus an independent JSON v3/one-task SHA-256 check. This does **not** prove first-run safety or ticket activation.

M12y [PR #1046] merged on 2026-11-02. Its `TaskSourcePreflightM12t.cjs::classifyAbsent()` rejects every bootstrap request, including an apparently empty private source directory with a caller-declared first installation. It distinguishes `POSSIBLE_FRESH_INSTALL` from existing source or missing-with-history, but **never** proves independent installation provenance.

### What M12z adds

- A **pure and test-only** `TaskFirstCreateContractM12z.cjs` with `prepare()` and `observe()`. It takes M12y's result, an explicit fake install claim and the real TASKS v3 policy; computes and validates an exact empty-document candidate; and models a simulated exclusive-create/independent-readback receipt. It performs **zero filesystem I/O** and is never imported into Quickshell or an actual writer. It never returns `writeAuthorized:true`, `bootstrapAuthorized:true` or `restoreAuthorized:true`.
- The fake claim is labeled `M12Z_FAKE_INSTALL_EVIDENCE`; its `instanceId`, generation 1, first-run flag and exact source basename are **shape checks only**. An arbitrary caller could reproduce the fake claim. It is *not* an attestation, stored installation identity, OS owner, or trusted release signal.
- A **disposable synthetic CI test** creates an owner-private `m12t-disposable` directory and empty `backups` directory via `mkdtemp`. Only the test code calls actual Linux `openSync(O_CREAT|O_EXCL|O_NOFOLLOW|O_WRONLY,0600)`, writes the synthetic document, fsyncs the file and parent directory, and independently reopens the source with `O_NOFOLLOW` for byte-for-byte readback.
- Verify a second exclusive create fails with `EEXIST` and the initial bytes remain unchanged. Also simulate the important crash window: **file created but completion acknowledgment lost**. A missing receipt must remain unconfirmed; a second create still fails and M12y classifies the source as `EXISTING_SOURCE`, not an absent boot.
- Refuse already-existing source, broken symlink, any backup/pending history, missing/incorrect fake claim, invalid candidate hash, changed readback, missing completion proof or ambiguous source. All returns deny real write/restore/bootstrap authority.

This is strictly narrower than shipping a host, journal, lock, credential manager or a new TASKS writer. The actual first-create syscall exists **only in disposable test cases**. No production code is updated.

### Conceptual contract boundary

```text
M12y read-only absence review
  -> possible fresh installation [still denied]
  -> M12z fake-claim candidate plan [simulation only; still denied]
  -> test-owned O_EXCL create against disposable fixture
  -> independent synthetic source reread
  -> simulated receipt (not OS identity or durable app acceptance)
  -> production authorization STILL FALSE

source existed / symlink / prior backup / lost confirmation
  -> NO AUTOMATIC REPLAY
  -> external review required before any future real action
```

## HOW TO USE

No operator terminal command, merge-triggered desktop change or native panel. Review GitHub CI:

```sh
node --test tests/tasks/test_task_first_create_contract_m12z.cjs
```

The command is CI/developer-test-only: it **does** create and remove private synthetic temporary fixture files when run, and is not authorization to run it against live user data. It has no configurable real-task source path.

## VERIFY

- New M12z suite exercises exact v3 synthetic candidate planning, no-clobber `O_EXCL` syscall, independent readback, second-create `EEXIST`, lost acknowledgment, tampered source, absence of readback, existing source/symlink/history, fake-claim refusal and unchanged production code.
- Existing M12y missing-source and M12t committed-backup/source comparisons remain unchanged and are rerun.
- Existing M11d single writer, M12r disabled tickets and M12x native fixture source contracts remain regression gates.
- No synthetic test can establish first-run provenance on the operator's real desktop. No native first-create, power-loss ordering, recovery journal replay or independently authenticated settlement is claimed.

## WATCH OUT FOR

1. A fake install claim is **not authority**. Any later production step requires a real operator-approved installation-provenance source, its ownership/rollback policy and collision handling. A clean empty folder alone cannot distinguish an actual first installation from lost data.
2. `O_EXCL` prevents overwriting the pathname during that particular create attempt; it does not fence a malicious same-user peer after creation, authenticate the caller or make a cross-file transaction.
3. Filesystem `fsync` in a disposable CI runner demonstrates a syscall path, **not** hardware power-loss durability, real target filesystem behavior or authenticated receipt binding.
4. A lost acknowledgment must lead to read-only source inspection and explicit recovery decision; do not automatically retry the create or treat a later existing file as a failed create.
5. No `ticketProducerEnabled` enablement, `guardedWriterEnabled` enablement, new `FileView`, production bootstrap, SQLite migration, forced local pull, code reset or real task-data access is authorized.

## CHECKLIST

- [x] Reverify M12y merged, current GitHub, protocol and no competing TASKS PR
- [x] Reuse M12y absence classification and real v3 policy
- [x] Add pure test-only candidate and receipt model with false authority flags
- [x] Test actual synthetic `O_EXCL`, `EEXIST`, lost receipt and byte readback
- [x] Add scoped CI and confirm production writer remains hard-disabled
- [ ] CI passing on PR head; operator source review/merge
- [ ] Establish trusted first-install provenance and crash/restart authority owner
- [ ] Design final in-application coordinator source readback/settlement
- [ ] Separate native and production authorization when future gates pass

## NEXT

Review the test evidence. Then focus on **durable stage identity and the last-confirmed UI/draft recovery contract** under M12l, not enabling tickets. Define what application-owned persistent install provenance could actually prove and which OS first-create primitives are available from the chosen runtime, with no production mutation until separately authorized.

## DECISIONS

**Implemented:** an intentionally nonauthorizing, disposable first-create/no-replay test contract.  
**Still uncertain:** real installation provenance, same-UID threats, native source lifecycle, crash durability and exact first-create integration.  
**Not decided or authorized:** privileged broker, a new permanent process, real storage creation, automatic restore, live ticket production, GitHub synchronization or final operator acceptance.
