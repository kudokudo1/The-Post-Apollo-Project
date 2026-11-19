# 🏥💜 Connections Package 1 // Controller-root rotation and revocation continuity

**PATIENT:** The-Post-Apollo-Project
**ROOM:** Universal Connections / C4b Silverblue Identity installed gateway
**STAFF ROLE:** External Hospital-compatible successor DOC (live Hospital attachment not verified)
**ASSIGNMENT:** Package 1 trusted-host foundation, C4b-owned producer/gateway enrollment seam
**STATE:** draft source-only CI, **NO production authority**, no real trust-root enrollment or workstation changes
**UPSTREAM:** C4b signed enrollment #2033, controller policy #2044, C3e role alignment #2046, real Silverblue observer #2066 (independent draft review)
**DOWNSTREAM:** protected C3e issuer/Identity native consumer, C5 one-use consent, approved operator root-custody decision
**OWNERSHIP:** only newly added C4b Python test-source, workflow and this document. The protected C3e/C5/Identity source and installed C4b service remain unchanged.

## Why this package exists

The working controller-policy reader authenticates an enrollment certificate against a public root supplied by an external **fixture** directory. It can reject forged guest signer keys and signed-host mismatches, but cannot prove who controls that root or whether the policy directory has been rolled back. Existing protected C3e floor ledgers and signed-role tests are separate owner-controlled experiments, not an operator-enrolled production authority.

This first package increment adds one coherent read-only transition contract: **a proposed change of the controller enrollment root must be signed by both its previously anchored key and its successor** and tied to the external controller's exact predecessor policy digest, previous transition chain head, monotonic transition number, host, existing/new release floors, and non-erased revocation set. The successor's actual bundle is then verified by the preexisting C4b controller reader against a fresh signed BEGIN/UNAVAILABLE denial.

A candidate that merely controls the new root cannot sign for the old root. A candidate controlling only the old root cannot impersonate the successor. A candidate attempting to remove an old revocation or reduce the release floor is refused even if it obtains both signatures. All of this assumes the **separate** previous-policy and transition-cursor pins remain controlled by a trusted party. CI does not provide that party.

## IMPLEMENTATION // Contract and source

- New C4b signed trust transition module:
  - Canonical exact-fields, duplicate-key-free event encoding; Ed25519 domain separation
  - Requires distinct previous and proposed public keys and their separate signatures over identical bytes
  - Requires a caller-supplied *independently authenticated* prior policy digest, prior transition SHA-256, monotonic sequence and exact event ID
  - Requires old and new root fingerprints to match canonical controller policy records
  - Preserves exact host, role/audience and source scope; rejects release downgrade, changed release without version advance, and revoked-ID removal
  - Reads the replacement bundle with unchanged controller policy intake, verifies successor signed enrollment against the same actual denial key and controller challenge
  - **Read only**: returns CI observations with all host, enrollment, consent, credential and production authorization flags false
- New C4b 27-case test suite: old/new root substitution, signature tampering, replayed/gapped cursor, forged chain head/event ID, noncanonical/duplicate event, host and release substitution, revoked ID removal, missing/swapped bundle, false denial signer, nonce replay and no-grant assertions
- Dedicated GitHub Actions workflow checks new tests plus existing controller policy, key enrollment, C3e-AF alignment, signed controller challenge and runtime receipt regressions

Source paths are tests/connections/identity_silverblue/c4b_signed_trust_transition_ci.py, test_c4b_signed_trust_transition_ci.py, and .github/workflows/connections-c4b-package1-signed-root-transition-ci.yml.

## HOW TO USE

Developers can read the draft and GitHub Actions results. This is **not** a CLI for installing roots. No new button, setting, key file, daemon, credential provider or native host enrollment is enabled. CPU++ → SETTINGS → CONNECTIONS remains read-only/deny-only.

## VERIFY // Criteria

- [ ] New 27-case source-level test suite succeeds on exact PR head
- [ ] All inherited C4b controller-enrollment / C3e-AF contract regressions succeed on exact head
- [ ] No C3e, C5, Identity, Hospital, PX, installed gateway, key or local workstation code mutated
- [ ] Independent Nurse 2 source/security review
- [ ] Operator acceptance for merge, separate from protected root/host deployment

The prior C4b #2066 KVM run verified the real installed gateway observation and rollback in CI. This rotation module **does not run within the VM** and does not independently authenticate its public key or host. Do not claim the prior KVM result alone verifies a protected root rotation.

## WATCH OUT FOR // Real production dependencies

**The missing trust authority is the blocker, not the number of green fixture tests.** An attacker with control over the independently supplied old root, previous policy digest and chain cursor can forge a self-consistent chain; a privileged actor with filesystem rollback capability can replay the fixture. This read-only function does not protect those inputs, consume a transition durably or provide independent host/seat evidence.

Before implementing an actual native controller, the operator and owning C3e/Identity/C5 teams must explicitly determine:

1. Which independently privileged principal owns the C4b enrollment *private* root, how initial root-public-key enrollment is approved, and whether custody is TPM/HSM or protected service storage
2. How root rotation, break-glass revocation and replacement are approved and audited independently of the compromised old root, including lost-key recovery without silent downgrade
3. Which protected, non-user-writable store holds the authoritative previous policy hash, transition chain head, release floor and revocation history; what prevents rollback after backup restore
4. How an independently authenticated running Silverblue gateway's actual receipt key, signed release and kernel/SELinux process evidence are captured outside guest self-report
5. How protected C3e and Identity consume that evidence without allowing C4b CI booleans to become login or credential grants

C3e and Identity own their source/issuer interfaces. C5 owns per-action human consent and PX owns Hospital's protected SQLite writer. This C4b change grants no ownership of any of them.

## CHECKLIST // Package 1, not a series of tiny PRs

- [x] Recover real C4b checkpoint and verify #2066 KVM success
- [x] Inventory merged controller policy and C3e-AF source seams and avoid owner collisions
- [x] Build one C4b-owned rotation, revocation and successor-enrollment source contract plus adversarial regression package
- [ ] Exact-head CI and NRS-2 independent review
- [ ] Operator-owned real trust-root policy, protected transition store and recovery decision
- [ ] Native external controller/host witness implementation in approved owner scopes
- [ ] Full real signed receipt + release + kernel/seat verification, key rollover and hostile recovery tests
- [ ] Coordinated package acceptance; real production activation remains separate

## NEXT

Check the exact-head workflow. Repair **only** evidenced test or wiring failures on this Package 1 branch; do not relax protected C3e process constraints. Seek independent review and an operator root-custody decision before proceeding to actual trusted enrollment. The companion #2066 real-guest observer stays a separate draft with its review SHA preserved.

## DECISIONS

- The user approved beginning the larger Package 1 work; only owner-scoped GitHub source has changed.
- No real root signing key was minted, copied or installed. Test roots exist only as disposable unit-test data.
- No local host writes, system service mutation, remote login, token handling, provider grant, PX Room mutation, automatic merge or deployment.
- Exact production key-custody and trust-store ownership decisions remain **unapproved** and cannot be supplied by a synthetic CI fixture.

## PACKAGE 1 INTEGRATION UPDATE // C4b ↔ C3e-AF continuity

C4b now composes its own dual-signed successor-root transition with **unchanged protected C3e-AF signed role enrollment verification** in `tests/connections/identity_silverblue/c4b_rotated_c3eaf_role_gate_ci.py`. This does **not** take ownership of C3e source.

- Requires the former C4b controller root, successor C4b root and C3e enrollment signer to remain separate.
- Requires new C4b policy hash, signed host, release epoch/sequence and receipt signer to match the independent C3e role verification after the proposed root transition. A stale signed C3e role for an advanced release refuses.
- Requires the C3e release and witness public keys never reuse the **retired** C4b controller root, in addition to unchanged C3e-AF restrictions against aliasing the successor root.
- Validates a new controller enrollment signed by the new root over the same real fresh signed-denial receipt already used by C4b's prior verifier.
- Adds **20 positive/negative test cases**, making **47 new Package 1 cases**, plus inherited C4b/C3e regressions in the existing dedicated workflow.

**Trust limitation:** Caller-selected CI roots, policy bytes, cursor and runtime pins are still not independent native custody. No release artifact-to-running-process external witness, protected monotonic ledger, root rollover recovery approval or native sign-in authority results from this. The real protected key-store/host-witness integration still requires operator and C3e/Identity ownership decisions.
