# 🏥💜 TASKS M12c // Independent Host Trust Authority Decision Contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Independently controlled signing keys, release approval, key rotation and anti-rollback governance  
**DOCTOR //** External Hospital-compatible ChatGPT worker; no verified live Hospital registration or staff ownership  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED SOURCE //** GitHub `main` `126dfbfb7cf86eca420e66c618b8266775dfd552`, October 31, 2026. Recheck before implementing a subsequent patch.  
**CLASSIFICATION //** **PROPOSED DECISIONS + SYNTHETIC POLICY TESTS**, not an approved production trust authority.

## IMPLEMENTATION

### Why this boundary exists

M11y exercised an Ed25519 signature verifier on disposable files, using generated keys and trust inputs passed separately to the verification function. M12b documented the next gate, **RELEASE_TRUST**, as open. Neither milestone proved who legitimately holds the real signing key, how a public verification key arrives independently of a candidate release, or which actor is empowered to approve its installation. Code signed by an attacker with an attacker-supplied key is still attacker code.

M12c documents a role-separated decision process and adds a **pure synthetic policy model** plus negative tests. The model does not run cryptography or connect to M11y automatically, and **cannot declare a real signer trusted**. Its Boolean `signatureVerifiedAgainstExternalRoot` and analogous inputs are synthetic test assertions, not evidence. Its strongest outcome is `SYNTHETIC_REVIEW_ELIGIBLE`, always with `productionAuthorized:false`, `trustStoreChanged:false` and `activationApproved:false`.

### Authority boundaries awaiting operator decisions

| Decision | Proposed models; neither accepted | Must never occur silently |
| --- | --- | --- |
| Trust-root custodian | Operator-held offline root, or administrator-owned trust store with operator-governed enrollment | Key supplied by the candidate release becomes trusted |
| Release signer and reviewer | Separate signing, independent review, custodian and final operator roles; equivalent auditable controls subject to approval | A signer approves their own release |
| Release channel | Signed immutable artifacts pinned to a separately authenticated verifier; or equivalent administrator-controlled distribution | Execute directly from mutable untrusted checkout |
| Anti-rollback | Protected monotonic generation **and exact accepted release identity**, with independent recovery | Same-generation replay or floor reset via the release folder |
| Rotation and revocation | Old/new-root transition proof and independent approvals, or pre-authorized offline recovery anchor | Self-signed replacement key automatically trusted |
| Threat model | Explicitly determine same-user adversary and root/admin trust limits; choose OS controls accordingly | PIDFD, nonce, signature or `flock` presented as complete host attestation |

No real custodian, signer, reviewer, key ID, filesystem trust-store path, key material, release generation or installed host is selected by this milestone. **The operator retains final authority**. The proposed separation of duties is a *recommended control*, not an unapproved assertion about Hospital staff assignments.

**Separate actions remain distinct:** trust-root enrollment, signed-release review, code installation, guarded TASKS writer activation and task-data restoration. Approval of any earlier action never implies a later one.

### Concrete model and failure cases

`tests/tasks/fixtures/TaskTrustAuthorityPolicyM12c.py` is a **pure Python import-only** evaluator. It accepts only caller-supplied synthetic objects; there is no filesystem, networking, shell, credential store, process launch, QML, task source, real generation persistence or signing step. It enforces proposed independent-role IDs, external-root provenance marker, pinned key fingerprint, released generation beyond a supplied floor, approved signer identity, revocation and strict evidence fields. A separate pure key-rotation evaluator refuses reusing an old key, using revoked/newly unknown keys, lowering the floor, or missing independent transition/review assertions.

The test matrix includes missing anchor, key supplied by release, role collisions, wrong signer, key/fingerprint substitution, revoked signer, generation rollback and same-generation replay, missing/false external checks, malicious field types, incomplete rotation evidence, unsafe key rotation and no-activation invariants.

**A passing model does NOT authenticate real people, verify signatures, establish an independently controlled key, attest an interpreter or change a protected generation floor.** M11y's actual synthetic Ed25519 verifier remains a separate crypto mechanism, and its generated keys must not be reused as production identities. An attacker controlling the caller could supply `True` for every model field; therefore **this model is not a production authorization endpoint**.

### Trust model / deployment implications

A real future implementation would need separately verified authorized identities and roles, a protected signing/private-key lifecycle, a publisher/source review audit trail, independent verification-key enrollment, exact executable/module hashes and interpreter provenance, restricted filesystem and process launch, a durable generation + release-digest floor protected against rollback, explicit revocation/recovery, and noncooperating-writer threat analysis. A same-user attacker, compromised operating system, or malicious parent process cannot be excluded merely by `pidfd_open`, `/proc`, Ed25519 over artifact bytes, or a session nonce.

The live TASKS `ApolloHubTodoStore.qml` still has **one `FileView`**, nine mutations through `stage(result)`, `guardedWriterEnabled: false`, and legacy `onSaved` publication. Native callback provenance, real-source backup, last-confirmed UI recovery and asynchronous API acceptance are *not* solved by trust governance.

## HOW TO USE

No operator-local commands and no keys to install. Review this proposal and machine-readable decision file in the draft PR. The CI-only test in a separate checkout is:

```sh
python3 tests/tasks/test_task_trust_authority_review_m12c.py
```

This invokes only synthetic review objects. It does not read actual TASKS JSON, start a host, install credentials or change an operating system service.

## VERIFY

- Inspect branch diff: only this report, `task_trust_authority_review_m12c.json`, the pure model, its tests and scoped GitHub Actions workflow.
- CI reruns prior M12b disabled integration audit, M11y synthetic signed release, M12a synthetic UI completion, M11t open gates and M11d one-writer inventory.
- M12c's **six trust governance choices remain OPEN**, M12b's **ten production evidence topics remain OPEN**, and M11t's **nine activation gates remain OPEN**, even when CI succeeds.
- Source of truth is current GitHub `main`, not an assumed synchronized Fedora working tree.

## WATCH OUT FOR

- **Do not generate or publish a production private signing key in GitHub, CI logs, a chat, or a pull request.**
- Distinguish a signed artifact from an independently **approved signer**. A valid signature from the wrong key must fail closed.
- A monotonically increasing number alone may not prevent replay of a different artifact claiming the same generation. Store or pin accepted release identity as well and protect the floor externally.
- Signed releases do not solve a compromised interpreter, hostile runtime, external writer, power loss, or native FileView callback misattribution.
- This report does not establish an actual trust-root owner, authentic identity verification, signed production release or live Hospital permission.
- The specific threat model and administrator-owned versus offline-root choice require explicit operator acceptance, not CI-based self-selection.

## CHECKLIST

- [x] Inspect Syntagma and relevant Hospital permissions
- [x] Verify M12b merged and production guard still disabled
- [x] Check current PR/branch ownership before GitHub-only changes
- [x] Document authority, trust distribution, generation and rotation choices
- [x] Add synthetic rejection tests with no production authority
- [ ] Verify final GitHub CI and independent review
- [ ] Operator review and merge
- [ ] Operator selects trust-root custodian and release governance
- [ ] Separately scope secure production provisioning, native source/host integration and activation

## NEXT

Review M12c. After explicit choice of governance model, the next **separately bounded** milestone would test operator-approved trust-anchor packaging/distribution on isolated, **nonproduction** fixtures. M12d's production-shaped host/source boundary remains proposed only; do not widen M11l or M11m disposable path restrictions.

## DECISIONS

**Verified:** M12b is merged, the single existing TASKS JSON writer is still legacy and guarded activation is disabled. The earlier M11y signed-release checks are synthetic-only.

**Proposed, not canonical:** Four authority roles, root custody, signing/reviewer separation, immutable distribution, generation/digest floor, key rotation/recovery and threat model.

**Not authorized:** Creating or publishing real keys, installing trusted roots, accessing real task data, changing `ApolloHubTodoStore.qml` or shell imports, local Fedora writes, Quickshell restart, merging this PR, guarded writer activation, task-data restoration, SQLite task migration or live Hospital registration.
