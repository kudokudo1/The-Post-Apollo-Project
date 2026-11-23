# 🏥💜 DOC 1 // Storage-independent C3e trust interface: development and protected-HOLD modes

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM / STAFF:** Universal Connections · Protected C3e Identity · DOC 1, externally Hospital-compatible; live Hospital connection unverified  
**ASSIGNMENT:** Build a bounded, GitHub-only *semantic trust-client interface* that separates the existing development-only SQLite ledger from future independently protected custody.  
**UPSTREAM:** Reviewed and merged C3e [local-to-independent roadmap #2217](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217), [atomic local-ledger test #2224](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2224), original signed history [#2192](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2192), cross-owner handoff [#2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018).  
**STATE:** **CI-only prototype and attack tests**. The protected/remote client is not implemented or installed. No production custodian, signer, storage, networking, service or Sign-In authorization. **PRODUCTION HOLD.**

## IMPLEMENTATION // The basic mechanism

The original local C3e program creates SQLite tables for the *test* current head, test nonce state and signed-history digests. It correctly spends a test challenge and changes a test head in one transaction, but a local actor can still roll back those tables together.

A storage-independent trust client must not assume those SQLite rows are real authority. It should ask a clearly identified backend for specific *semantic operations*: read the current state, issue one challenge, commit a signed next-history proposal, and inspect an uncertain outcome. Eventually, an independently administered custodian could implement this contract after owners approve a protected transport and actual root/host evidence. **The interface shape by itself cannot attest a backend.**

This milestone adds **only**:
- `tests/connections/c3e_release_trust/C3eStorageIndependentTrustBoundary.py`, a test-only client and local adapter, not installed anywhere;
- `tests/connections/test_connections_c3e_storage_independent_trust_boundary.py`, negative/adversarial cases;
- a dedicated GitHub-hosted test workflow and this documentation.

It **does not modify** the existing SQLite ledger, signed-history verifier, C4b gateway, broker, Identity Center, C5, PX/Hospital, Forest or TimeW implementation.

## Modes and authority boundary

| Explicit mode | Allowed in this milestone | Always refused |
| --- | --- | --- |
| **Local Development Only** | Use the existing root-guarded `DevelopmentLedger` fixture adapter to read local test head, issue local test challenge, pass signed test records through original #2192 verifier and local SQLite transaction, and query test outcome. Results clearly say `LOCAL_FIXTURE_VALID_NOT_INDEPENDENT_TRUST`; **every authority flag is false**. | Calling the result operator-enrolled, independent, rollback-resistant, seat-authenticated, C5-consented or production-ready; arbitrary backend injection; real credential/Sign-In permission. |
| **Independent Custodian Required** | Return one static diagnostic `INDEPENDENT_CUSTODIAN_UNAVAILABLE_HOLD` with false flags. | **Any** snapshot read, challenge issuance, signed commit or history lookup through local SQLite; treating an object that claims to be remote as enrolled; service discovery, insecure local fallback or production grant. |

The future operator-approved protected backend **does not yet exist**. This is intentional. There is no “trust_me=true”, provider URL, public key in the repository, auto-generated root, self-enrollment or shortcut that upgrades the local test backend. A protected implementation needs a separately reviewed PR with secure transport, pinned out-of-band public root, actual running-gateway evidence, revocation/current history/nonce custody and atomic crash-safe commit.

### Semantic operations, not a frozen wire protocol

| Operation | Development fixture behavior | Future protected acceptance requirement |
| --- | --- | --- |
| `read_current_snapshot` | Observe local test epoch/head/sequence; returns negative authority flags | Authenticate *current* independent custodian, enrolled root/policy epoch, revoked roles, latest head/sequence and freshness |
| `issue_challenge` | Return disposable random 32-byte test challenge scoped to fake host/release/time | Custodian durably issues a one-use challenge bound to exact audience, host, release, active seat and independently current head |
| `commit_signed_history` | Reuse unchanged signed verifier and atomic local nonce+head transaction; success is test-only | One protected serialized spend+head advance, signed terminal outcome and independent rollback/fork resistance |
| `lookup_terminal_outcome` | Read local `issued` or `consumed` state after an uncertain ACK | Authenticated query of protected terminal result. No automatic retry of uncertain commit |
| Enrollment revocation | Always refused | Separate operator-approved protected root/revocation/rotation authority |
| Production admission | Always refused | Requires separate C3e real-root, DOC 2 installed host evidence, C5 user consent and Identity Center command owner gates |

The names here express the **desired semantic responsibilities**, not owner-approved native API field names, cryptographic payload format, remote method names or network ports. The future remote custodian may implement a different adapter, but it must never interpret fixture statuses as legitimate protected evidence.

## VERIFY // Executable threat checks

The CI suite tests that:
- locally issued challenges, test history observations, signed test commits and terminal lookups remain clearly labeled and return no trust grants;
- malformed/forged or extra authority fields in local snapshots/results are rejected before the caller can treat them as valid;
- local signature tamper, old-head/replay, lost ACK, unknown nonce and production/revocation attempts fail closed or return a diagnostic only;
- protected-required mode rejects local backend injection and **never invokes a local SQLite method**;
- a mock object with `certified=true` and a remote-looking string cannot establish protected custody;
- a previously spent test challenge can still be replayed after a **full rollback of the local database image**, yet the interface continues returning only false authority flags;
- original local ledger, signed-history, operator signer enrollment and AF/Z test suites remain unchanged and green;
- broker `readonly property bool credentialActionsEnabled: false` remains unchanged.

The workflow runs only in disposable hosted GitHub CI. Source-level flag assertions are secondary to adversarial behavioral tests; neither is real native deployment acceptance.

## HOW TO USE

There are no operator desktop steps. The new code lives exclusively under `tests/`; it has no independent key store, network transport, daemon, signing private key or machine installer. A developer running the new workflow sees the behavior of the local adapter and a strict protected-mode refusal.

When the NAS or another Post-Apollo computer becomes ready, the operator must select an **independently administered security custodian** and approve a separate implementation for its authenticated transport, key enrollment and recovery. Then DOC 1 can add a separately reviewed protected adapter without rewriting the original signed-history verifier. DOC 2 owns the actual Silverblue process/release/receipt signer evidence. C5/Identity retains consent and action boundaries.

## WATCH OUT FOR

- **No production fallback.** Loss of independent custody must always yield HOLD/UNKNOWN, never a silent switch to local test SQLite.
- **A second database is not automatically independent.** A writable NAS mount or identical administrators/backups can restore state alongside the desktop.
- **Valid test signatures are not authentic operator enrollment.** The local verifier's caller-pinned keys remain synthetic.
- **CI guard environment variables are not hardware attestation.** A privileged operator could spoof `GITHUB_ACTIONS`; test fixture isolation plus the absolute prohibition on production use, rather than an env var alone, defines this milestone.
- **No automatic migration of development authority.** Real cutover requires fresh protected root/epoch, invalidation of all local challenges, independently current head and recovery acceptance.
- **Purpose separation.** Forest, Hospital, TimeW and C5 cannot borrow an Identity root or one-use grant merely because a future custodian might share a computer.

## CHECKLIST / NEXT

- [x] Recheck merged #2217 and #2224, original C3e-R and #2192 source, Syntagma protocols and C3e/C4b ownership.
- [x] Implement a **local development adapter only**, with a blocked protected-required mode.
- [x] Add adversarial tests for no hidden fallback, spoofed adapter claims, invalid snapshot, replay/rollback and uncertain commit.
- [ ] All exact-head GitHub CI tests PASS and Nurse 2 reviews the code **before authorized merge**.
- [ ] Operator alone selects eventual real host/custodian, approves enrollment root and recovery ceremony.
- [ ] Separate protected transport + actual root/host proof, multi-process/machine nonce and crash/rollback tests, C5 and Identity approvals.

## DECISIONS

The operator already accepted the **development sequence** “local test ledger now → independently protected custodian when the NAS/other computers exist.” This milestone implements the *no-trust promotion* boundary, not a real remote backend. All future protected authority, migrations and production Sign-In remain **HOLD**.
