# 🏥💜 Universal Connections // C3e-I supervised supersession transaction fixture

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release recovery  
STAFF ROLE // Nurse 2 · NRS-2, external Hospital-compatible; no live Hospital registration verified  
ASSIGNMENT // C3e-I *synthetic* crash-recoverable supersession of a C3e-G stalled pending release with a newer root-signed candidate and operator-signed decision  
BASE // C3e-H development head `64df39c0`; **PR #1534 subsequently MERGED** at `184f46cd`. C3e-I originated as a stacked branch and was retargeted to `main` only after GitHub confirmed that merge. No independent C3e-H review submission was present at reconciliation.  
SCOPE // GitHub-only test fixtures, workflow and this document. No workstation, native RPM, real keys, real provider credentials, production service, NAS or live witness.

## IMPLEMENTATION

C3e-G [PR #1525](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1525) is merged. It requires the original pending signed release and original authority floor for a crash reconciliation. If the external release authority has advanced to a newer signed policy/release, ordinary recovery refuses and leaves an outstanding intent. C3e-H [PR #1534](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1534) adds a **READ-ONLY** operator signature preflight for this case; it has now **merged**. Its independent post-merge security review remains a separate gate.

C3e-I **began as a stacked PR targeting C3e-H's branch**, not a stealth replacement of C3e-H's merge approval. After C3e-H merged at `184f46cd`, its PR base was retargeted to `main`. The historical dependency and missing independent review remain explicit. It tests a permissioned, two-database supersession **inside disposable GitHub CI**:

1. Require an existing C3e-G pending journal. Explicitly initialize an extra **single-row** `supersession_intent` table *inside the same existing synthetic witness SQLite file*. No extra user-service or identity is added and no missing trust file is auto-created.
2. Snapshot bounded, nofollow operator-signed approval, operator public key, authority public key, root-signed release policy, delegated signature, exact package and related evidence **once** into a private temporary directory. Feed the same immutable-by-convention snapshots to C3e-H preflight and the subsequent C3e-C client update. No candidate-supplied key can change the pre-pinned root.
3. Invoke unchanged C3e-H's real GPG signature/purpose/node/epoch/sequence/digest checks with a **fresh authority challenge**. C3e-I adds the minimum extension needed for crash recovery: on an explicit retry only, the C3e-H gate may also examine a client already at the **exact newly signed replacement tuple**. Unrelated or unverified client contents refuse.
4. Under a witness-side SQLite `BEGIN IMMEDIATE`, verify that the legacy pending journal, enrolled identity, initial witness and client state still match the approved context. Durably **PREPARE** a supersession intent containing the hash of the original pending record and the exact operator approval digest, prior client checkpoint, new signed target checkpoint, and current signed authority floors. Leave the legacy C3e-G journal intact.
5. Invoke unchanged C3e-C root-authorized client release admission to commit the newer signed release. Require the client checkpoint to equal the signed tuple. In one final **local** witness transaction, recheck both pending journal and target client, commit witness epoch/sequence and atomically delete **both pending journal rows**. There is no silent reset of trust, nor a client/witness distributed atomic commit.
6. For a process dying after PREPARE or client COMMIT, normal new operations refuse. **Explicit recovery only**, with **the same still-valid operator-signed approval**, exact same signed candidate/authority-floor fingerprint and a **fresh** authority challenge, finishes from the recorded prior or target client state. Changed operator approval, altered release, missing/truncated witness, newly advanced authority floor, conflicting client or expired operator signature refuse while keeping both original intents for supervised resolution.
7. All operations run with three disposable GPG identities (release-policy signer/delegated signer, authority signer and operator signer), an existing separate-process synthetic C3e-E authority, and existing CI-only SQLite fixtures. The optional fault hook terminates a child process at each durable phase. A simulated failed witness update must preserve **both** journals until retry.

### Recovery state table

| Observed state | Allowed synthetic behavior |
| --- | --- |
| Legacy pending + signed operator approval for newer release; no supersession intent | PREPARE newer supersession only after C3e-H preflight |
| Supersession PREPARED, client still old | Explicit retry + same signed approval and signed newer release; commit client then witness |
| Supersession PREPARED, client already new | Explicit retry + reverified exact new release; commit witness and clear both intents |
| Final witness committed, both intents cleared | Normal newer admission may be considered later; old signed approval has no pending target |
| Pending + changed approval, signature, root, client or authority state | Fail closed; never silently discard pending intent |
| Missing, restored or corrupt ledgers | Fail closed; require operator-supervised independent recovery |

## HOW TO USE

No desktop action. A new GitHub workflow `.github/workflows/connections-c3ei-supervised-supersession.yml` drives synthetic signed release 9 into a C3e-G crash window, advances the simulated authority and signed candidate to release 10, signs an exact scoped synthetic operator approval, and exercises a crash/retry/supervision scenario. Its test-only outputs are **not usable as a real operator authorization**.

New files:
- `tests/connections/c3e_release_trust/C3eSupervisedSupersession.py`
- `tests/connections/test_connections_c3ei_supervised_supersession.py`
- `.github/workflows/connections-c3ei-supervised-supersession.yml`
- This document

C3e-I also makes one **stacked change** to C3e-H's yet-unmerged `C3eOperatorRecoveryGate.py` to permit a post-client-commit **exact signed-target** state during explicit recovery, rather than broadly accepting an arbitrary different client checkpoint. The original C3e-H tests remain in the dependency suite.

## VERIFY

- [ ] New C3e-I real GPG/SQLite tests pass, including real process death after the supersession intent, client update, and final witness update.
- [ ] Explicit retry rechecks original operator signed approval/pending hash and a fresh authority signature; no replay or unsigned reset.
- [ ] The new final witness transaction advances to exact signed target and removes both journal rows only after correct client commit.
- [ ] Same-signed-approved release can recover from either old or already-new client; changed approval/candidate/floor/refused authorization cannot.
- [ ] Failure to update witness leaves both pending journals and client target for explicit retry.
- [ ] Prior C3e-H (16), G (19), F (16), E (15), D (15), C (16), A (18), and C2n (6) deny-only tests pass.
- [ ] Existing Fedora signed fake-RPM guest, root-policy verification and Grammar regressions pass.
- [ ] Independent **post-merge** C3e-H security audit, separate C3e-I security audit, operator final acceptance and merge chronology documented accurately.

## WATCH OUT FOR

**This is not a distributed atomic transaction.** The newer client release and new witness floor still land in separate SQLite commits with a durable local intent between them. Real power-loss, disk corruption, remote races, immutable deployment, TPM/HSM custody, and a separate authenticated authority are not simulated. A privileged actor can restore all software-only histories and replay the synthetic operator key. The disposable signing key is **not operator-enrolled** and is generated on the same CI runner as the other identities. The exact approval is time-bound; after expiration or a newer authority floor, recovery deliberately blocks rather than silently renew or ignore authorization.

The added code is **test-only**, under `tests/connections/`; it is not a production primitive and is not integrated with `rpm-ostree`, the Connections broker, Social/Settings, real credentials, NAS or a remote witness. There is no production signing key, protected external monotonic storage, authenticated client transport, quorum, operator root-custody or recovery ceremony. **The existing C4b Silverblue worker owns native lifecycle integration** and is not modified.

The C3e-H preflight reads SQLite with `mode=ro` but cannot itself lock two remote databases across a future execution. C3e-I repeats trust checks and locks the local witness journal for prepare/finalize; its separate read of the client file is still vulnerable to hostile concurrent legacy writers that ignore this new protocol. An operator-controlled single-writer admission service and independent trust boundary would be necessary before a real rollout. Production authority use remains HOLD.

## CHECKLIST

- [x] Rechecked current GitHub, C3e-G merged state, C3e-H open review gate and C4 Silverblue ownership.
- [x] Read Syntagma AGENTS, Hospital Agent/Report and Permissions protocols.
- [x] Create C3e-I isolated branch **from C3e-H head**, not main.
- [x] Add synthetic signed supersession journal and real crash/retry adversarial tests.
- [x] Add CI and this handoff document.
- [ ] Exact-head CI, defect repair and independently verified results.
- [ ] C3e-H **post-merge** independent review and C3e-I independent review, followed by separately recorded operator final acceptance and merge disposition.
- [ ] Operator-design approval for real release-root/witness custody and native Silverblue coordination.

## NEXT // DECISIONS

Review exact CI evidence for both signing authority and commit-order fault windows. Correct only demonstrated defects and preserve strict signature/root/rollback checks. C3e-I must not be mistaken for independently reviewed solely because its parent C3e-H merged; preserve both review histories. Separate live operator approval and production trust must be established before any real recovery permission is provisioned.

**No workstation writes, production key import, service activation, real credential access or C4b ownership change by this experiment.**
