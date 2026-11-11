# MACHINE // Protected archive destination isolation and rollback fixture

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // Hospital-compatible external DOC; live Hospital attachment not verified
ASSIGNMENT // Prove a future protected archive destination can be separated from a normal browser user and failure cases preserve originals
SOURCE // Merged MACHINE protected-metadata deny-only contract, with PR #1898 read-only migration source preflight still open/draft at branch creation
SCOPE // Disposable CI-only root fixture and tests. This is NOT a migration implementation.

## IMPLEMENTATION

The protected metadata broker is still **deny-only**. Browser-side native hosts cannot reach permanent protected archives. A future deployment requires separate service ownership of protected files so another process under the browser account cannot simply read them from disk.

This PR introduces **one test-only privileged Linux script**, `tests/timew/test_machine_protected_destination_rollback.py`, and extends the existing MACHINE CI workflow. It does not create any reusable migration library, service, RPM, unit, target root setting, host manifest, permission grant, authentication interface or user command.

On the disposable GitHub runner, root creates a strictly recognized `/tmp/machine-destination-ci-*` fixture. It reserves three **unassigned numeric Unix UIDs** only for subprocesses in this fixture: an ordinary browser UID, a distinct non-root protected-service UID, and a foreign UID. No system users are created.

The fixture has a 0700 source owned by the browser UID with one syntactically valid synthetic sealed record, and a separate 0700 destination owned by the protected UID with a preexisting 0600 sentinel record. The test directly asks Linux to enforce file access under these identities. It demonstrates that the browser and foreign UID cannot read, list, append, unlink, chmod or create files in the protected directory, and the protected service UID cannot directly read the browser-private source.

A **root-owned test harness only** models a possible future protected transfer:
- Check the source directory is owned by the browser UID, mode 0700, and has no symlink substitution.
- Read only one expected UUID `*.json` record through descriptor-relative `O_NOFOLLOW`; refuse if owner, mode 0600, link count, size, structure or exact SHA-256 differ.
- Verify protected destination ownership/mode. Stage existing opaque encrypted bytes under an exclusive temporary filename, change staged file ownership to the service UID, fsync, then recheck the source before publishing with `link` (no replacement of existing filenames).
- Simulate errors both **before publication** and **after publication**; clean up only the newly staged/published inode if it is still the one the fixture created. Never unlink or move the original source. Verify the previously present destination sentinel is byte-identical after every case.
- Simulate source mutation between the first and second source reads, missing/wrong digest, hardlink, source symlink, wrong owner/mode, preexisting conflicting target, and repeated import. All fail closed without overwriting an existing record.
- Show one successful **synthetic-only** transfer where exact ciphertext bytes and record UUID are preserved, the target is 0600 and owned by the protected UID, and kernel refusal persists for the browser and foreign UIDs.

The test deliberately does NOT expose a `migrate` CLI. The transfer function is internal to the CI file and is gated on root and an exact temporary fixture shape.

## VERIFY

GitHub Actions runs `sudo -n python3 -B -I tests/timew/test_machine_protected_destination_rollback.py` on an ephemeral Ubuntu 24.04 runner. The real process identity tests use `setgroups`, `setresgid`, `setresuid` and subprocesses. They do not mock `PermissionError`. Any unavailable sudo privileges or collisions with assigned fixture UIDs must fail rather than downgrade the test.

The existing protected metadata broker workflow also reruns kernel `SO_PEERPIDFD` lifecycle and distinct-UID archive denial, actual `setsid` session cancellation, slow-client absolute request deadlines, and encrypted archive/WebCrypto synthetic regressions.

No real Brave session, device file, normal account data, production archive, service registration or desktop installation is used.

## HOW TO USE

**No UI or workstation action exists for this milestone.** This is a repository CI test only. It is not safe or supported to copy the root-owned test harness into an installed migration utility or to run it against personal archives.

For future production work, obtain separate operator approval for protected account creation, backup, encrypted-only source and target copy, independent verification, cleanup/rollback, and service activation. Do not infer authorization from a CI PASS.

## WATCH OUT FOR

- The root-owned simulation is **not proof that an unprivileged transfer broker exists**. A production transfer mechanism, authority checks and kernel security labels must be designed and reviewed separately.
- The simulation does not reproduce sudden power loss, entire-disk failure, an adversarial process concurrently rewriting or replacing source/destination, or fsync errors. A published record followed by an uncertain error requires operator inspection, not blind deletion.
- A same-UID attacker can still reach the **existing ordinary-user source**, even when the destination is correctly protected. A live migration needs backup, strict custody, reviewed access, and an explicit operator-approved source-retirement/rollback decision.
- File permission isolation is not AES-GCM authenticity and does not prove a trusted Brave client. No passphrase is entered; all fixtures are synthetic ciphertext with structurally valid envelopes, not production encrypted browser sessions.
- No real C3e independently verified host/process/seat witness or purpose-bound C5 one-use consent/replay ledger is connected. Metadata broker ingress remains **deny-only**.
- The branch is intentionally independent from still-draft PR #1898. Source inventory preflight must not be treated as landed in main until independently verified merged.

## CHECKLIST

- [x] Check Syntagma, MACHINE ownership, current main and PR #1898 state
- [x] Implement disposable CI-only separate-UID source/destination fixture
- [x] Prove browser/foreign direct access denial with actual kernel permissions
- [x] Simulate no-overwrite ciphertext staging, injected failures, source mutation and exact rollback
- [x] Preserve sentinel, original source, permissions and later service-owned successful copy
- [ ] Exact-head GitHub CI and independent Nurse 2 security review
- [ ] Operator source merge decision and independently authorized local deployment planning
- [ ] Reviewed encrypted backup and protected account/target design with SELinux/policy evidence
- [ ] Authorized persistent migration, C3e live host/seat, C5 one-use consent
- [ ] TimeW encrypted restoration, reopen/dedup and multi-monitor placements

## NEXT / DECISIONS

Next MACHINE development can establish **read-only destination-readiness checks** with a trusted supervisor-provided root, audited provenance and rollback plan, once this independent test is reviewed. Do not install anything or touch real archives without a new explicit operator approval. MACHINE retains its TimeW code; Connections C3e and C5 retain their separate security work. No production files, system accounts, user directories, browsers or running services were modified.
