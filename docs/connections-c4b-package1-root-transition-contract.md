# 🏥💜 Connections Package 1 // Controller-root rotation and revocation continuity

**PATIENT:** The-Post-Apollo-Project
**ROOM:** Universal Connections / C4b Silverblue Identity installed gateway
**STAFF ROLE:** External Hospital-compatible successor DOC (live Hospital attachment not verified)
**ASSIGNMENT:** Package 1 trusted-host foundation, C4b-owned producer/gateway enrollment seam
**STATE:** draft source-only CI, **NO production authority**, no real trust-root enrollment or workstation changes
**UPSTREAM:** C4b signed enrollment #2033, controller policy #2044, C3e role alignment #2046, real Silverblue observer #2066 (merged; this is not production acceptance)
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
- New C4b 28-case test suite: old/new root substitution, signature tampering, replayed/gapped cursor, forged chain head/event ID, noncanonical/duplicate event, host and release substitution, revoked ID removal, missing/swapped bundle, false denial signer, nonce replay and no-grant assertions
- Dedicated GitHub Actions workflow checks new tests plus existing controller policy, key enrollment, C3e-AF alignment, signed controller challenge and runtime receipt regressions

Source paths are tests/connections/identity_silverblue/c4b_signed_trust_transition_ci.py, test_c4b_signed_trust_transition_ci.py, and .github/workflows/connections-c4b-package1-signed-root-transition-ci.yml.

## HOW TO USE

Developers can read the draft and GitHub Actions results. This is **not** a CLI for installing roots. No new button, setting, key file, daemon, credential provider or native host enrollment is enabled. CPU++ → SETTINGS → CONNECTIONS remains read-only/deny-only.

## VERIFY // Criteria

- [x] New 28-case source-level test suite succeeds on exact PR head
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

Check the exact-head workflow. Repair **only** evidenced test or wiring failures on this Package 1 branch; do not relax protected C3e process constraints. Seek independent review and an operator root-custody decision before proceeding to actual trusted enrollment. The companion #2066 real-guest observer was merged on 2026-11-19. The C4b controller-root Package 1 draft remains separate and requires its own independent review.

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
- Adds **20 positive/negative test cases**, making **48 new Package 1 cases** after the additional retired-root receipt-role refusal, plus inherited C4b/C3e regressions in the existing dedicated workflow.

**Trust limitation:** Caller-selected CI roots, policy bytes, cursor and runtime pins are still not independent native custody. No release artifact-to-running-process external witness, protected monotonic ledger, root rollover recovery approval or native sign-in authority results from this. The real protected key-store/host-witness integration still requires operator and C3e/Identity ownership decisions.

## PACKAGE 1 LINUX CONTROLLER-LEDGER REHEARSAL // 2026-11-19

**Next substantive Package 1 increment:** root-owned *controller* policy and monotonic rotation cursor implemented solely for disposable GitHub-hosted Linux CI. This is additive C4b code, not a protected C3e issuer or a native workstation install.

New source files:

- tests/connections/identity_silverblue/c4b_root_owned_controller_ledger_ci.py
- tests/connections/identity_silverblue/test_c4b_root_owned_controller_ledger_ci.py

Actual kernel Unix-UID boundary exercised in GitHub Actions:

1. Explicit GitHub-hosted CI guard requires Linux root and a protected /run/c4b-p1-controller-ci-* directory owned by root, with mode 0700.
2. The root supervisor explicitly initializes a 0600 SQLite ledger with the previously pinned synthetic controller public key, signed-policy bytes and current chain cursor. A missing database is NEVER auto-created during consume.
3. A separate staged-intent transaction pins the exact next root SHA256, next policy SHA256 and one-use transition ID before candidate verification. Staging does NOT equate to operator consent.
4. Under BEGIN IMMEDIATE, the root process re-reads that private current state, reuses the existing C4b dual-signature verifier and fresh signed guest denial, and atomically advances both the policy/root and chain cursor while clearing the exact pending intent.
5. Replay, tampering, invalid signatures, missing state and a second intent refuse without silently advancing the cursor; a separate real nobody UID process is required to fail a read on the protected DB.

**Security limitations:** This proves a Linux permission separation test against an unprivileged desktop UID, not physical machine identity, SELinux/TPM root-of-trust, independent C3e protected trust custody, hardware antirollback or authentic human consent. A compromised root supervisor or snapshot of the whole root-owned SQLite file defeats the source's external rollback claim. CI-owned disposable Ed25519 fixtures can never authorize production sign-in. Key custody and native controller installation remain held for the operator and protected owner coordination.

**Verification gate:** 28 new disposable Linux root-owned-ledger tests in the existing Package 1 CI, in addition to 28 signed root-rollover and 20 rotated C3e-AF alignment tests. Exact-head workflow results and independent security review still required.

**Recovery:** #2068 remains the single C4b Package 1 draft. To reproduce CI, inspect the dedicated connections-c4b-package1-signed-root-transition workflow. No commands are provided for running this fixture as a production service.


## PACKAGE 1 FRESH INDEPENDENT CHECKPOINT CONTRACT // 2026-11-19

**Scope:** C4b-only additive source verifier and Linux CI tests, on the existing #2068 draft. This **does not** enroll an actual remote witness or choose the operator's production signing-key custodian.

### Mechanism

- A separately pinned Ed25519 **witness** public key verifies a domain-separated, canonical, exact-fields signed statement containing an independently issued fresh challenge digest and the controller's currently committed root, policy hash, chain digest, sequence, host ID and minimum release floor.
- A stale signed witness response for a different nonce, a different host, a different local root/policy, a different release floor or a rolled-back SQLite transition sequence **refuses**. C4b controller root and witness signer must be separate.
- The C4b root-owned ledger now exposes a distinct **witness-required diagnostic rotation entrypoint**. It verifies the signed witness statement against the ledger's **current state inside the same BEGIN IMMEDIATE SQLite transaction** before checking old/new root signatures and spending the one-use staged intent. The legacy unwitnessed CI entrypoint remains test-only; neither entrypoint can grant credentials or production login.
- A disposable Linux test copies a root-owned SQLite file before a legitimate rotation, lets the witness sign the newer state, restores the older file, and verifies that the newer signed witness **refuses** the restored controller state. It explicitly demonstrates that a forged/stale witness signing home can make old state appear consistent again: the true independent custodian is the missing trusted component.
- Tests also check missing signer, wrong pinned witness key, signature forgery, duplicate/noncanonical fields, wrong host, wrong chain, wrong release floor, wrong controller root, nonce replay and production-scope injection. No real external witness private key is stored or installed by this package.

**Trust boundary:** This is stronger than inspecting a Unix UID permission flag, because it shows how a separately signed checkpoint can detect a privileged filesystem rollback *when the external witness preserves and signs the genuinely current history*. It is **NOT** protection against a compromised shared-root signer, external witness rollback, compromised operator key, copied signing seed, reuse of a signed challenge, or forgery when the attacker controls all test pins. A production service needs an independently isolated custodian, protected one-use challenge ledger, audited key enrollment/recovery, rollback-resistant hardware or external anchor and signed host/seat/runtime attestations. C3e and Identity retain ownership of those decisions.

**Verification criterion:** New 21-case checkpoint/recovery suite under real disposable Linux root CI in the **same** Package 1 GitHub Actions workflow; prior 28+20+28 source/UID tests plus inherited C4b/C3e tests must also stay green. Exact-head independent Nurse 2 review remains required. No merge, local installation, trusted roots or sign-in activation are authorized by CI.
