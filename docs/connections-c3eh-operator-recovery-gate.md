# 🏥💜 Connections C3e-H // operator-authenticated supersession gate

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release-trust recovery  
STAFF ROLE // NRS-2 · externally Hospital-compatible; no verified live Hospital session  
ASSIGNMENT // Signed operator decision for a **pending** C3e-G release when the authority has advanced  
SCOPE // GitHub-only, READ-ONLY CI test fixture, synthetic keys. No live service, workstation, NAS, key installation or production privileges.

## IMPLEMENTATION

C3e-G [PR #1525](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1525) is merged at `f29c9940`. It persists an intent before updating the client and witness; explicit recovery requires the exact original pending candidate and current authority floor. This is safe when both remain available, but it intentionally deadlocks if the authority has already advanced to a **different release**. GitHub currently does not show a separately submitted independent C3e-G review, so this successor work is still *developer verification*, never a backdated independent audit.

C3e-H adds a **READ-ONLY authorization preflight** and defines the proposed supervisory trust contract. It **does not supersede, delete, rebase or update any pending operation**:

1. Open the existing witness journal read-only and require precisely one C3e-G pending intent. Validate the enrolled node/release root/authority pins, witness previous floor and allowed prior/target client state. A missing/changed/unknown client or witness ledger refuses.
2. Compute SHA-256 of a canonical encoding of the **entire pending journal plus enrolled context**. The operator's signed decision is bound to that exact intent; approval for another pending operation cannot be reused.
3. Query the existing C3e-E simulated authority for **a fresh 256-bit challenge-bound C3e-D OpenPGP proof**, and require its policy/release floors to be strictly above the pending release.
4. Snapshot bounded, nofollow operator approval bytes, detached signature and public key into a temporary location. Verify actual `gpgv` signature against a separately pinned **operator** signer. It must be distinct from the simulated release signing root and authority witness signer.
5. Copy and verify the **newer exact signed release** using existing C3e-A policy/manifest/delegated OpenPGP checks against the signed current authority floor. A forged package or mismatched root policy never obtains a positive preflight.
6. The signed operator record has an exact schema, purpose/audience, node/release/authority/operator pins, pending journal digest, new signed policy/artifact SHA-256, new epoch/sequence, external authority floors, issuance and expiry. Require issued time at or before verifier clock and a maximum 10-minute validity window. Any missing, duplicate, extra or altered field rejects.
7. Inspect the two ledger files with SQLite `mode=ro` and `query_only=ON`, not with the previous read/write connection helper. Reinspect them before returning success to detect state changes during signature verification. Result is only `C3EH_TEST_SUPERSESSION_GATE_AUTHORIZED_READ_ONLY`; the code contains no witness/client UPDATE, DELETE, installation, network endpoint or production broker import.

The new workflow exercises 16 real GPG adversarial cases, all earlier C3e-G/F/E/D/C/A tests, and the existing C2n permission-denial contract. Prior C3e code, C4 Silverblue, systemd, CPU++ widgets and package installation are untouched.

## HOW TO USE

No desktop action. In disposable GitHub CI, the C3e-G fixture leaves a signed release 9 pending, the simulated authority advances to signed release 10, and a **third disposable GPG identity** signs an exact 10-minute supersession decision. The C3e-H gate verifies the request but never performs the supersession.

This is a prerequisite contract for a later, independently reviewed recovery executor. Its failure behavior is intentional: pending work remains pending even when operator authorization fails.

## VERIFY

On exact PR head:

- [ ] 16/16 C3e-H real operator-signer, pending-context, and read-only-storage tests.
- [ ] Approval must reference exact pending journal SHA-256 and exact root-authorized replacement release bytes.
- [ ] Wrong key/pin, replayed signed approval for another intent, wrong scope/node/root, stale/expired approval, duplicate signed fields and forged signature refuse.
- [ ] Unavailable/replayed authority challenge and unsigned candidate refuse.
- [ ] Denied checks do **not** modify the pending intent, witness floor or client ledger.
- [ ] C3e-G (19), F (16), E (15), D (15), C (16), A (18), and C2n (6) regressions pass.
- [ ] Signed fake RPM in disposable Fedora guest and Meta Apollo Grammar remain green.
- [ ] Independent C3e-G post-merge audit and separate C3e-H review recorded accurately, with operator acceptance kept distinct.

## WATCH OUT FOR

**A valid signed approval is not proof of operator consent unless the operator signing identity was already enrolled through a trustworthy, independently controlled process.** In this CI experiment the supposedly trusted operator key is minted by the *same test runner* as the candidate, and its expected pin is a test argument. There is **no real operator-enrolled trust**, real key custody, second administrator, independently protected witness, secure network admission, HSM/TPM rollback counter, physical outage simulation or production multi-machine transaction.

The unsigned request can supply paths, but the bounded nofollow snapshot and detached signature checks make this a static validation experiment. Its result is **not a reusable authorization token**: it is not durable, not replay-resistant across restored state, and not a delegation to a production executor. A future executor must revalidate every signed input under its own locks and require explicit operator authority and independent witness history. The read-only gate does not solve authority-side database rollback, concurrent legacy C3e-F writers, split-transaction atomicity, quorum, disaster recovery, nor lost signed release artifacts.

**No real release supersession is implemented here.** When the authority has advanced, C3e-G's pending transaction is still intentionally blocked. C3e-H only defines/test-checks the extra approval evidence needed before safely designing a durable replacement journal and explicit operator-supervised reconciliation. This avoids silently adding a reset privilege to the existing release path.

## CHECKLIST

- [x] Inspect current Syntagma AGENTS/Hospital policies, PR #1525 state, code/ownership, concurrent PRs.
- [x] Create dedicated C3e-H GitHub-only branch.
- [x] Add read-only operator-signed supersession gate and 16 adversarial cases.
- [x] Add workflow and recovery document.
- [ ] Exact-head CI and failure-driven repairs.
- [ ] Independent security review and scoped merge authorization.
- [ ] Future owner decision: independent witness custody and operator key enrollment, secure signed supersession execution with crash-safe journaling, Silverblue coordination.

## NEXT

Evaluate CI; verify exact SHA, process identity, signer isolation and denial behavior. Only after the **operator trust root and independent witness custody are designed** should a later milestone add actual state mutation. Any production rollout requires separate permissions and native review.

## DECISIONS

External Nurse 2 GitHub-only test implementation. No claim of independent review of our own work. No local workstation changes, real credentials, service launch, key import, system package changes, production authentication, C4b ownership changes, or PR merge in this checkpoint.
