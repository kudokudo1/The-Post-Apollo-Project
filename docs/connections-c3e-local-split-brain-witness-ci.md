# 🏥💜 DOC 1 // Two cloned C3e local witnesses can disagree without a protected arbiter

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / STAFF:** Universal Connections · Protected C3e Identity / DOC 1, external Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT:** Demonstrate why two independently writable *local development* history copies cannot settle a disputed protected history fork  
**STATE:** Source and disposable GitHub CI only · **PRODUCTION SIGN-IN HOLD**

## IMPLEMENTATION

Two files do not share a SQLite transaction lock if they live in different directories. If both start with the same old history head, each can accept a different *locally valid candidate* extending that predecessor. Each file can then report "my local head matches my own commit," even though the results **disagree**. Unlike the single-store conflict check in merged [DOC 1 #2334](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2334), neither store's individual compare-and-swap can determine the correct **global** next head.

This milestone adds a small pure, **fail-closed classifier** of two pre-existing `C3eSplitStoreRollbackWitnessCI` observations, and a disposable Linux test that creates two copies of its existing shadow database in separate `/run/c3ew-ci-*` root-only directories. The implementation does **not** change the existing ledger, shadow writer, C4b gateway, C5, Identity command, SwayPX or TimeW source.

The test forks two actual local writer processes and supplies each an *intentionally synthetic, unverified* but well-formed next-head candidate against the same predecessor. With no common transaction domain, both commit successfully, yielding two conflicting sequences that look self-consistent locally. No signed history from independent enrolled machines is created or claimed.

| Input to the new classifier | Result | Authorized action |
| --- | --- | --- |
| Both locally match but **same sequence, different heads** | `COMPETING_EQUAL_SEQUENCE_DIFFERENT_HEADS_UNKNOWN_HOLD` | None |
| Both locally match but have **unequal sequences** | `UNEQUAL_SEQUENCE_NO_AUTHORITATIVE_WINNER_UNKNOWN_HOLD` | None |
| Both locally match with **identical heads and sequence** | `MATCHING_UNENROLLED_LOCAL_HEADS_STILL_UNKNOWN_HOLD` | None |
| Either local candidate's own guest vs shadow data is inconsistent | `INCONSISTENT_LOCAL_WITNESS_OBSERVATION_UNKNOWN_HOLD` | None |
| Schema, denial flags, status or relation are malformed/forged | Fixed `Refused` | None |

Even two identical copies do not establish separate operator enrollment, physical administration, authenticated source origin, a protected challenge spend, current release/revocation policy, or a protected terminal receipt. Because reports are caller-supplied, a single caller can simply duplicate a report to impersonate two agreeing witnesses; this also returns HOLD.

All outputs set `winner=None`, `safeActions=[]`, all inherited protected authority flags and extra quorum/receipt/settlement/retry/Sign-In flags strictly `False`, and `UNKNOWN_HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED`. Attempting to invoke `choose_protected_winner` always refuses. This is not an election algorithm or a future quorum wire format.

## HOW TO USE

No workstation, NAS, key, service or production commands. All mutable DB files exist only on GitHub-hosted disposable Linux runners during CI, using the original #2334 test-only writer and earlier root-owned local C3e fixtures.

The four new additive DOC 1 files are:

- `tests/connections/c3e_release_trust/C3eSplitBrainWitnessDisputeCI.py` (read-only, pure classifier)
- `tests/connections/test_connections_c3e_split_brain_witness_dispute.py` (22 adversarial cases)
- `.github/workflows/connections-c3e-local-split-brain-witness-ci.yml`
- This document.

## VERIFY

The 22 tests include two forked writers committing conflicting synthetic next heads, agreement with separately updated copies, duplicate-report impersonation, advancing one side only, different guest/shadow heads, wrong schema/status/next, missing/extra fields, positive authority, bad sequence/head type, contradictory claimed relation, explicit production winner refusal and a two-copy rollback restoring the same **obsolete** head.

The dedicated workflow additionally runs **162 inherited tests**: 32 custodian cutover +30 IPC non-settlement +24 split-store rollback +20 C3e/C4b signed-denial shadow +28 storage-boundary +28 original SQLite ledger. Other standard Grammar, offline root-pinned admission and Fedora fake-signed-RPM workflows must be checked at the exact PR head. Nurse 2 must independently inspect source and raw logs before operator merge disposition.

## WATCH OUT FOR

- Two local process outputs do not represent authenticated independent trustees or quorum votes. **The experiment deliberately has no external root or voting membership.**
- The two candidate heads are synthetic and **not** signed, enrolled or verified proposals. Their separate commits prove only local storage independence, not cryptographic history correctness.
- Higher local sequence, a matching signed denial, caller-supplied timestamps or two identical replies do not resolve an independently protected fork. Never pick the "latest" one based on untrusted input.
- A real future NAS/other-computer custodian must have separately approved administrative/key/storage/backup ownership, authoritative current head and revocations, strict per-purpose one-use challenges, authenticated native producer, atomically settled signed receipts, and a reviewed policy for partition/restore/split brain. The user approved **local development first, separate protected hardware later**, not a particular custodian, automatic promotion or production cutover.
- DOC 2 C4b owns actual Silverblue host evidence; DOC 5 owns TimeW C5; DOC 6 owns Identity command semantics. This fixture does not expand DOC 1's authority into their lanes.

## CHECKLIST / NEXT

- [x] Confirm PR #2334 merged `257834ac` with 4/4 CI and correct its outstanding Nurse 2 review request to retrospective.
- [x] Add pure two-report HOLD classifier and real forked copied-ledger disagreement fixture.
- [ ] Verify exact-head new + inherited GitHub CI, Grammar, root admission and Fedora workflows.
- [ ] Obtain independent Nurse 2 exact-head source/CI review and operator disposition before merge.
- [ ] Real independently authenticated root/current history/nonce and protected conflict recovery remain future operator-custodian decisions and native acceptance tasks.

## DECISIONS

No authoritative voting, remote transport, production signing key, real protected custodian or Sign-In activation is created here. A **locally matching history** is not a **trusted current history**, and neither one-side nor two-side local consensus may confer permissions. **PRODUCTION SIGN-IN HOLD.**
