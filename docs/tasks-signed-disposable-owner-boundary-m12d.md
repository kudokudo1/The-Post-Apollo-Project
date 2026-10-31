# 🏥💜 TASKS M12d // Signed Synthetic Release → Observed Disposable OS Owner

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M12d *isolated* signed release / executable process / disposable source integration test  
**DOCTOR //** External Hospital-compatible ChatGPT worker, not live Hospital-registered  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED BASE //** GitHub main `2e4d121b8cdc237a9819be6a9c03581f6a18e9de` (October 31, 2026); recheck current head before future work  
**CLASSIFICATION //** **TEST-ONLY SYNTHETIC PROCESS AND SQLITE JOURNAL**. No production task data, host, QML, local installation or activation.

## IMPLEMENTATION

M11y verifies Ed25519 signed artifacts against separately supplied public trust inputs, M11u/M11v inspect sealed script bytes and Linux PID/executable correlation, M11w runs a real child that holds an existing **disposable** M11l source/journal owner. M12c describes the unresolved root-custody and authorized-signer governance. **M12d connects the working test mechanisms without giving the test harness production permissions.**

### Concrete data path

1. **Disposable signer/test identity:** `tests/tasks/test_task_signed_owner_boundary_m12d.cjs` creates an owner-private fresh directory under `/tmp/m12d-root-*`, with exactly `m11y-release-copy` signed release files and an `m11l-tasks-copy/todo-copy.json` initialized to one *exact* known `M11W_TEST_0` task. Ed25519 keys are ephemeral process-memory test keys. Its public key, SPKI fingerprint and release minimum generation are separately passed to the M11y verifier by **the same test runner**. This is **not independently provisioned production trust**.
2. **Actual signature verification:** the untouched M11y `verifySyntheticRelease()` checks exact signed canonical manifest, Ed25519 signature, generation, private file metadata and three SHA-256 digests, then returns captured byte buffers for `synthetic-host.py`, `synthetic-owner.py` and `synthetic-interpreter.bin`. No released file path is subsequently executed.
3. **Bounded test handoff:** Node transmits only base64-encoded captured bytes to the new `TaskSignedOwnerBoundaryM12d.py` via a bounded JSON stdin message. The Python runner **does not cryptographically authenticate that message** and a caller could spoof its `signatureVerified:true` assertion. Therefore it additionally refuses host and owner source bytes that do not equal the **exact reviewed-in-test-checkout** M11w child and M11l module bytes. These checkout bytes are an extra CI fixture allowlist, **not a real independent trust root or a production signature verifier**.
4. **Signed interpreter descriptor:** the signed `synthetic-interpreter.bin` contains only `M12D-SYNTHETIC-INTERPRETER-SHA256:<digest>` for the fixed `/usr/bin/python3`. Python reuses M11v's actual pinned interpreter check: root-owned interpreter and ancestor requirements, source digest readback, and exact kernel executable inode observation when the child launches. A signed descriptor is not proof that a production OS or signer is trustworthy.
5. **Sealed process + durable disposable owner:** Python passes captured host and owner module bytes through existing M11w `attach_synthetic()`, which seals two Linux memfds, creates a child PIDFD, validates `/proc/PID/exe`, and binds the child session to the actual `m11l-tasks-copy/gate-review.db` journal writer/epoch. This reuses the **original M11l strict test path checks, backup, lifetime flock and SQLite stage history**, unchanged.
6. **Restricted source:** before launching, the test checks the exact `/tmp/m12d-root-*/m11l-tasks-copy` directory structure, owner-only mode, and exact synthetic `todo-copy.json` seed bytes. The M11w child independently restricts source to `m11l-tasks-copy/todo-copy.json` and can reserve only a synthetic `M11W_TEST_0` task, not write it.
7. **Crash/restart and source preservation:** `NEW_RESERVE` creates a synthetic journal reservation and independently checked byte-identical backup but **does not save the candidate JSON**. Process exit releases its lifetime lock. A separate `EXISTING_CHECK` process opens the same disposable journal with a fresh session, advances epoch, enters `RECOVERY_REVIEW` and refuses a new reservation. Source and backup remain unchanged.

### Negative matrix

| Test | Expected refusal or preservation |
| --- | --- |
| Real Ed25519 signature, approved *synthetic test key*, fixture-matching bytes | Observed child/PIDFD and persisted disposable journal reservation |
| Fresh process after original owner leaves | New epoch, review-only, cannot reserve again |
| Missing/wrong external test key or candidate-supplied public key | M11y refuses before child launch |
| Host file modified after signing | M11y hash mismatch |
| Attacker signs modified host with *test signer* | Python rejects unreviewed fixture bytes even if Ed25519 verifies |
| Attacker signs modified owner module | Refuses before executing owner module |
| Wrong signed interpreter binary digest | M11v pinned executable check refuses before child launch |
| Malformed signed interpreter descriptor | Refuses |
| Old signed release generation | M11y anti-rollback floor refuses |
| Wrong source directory or modified synthetic seed | Refuses without journal creation |
| Forged `signatureVerified:false` handoff | Refuses |
| Production singleton | One existing `FileView`, guard false, nine mutation routes, no M12d mount |

### Trust boundaries and limits

**EVIDENCE WHEN GREEN:** In a Linux CI runner, a signed **synthetic** release fixture is verified; captured bytes are handed to a separate subprocess; M11v/M11w inspect and run a pinned fixed OS interpreter, sealed host/owner byte buffers, observed child process and disposable SQLite journal owner; a synthetic reservation survives parent/child exit and a new owner enters recovery review.

**NOT PROVED:** the real signing root, trusted signer identity, authenticated Node→Python handoff, signed code review outside checkout, actual source path authority, runtime isolation against a malicious parent, malicious same-user writers, OS compromise, exact FileView/native callback attribution, real task source backup, durable JSON settlement, rollback-resistant hardware persistence or power loss. M12d's `signatureVerified` JSON flag is **not a trusted security assertion**; CI combines the M11y verified buffers and Python fixture-byte equality to test mechanics. Do not reuse this parent entrypoint or its marker as a production trust decision. A signed malicious module with a permitted marker is unsafe to execute unless independently reviewed and restricted, hence fixture exact-match rejection.

## HOW TO USE

No Fedora machine commands or Post-Apollo UI changes. GitHub Actions runs on Ubuntu with Node 22 and Python. In a separate disposable Linux checkout:

```sh
node --test tests/tasks/test_task_signed_owner_boundary_m12d.cjs
```

This executes only the fixed, reviewed synthetic child and synthetic M11l owner under a temporary directory; no real tasks or external services are read.

## VERIFY

- Confirm branch contains only the new Python runner, Node end-to-end tests, this doc and narrow GitHub Actions workflow; all previous M11u/v/w/y, M12c policy tests and production QML/host code remain untouched.
- CI runs M12d end-to-end and earlier M11w/M11y/M12c/M12b/M11t/M11d regression suites. CI green is a synthetic/mechanical PASS, not production trust acceptance.
- Confirm live TASKS still has one `FileView`, nine `stage(TodoPolicy.*)` methods, and `readonly property bool guardedWriterEnabled: false`.
- The original M11t **nine production gates remain OPEN**; M12b **ten evidence topics remain OPEN**; actual M12c trust authority still **not selected**.

## WATCH OUT FOR

- M12d increases integration confidence **only for disposable fixtures**. Real host signer custody and release provenance must be decided by operator before even a disabled production host is built.
- The Node test makes a signed **descriptor of a real system interpreter SHA**, not an immutable signed operating-system image. M11v independently checks this interpreter as best it can; compromised root/runtime is outside scope.
- If the Python handoff is forged, the `signatureVerified` flag means nothing. The fixture-source allowlist and strict directory contract keep the synthetic test bounded, but this is **not** usable as an authenticated production message bus.
- SQLite remains **journal metadata only**. Real task data continues to be stored by the existing Quickshell `FileView`; no second task writer exists.
- A synthetic journal reservation is not equivalent to user-data save confirmation. Native `FileView.onSaved`, UI recovery overlay and async mutation API remain separate unresolved work.
- Never widen M11l/M11m test-copy restrictions or connect the Python test runner to a production source path.

## CHECKLIST

- [x] Verify M12c landed; current main, ownership and Hospital rules
- [x] Reuse original M11y signing and M11v/M11w sealed process/journal mechanics
- [x] Add bounded signed captured-byte handoff and interpreter descriptor
- [x] Restrict to private exact-seed synthetic TASKS source
- [x] Add genuine signed-bundle negative cases and restart/recovery
- [x] Add source-only CI checks and Hospital handoff
- [ ] CI verified and independently reviewed
- [ ] Operator review/merge
- [ ] Separately decide production root custody, source permissions, native callback fencing, UI API, rollback and activation

## NEXT

After M12d review, a future **isolated native callback attribution experiment** could test how to correlate FileView callbacks and host settlement without modifying the live TASKS singleton. A production-shaped QML integration remains **outside this assignment** until release trust authority and native evidence are independently approved.

## DECISIONS

**Implemented:** GitHub-only cross-language signed synthetic release → sealed Linux child process → real disposable SQLite owner integration test.

**Proposed, still OPEN:** production trust-root owner and signer, independent verification deployment, actual-source authority, native callback fencing, UI API and error-state overlay, protected writer activation.

**Not authorized:** real TASKS file inspection, user data writes, Fedora changes, live Quickshell restart, production host install, signing authority establishment, PR merge, SQLite task-data migration, automatic restoration or live Hospital registration.
