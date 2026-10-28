# 🏥💜 TASKS M11w // Sealed synthetic child ↔ disposable durable journal-owner binding

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / ASSIGNMENT //** TASKS JSON writer continuity; M11w disposable owner lifecycle test  
**PROVIDER //** OPEN AI // CHATGPT, external Hospital-compatible; not live registered  
**REVIEW BASELINE //** `main` at `736031610b6ffacd99b9f0bab8f487d88e4b5045`, 2026-10-28. Recheck the head and ownership before further work  
**STATE //** **TEST-ONLY**. No production host, no Quickshell mount, no real TASKS file, no actual user data or activation.

## IMPLEMENTATION

M11v exercised an observed Linux child process and a synthetic session with a **fictional** epoch. M11w adds an **actual disposable M11l SQLite owner** behind that child, without modifying the existing M11l/M11m/M11u/M11v code.

- `TaskBoundJournalChildM11w.py` is a synthetic-only child script marked with the M11u test header. It accepts exactly an existing private `m11l-tasks-copy` directory, a **sealed M11l implementation file descriptor** and either `NEW` or `EXISTING`. It loads the existing M11l source only from the sealed fd, generates a random process session, and opens a lifetime `CandidateOwner` using journal writer `m11w-<sessionId>`. Its single permitted `reserve` operation is hard-limited to an unmodified `M11W_TEST_0` one-task synthetic document. It cannot itself replace a JSON source file.
- `TaskBoundJournalProbeM11w.py` is a test-only parent module. It verifies the independently provided **test pins** for the M11l source bytes and system interpreter; copies both the child script and pinned M11l source bytes into separate sealed memfds; starts `/usr/bin/python3 -I -S -B` without shell, opens `pidfd_open`, verifies kernel-observed executable device/inode and process start ticks, and accepts only a strict `hello` frame.
- Parent verifies that the session ID observed from the child corresponds **exactly** to the `writer` column of the persisted SQLite `owner` record. Every accepted synthetic message is tied to the current request ID, exact session, epoch and random challenge, and cross-checked against an independent SQLite `mode=ro` journal snapshot.
- `TaskBoundJournalProbeM11w.py` accepts no user-facing CLI. Its helper `attach_synthetic` explicitly refuses wrong directory name, invalid child snapshot, changed sealed M11l bytes, unsupported interpreter pin and mismatched process identity.
- On a synthetic reserve, `stage_history` and `pending_stage` commit via the **existing M11p v2 journal**. Tests kill the owning child with pending stage, then open a fresh, separately observed child and verify new session/new journal writer, epoch increase, permanent `RECOVERY_REVIEW`, unchanged source and backup, and refusal to reserve any further stage.

### What the observed correlation does and does not prove

**When CI passes**, we have observed a Linux process running synthetic script bytes copied from a test fixture, with a kernel-observed executable inode, PIDFD, fresh session and an exact recorded disposable owner writer ID. The process holds the existing OS lock and its journal records a real synthetic reservation. After its abrupt termination, a new process enters durable recovery review. This is more than a mock epoch; the journal comes from the same disposable M11l implementation as earlier native fault tests.

This is **not** cryptographic endpoint authentication against a malicious parent or child. The interpreter and M11l content hashes are calculated in the CI checkout for **functional tests only**, not obtained from an independent trust authority. The interpreter, Python runtime, caller, filesystem ancestors, and module distribution remain trust assumptions; its process identity could be subverted by a compromised same-user environment. The actual production source and TASKS UI are never connected. The M11t `TRUST_EXEC`, `PROCESS_BINDING`, `SOURCE_BACKUP`, `STAGE_CALLBACK`, `UI_CONTRACT`, `RECOVERY_FREEZE`, `ROLLBACK`, `RUNTIME_ACCEPTANCE` and `ACTIVATION_APPROVAL` gates remain **OPEN**.

### Scope constraints

- The only seeded JSON is a synthetic v3 `todo-copy.json` in a disposable private `m11l-tasks-copy` directory.
- The M11l owner module's existing **test-only path restriction is preserved**, never broadened.
- SQLite holds **disposable stage-admission metadata**, not task data. The JSON source is not rewritten by this host test.
- The old production singleton remains the **only live TASKS writer** with `guardedWriterEnabled: false`.
- This is not a full system crash test, power-loss proof, Quickshell native callback test, or operator-machine test.

## HOW TO USE

No changes or commands are needed on the operator's Fedora installation. CI tests use new private `TemporaryDirectory` fixtures, Linux kernel process introspection, a sealed memfd and the source-only M11l owner implementation. In an isolated repository checkout, the offline regression command is:

```sh
python3 tests/tasks/test_task_bound_journal_probe_m11w.py
```

The test is intentionally Linux-specific. Unsupported kernel /proc, root-owned system interpreter, memfd sealing or PIDFD support causes failure, not a production fallback.

## VERIFY

The M11w test matrix covers:

| Synthetic case | Expected outcome |
| --- | --- |
| New child with valid script/interpreter/module pin | PIDFD and executable observed; journal `writer=m11w-<session>`, epoch 0 |
| Competing owner while first is live | Existing M11l OS lock refuses contention |
| One journal reservation, then child kill | `RESERVED` stage, source and independent backup unchanged |
| Fresh owner after death | New session, epoch 1, permanent `RECOVERY_REVIEW`, no new stage admitted |
| Stale session or epoch | Refuse and preserve source/journal |
| Forged `hello` session not equal to durable writer | Parent refuses session binding |
| Incorrect module digest or changed bytes | Refuse before trusted launch |
| Incorrect kernel-observed executable | Parent refuses child |
| Arbitrary/non-disposable path | Refuse before launching |
| Production singleton/shell source audit | No M11w mount, exactly one existing FileView, guard hard-coded false |

CI additionally reruns M11v process, M11u sealed source, M11t open acceptance gate, M11p replay/crash, and M11d one live writer tests. This is not authorization or native production certification.

## WATCH OUT FOR

- **No durable production owner is now deployed.** The test child uses existing *disposable* M11l journal semantics. A journal writer ID derived from a host session is evidence of correlation, **not** proof the host is trustworthy.
- A process died after the synthetic reservation and before any FileView write. No task JSON was mutated. No claim is made about native `FileView.onSaved` scheduling or physical power loss.
- A PIDFD pins kernel process identity against PID reuse but does not attest dynamic module imports, user-space takeover, or executable provenance. The session nonce is not a signature.
- The OS lock remains advisory, so independent noncooperating task writers are not excluded.
- An interrupted journal must be preserved; do not reboot/rebootstrap the same private fixture to make a test appear passed.
- No `shell.qml`, `ApolloHubTodoStore.qml`, real TASKS data, Quickshell application, local config, SQLite task-data migration, GitHub Projects, or Hospital state was changed.

## CHECKLIST

- [x] Inspect merged M11v source, current main, TASKS ownership and Syntagma rules
- [x] Create separate sealed synthetic child using existing M11l owner bytes
- [x] Bind observed child to session and persisted journal writer ID
- [x] Add pending-stage crash/restart review and refusal regressions
- [x] Add code-only CI, documentation and no-production-mount checks
- [ ] Verify final GitHub CI and independent review
- [ ] Operator review/merge
- [ ] Separate scope for authenticated production host, real-file backup and native callback integration
- [ ] Separate approval for local changes, production activation and eventual SQLite migration

## NEXT

After M11w CI review, the next meaningful boundary is a **production host design review**: define a truly independent trust anchor for the interpreter and journal module, source identity and backup, and the public TASKS/Planner asynchronous writer contract. Do not turn this disposable probe into a production host by relaxing its path check.

## DECISIONS

**Operative:** M11w is a disposable, GitHub-only test slice, using the exact existing M11l journal implementation and observed Linux process/session mechanics.

**Not operative / not authorized:** production writer integration, real data inspection, local writes or restart, PR merge, recovery restoration, SQLite task-data migration, production activation, remote GitHub task writes or live Hospital registration.
