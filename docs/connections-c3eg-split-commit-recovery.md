# 🏥💜 Universal Connections // C3e-G split-commit recovery

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release-trust recovery  
STAFF ROLE // Nurse 2 · NRS-2 (operator-assigned; externally Hospital-compatible; live Hospital registration not verified)  
ASSIGNMENT // C3e-G safe handling of client/witness partial commits after process death  
BASE // `237eda15e8173234883dafdd7cb0d0b64b0b1061`  
SCOPE // GitHub-only new files, disposable simulated signing authority and GPG/SQLite tests. No workstation, real signing keys, services, credentials, or production activation.

## IMPLEMENTATION

C3e-F PR #1515 is merged at `877eb00d` and its [independent post-merge security audit](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1515#issuecomment-6723201679) confirmed **two independently committed SQLite databases**: C3e-C commits the client release first, then C3e-F commits the witness release. A process crash between commits may leave client at version 9 while witness remains at version 8. Existing C3e-F had no durable intent or explicit recovery protocol.

C3e-G is a **new opt-in CI-only protocol**, without changing C3e-F or any live caller:

1. `tests/connections/c3e_release_trust/C3eSplitCommitRecovery.py` explicitly adds a single-row pending-intent journal **inside the existing synthetic witness SQLite database**. Initialization refuses mismatched client/witness floors, preexisting journal or missing ledger. It never silently repairs, deletes or recreates trust.
2. For a new release, the caller must present a **fresh C3e-D challenge-bound signed authority proof** (using actual GPG) and exact C3e-A signed policy, manifest and package bytes, which are copied into a bounded, non-symlink temporary snapshot before verifying. It checks enrolled witness node, release root and authority signer pins.
3. The witness first durably **PREPARE**-commits the intended next release tuple (policy epoch, sequence, policy SHA-256 and artifact SHA-256), the previously recorded **client** tuple, and the exact signed authority floors. The client then uses unchanged C3e-C to commit the target. The witness finally checks the target client state, advances its own floor and deletes the pending intent **in one final local SQLite transaction**. This does **not** make both SQLite databases a single atomic transaction.
4. After an interruption, a normal new submission refuses while the intent remains. **Explicit recovery only** uses a **new random challenge and fresh signed authority statement**, rechecks exact signed release snapshots/hashes, required identity pins and the original authority floor. If client still equals the recorded previous tuple, it can complete client admission; if client already equals the recorded target tuple, it finalizes witness only. Any other client state, changed release, higher authority floor, missing ledger, invalid signature or mismatched identity fails closed; it never resets floors or throws away the pending evidence automatically.
5. `test_connections_c3eg_split_commit_recovery.py` uses real C3e-E subprocess signing fixtures and OS child-process termination with `os._exit(77)` immediately after each committed phase. Test cases cover: process death after PREPARE, after client commit, and after witness commit; successful signed recovery; rejection of untrusted/new candidates or replay; simulated witness final-commit failure; missing client/witness; corrupt/missing recovery schema; untracked client-ahead state, conflicting artifact hash, wrong node and preservation of production deny-only source.
6. The new workflow `.github/workflows/connections-c3eg-split-commit-recovery.yml` runs those tests along with all prior C3e-A through C3e-F release-trust regressions and the C2n permission tests. Existing C3e-F source, real Fedora guest/RPM, the separate C4b Silverblue worker's files, and production QML/JS remain unchanged.

### Recovery state transitions

| Observed state | Allowed behavior |
| --- | --- |
| No intent, matching floors | New signed release may be PREPARED |
| Pending, client still at PREPARE's prior tuple | Explicit, freshly signed recovery replays exact candidate and commits client, then witness |
| Pending, client already at intended target tuple | Explicit, freshly signed recovery confirms target and commits witness, clearing intent |
| Pending, conflicting release / authority floor / client state | Refuse, retain intent and evidence for operator decision |
| No pending but client ahead of witness | Refuse untracked split; never silently infer an authorization |
| Missing/corrupted witness or client state | Refuse; never auto-bootstrap |

## HOW TO USE

No operator desktop action. The new workflow runs in GitHub-only disposable test environments with synthetic signing identities and three separate SQLite files. The API is not connected to a production QML broker or actual rpm-ostree installation. The test intentionally uses a synthetic checkpoint hook to make child processes die between the durable stages.

### Checkpoint pointers

- Prior C3e-F source: `tests/connections/c3e_release_trust/C3eRollbackWitness.py`
- New recovery: `tests/connections/c3e_release_trust/C3eSplitCommitRecovery.py`
- New test: `tests/connections/test_connections_c3eg_split_commit_recovery.py`
- GitHub workflow: `.github/workflows/connections-c3eg-split-commit-recovery.yml`

## VERIFY

At exact PR head, require:

- [ ] New C3e-G actual child-crash/restart tests and signed reconciliation tests pass.
- [ ] Crash after intent, client or witness commit returns correct observable state.
- [ ] No automatic new admission when intent is pending; no recovery without a new signed proof.
- [ ] Signed recovery can complete client-old or client-target state but cannot accept a different candidate, altered manifest, changed authority floor, wrong identity, broken SQLite state or replay.
- [ ] Failed witness commit leaves pending intent; signed retry completes.
- [ ] Existing C3e-F/E/D/C/A and C2n denial tests pass.
- [ ] Real Fedora signed-RPM and Meta Apollo Grammar regressions pass on the PR head.
- [ ] Independent security review and operator disposition remain separate from the developer checkpoint.

## WATCH OUT FOR

**This is not a distributed atomic transaction**, a hardware-backed monotonic counter, a real independent witness, a secure remote network or a production recovery service. It does not make two separate SQLite commits physically indivisible. It implements a **durable and explicitly reconciled partial-commit protocol** under a narrow simulated crash model with intact and trustworthy local databases and a still-available signing authority. A power outage or storage device failure may have failure modes beyond a child process killed by `os._exit`; no real disk-failure fault injection, filesystem-fsync boundary audit, or remote two-phase commit is included.

A privileged attacker may alter, replace or restore the client, authority, witness **and pending intent** together. The C3e-F security audit already proves complete shared rollback remains possible. The release authority's signature authenticates its reported floors, not its underlying true state. The real operator-controlled trust root, separately administered witness, anti-rollback source, key custody, authenticated clients, root/signer rotation, remote recovery ceremony and partial-database-corruption restoration policy are still undecided.

There is **no automatic recovery** for a pending operation when the authority has moved to a different release floor or when the original signed release bytes are unavailable. That case intentionally requires explicit operator-supervised reconciliation with an independent protected history; do not bypass it by resetting the ledger or accepting a lower floor. The prototype does not guard against a concurrent legacy C3e-F writer that ignores the new intent protocol, and does not provide a production cross-process service lock. The supplied test fault hook must not be interpreted as a production RPC.

No real credentials, provider APIs, active desktop components, service activation, native Silverblue installation or signed production release authority is changed by C3e-G.

## CHECKLIST

- [x] Verify latest GitHub and Syntagma AGENTS/Hospital permissions, C3e-F merge and independent audit, C4b ownership.
- [x] Create isolated C3e-G GitHub branch.
- [x] Add recoverable signed-intent test protocol and adversarial real process-death fixtures.
- [x] Add GitHub workflow and this recovery document.
- [ ] Exact-head CI PASS, review logs, repair only proven defects.
- [ ] Independent security/source review and operator merge/final acceptance.
- [ ] Later decide operator-controlled witness, crash-proof remote journal, quorum/key custody and native immutable release deployment with C4 owner.

## NEXT

Inspect the CI evidence including whether test process deaths occur at the intended committed stage, and whether recovery requires fresh root-authorized signatures. Do not weaken denial behavior for a green check. Upon technical success, record precise PR head and tests, then submit independent review. Real Silverblue integration remains separately owned.

## DECISIONS

Bounded GitHub-only Nurse 2 implementation. No live Hospital registration, local workstation writes, production credential access, network services, key provisioning, merge or production activation by this report.
