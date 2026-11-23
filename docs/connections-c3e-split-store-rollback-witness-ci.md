# 🏥💜 DOC 1 // Two disposable local SQLite stores are not independent trust custody

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF:** DOC 1, external Hospital-compatible, live registration not verified  
**ASSIGNMENT:** Test what a separately retained history checkpoint can and cannot establish when the C3e guest-local ledger is restored  
**STATUS:** Development-only / source and disposable hosted CI / **PRODUCTION SIGN-IN HOLD**

## IMPLEMENTATION

A SQLite database is a file containing pages and a transaction journal. A signed C3e local-history update changes the guest's head/sequence and marks the challenge spent. Restoring an old copy of **that one file** can undo the observable spent state. Prior reviewed #2282 and #2296 demonstrated this. The next question is what happens when another local process retains **a second checkpoint in a separate file** that the guest restore does not automatically replace.

This milestone creates a *test-only* second SQLite database in its own root-owned, mode-0700 `/run/c3ew-ci-*` directory, separate from the original existing C3e root-owned development ledger in `/run/c3er-ci-*`. It uses the unmodified `C3eStorageIndependentTrustBoundary` and `DevelopmentLedger` source. The new shadow comparison module has four strict operations:

1. `initialize_ci_only`: initialize a **non-authoritative** second database with the original local snapshot. This is not an out-of-band root enrollment or protected genesis ceremony.
2. `compare_ci_only`: distinguish `MATCH`, stale guest sequence, a same-sequence differing head, or guest ahead of shadow. No result can grant trust, even a match.
3. `advance_ci_only`: test an SQLite `BEGIN IMMEDIATE` compare-and-swap on the shadow's previous head and sequence. Two forked callers proposing different next heads from the same predecessor cannot both update the shadow file. This **does not authenticate the proposed new head**, which is supplied by the caller.
4. `protected_admission`: unconditionally refuse. A second SQLite file is not an operator-enrolled trust custodian.

The tests use fresh Linux processes to read and update the shadow database. If the original local guest ledger commits and the shadow advances, **restoring only the guest database** is detectable as a stale guest head. If the same operator can restore **both databases** together, they agree again on the old checkpoint: two databases do **not** create independent rollback resistance. After restoring the guest alone, the original synthetic signed history can even be replayed to the same head, again producing a `MATCH` without authentication.

The source and tests are not shipped to a Linux host service. They contain no network listener, production signing key, elected root, real guest/seat measurements, durable protected terminal receipt or any actual independently administered NAS machine. All output authorization flags are hard-false, with `HOLD_NO_AUTOMATIC_RETRY_OPERATOR_ENROLLED_CUSTODIAN_REQUIRED`.

## HOW TO USE

No operator workstation steps or NAS configuration. The only write operations are commits of four new source/CI/docs files to an isolated GitHub branch, and writes to temporary GitHub-hosted disposable databases during CI.

**Four additive DOC 1 files:**

- `tests/connections/c3e_release_trust/C3eSplitStoreRollbackWitnessCI.py`
- `tests/connections/test_connections_c3e_split_store_rollback_witness.py`
- `.github/workflows/connections-c3e-split-store-rollback-witness-ci.yml`
- This document

The test-only witness writes a candidate head without verifying a new signature, authentic signer roster, host process, challenge purpose or one-use spend. That missing authentication is intentional and must never be treated as a complete future protected protocol.

## VERIFY

New 24-case suite tests: initial diagnostic-only match, a real existing local signed commit, shadow-ahead and guest-ahead divergence, original local DB restore, replay that re-matches, stale duplicate/fork refusal, forged positive fields, swapped source and malformed sequences/digests, no auto-create, unsafe directory and symlink refusal, actual child-process restart/reads, two concurrent child writers competing over one previous head, child SIGKILL after shadow commit but before reply, and a decisive **restore-both-databases** demonstration that makes old state appear matched again.

Dedicated GitHub CI also reruns **201 inherited C3e/C4b tests**: 32 cutover + 30 IPC non-settlement + 18 C4b raw nonce + 28 C4b controller challenge + 20 C3e/C4b shadow + 17 real SIGKILL + 28 storage boundary + 28 local ledger. Exact-head Grammar, offline root-pinned release and fake RPM/SELinux guest checks are additional required evidence. Nurse 2 independently reviews the exact head before any operator-controlled merge.

## WATCH OUT FOR

- **Not actually independent:** Both files reside on one disposable runner and are writable by its root administrator. This experiment models split storage but cannot establish independent administration, backups, antirollback or hardware trust.
- **Not attested:** The comparison inputs originate from a local test snapshot. Even a matching head is not an authenticated source of truth, and the shadow compare-and-swap accepts unverified synthetic candidate heads.
- **Not full crash resilience:** `SIGKILL` after `COMMIT` demonstrates acknowledged-versus-persisted uncertainty, not real power-loss durability. An independent terminal receipt, authenticated outcome lookup and anti-fork recovery remain missing.
- **Not a production authority transfer:** The operator authorized local development now and independent protected hardware later, **not** a particular NAS, admin, root fingerprint, wire format or production enrollment. DOC 2 retains C4b actual running gateway source/boot/seat, DOC 5 C5 and DOC 6 Identity-native command ownership. The original C3e Identity-only challenge must not be reused for Hospital, Forest or TimeW.
- **Still HOLD:** All results, even apparently successful compare-and-swap or byte-identical states, set protected/root/history/host/receipt/consent/credential/retry/Sign-In permission fields false.

## CHECKLIST / NEXT

- [x] Confirm Syntagma and Hospital rules, current GitHub main, completed DOC 2 standby, reviewed DOC 1 #2296 and accepted local-first roadmap.
- [x] Add separate-process, two-file witness comparison with intentional same-host rollback counterexample.
- [ ] Verify exact-head new/inherited CI from raw GitHub logs.
- [ ] Obtain independent Nurse 2 scoped source/security review and operator merge disposition.
- [ ] Under separate future operator approval, select custodian host/administrator, purpose-specific enrollment root, current independently protected signer/challenge/history, revocation and recovery policy.
- [ ] Native DOC 2 process/seat and C5/Identity security acceptance; **PRODUCTION SIGN-IN HOLD**.

## DECISIONS

This is a **local development experiment**, not an accepted production custody interface. The future independent custodian must be isolated in administration, keys, immutable/current history, backup and recovery, not merely placed in another database, container or directory. No production Sign-In activation, local host mutation, key provisioning or merge was authorized.
