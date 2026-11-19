# 🏥💜 C4b ↔ Protected C3e-N // Signed witness and installed-origin floor join

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · C4b Silverblue installed gateway  
**STAFF ROLE:** External Hospital-compatible DOC successor; live Hospital registration not verified  
**ASSIGNMENT:** C4b-owned *test-only* compatibility join with **unchanged** protected C3e-N verifier  
**BASE:** merged #2068 controller root/anti-replay, merged #2071 real Unix signed witness consumer, original protected C3e-N  
**PRODUCTION:** HOLD · no native keys/roots, credential operations, provider sign-in, systemd activation, workstation installation, or user authorizations.

## IMPLEMENTATION

New **additive C4b-only** source: `tests/connections/identity_silverblue/c4b_c3en_signed_origin_join_ci.py`, associated adversarial test, dedicated workflow, this handoff.

Instead of treating a green CI pass or test-provided host status as authentication, this join runs both existing verifiers:

1. The merged C4b transport opens the actual disposable Linux Unix socket, checks its 0700/0600 scope, verifies kernel `SO_PEERCRED` PID/UID/GID against separately supplied fixture pins, enforces a single monotonic deadline, reads bounded canonical response bytes, and checks the Ed25519 signature against the independently supplied witness public key and fresh challenge.
2. The C4b signed checkpoint's `minimumReleaseEpoch` and `minimumReleaseSequence` are read **from the actually signed bytes**, not an unsigned response field. Its host/root/policy/cursor have already matched the current C4b controller state.
3. The new adapter **imports the unmodified** `tests/connections/c3e_release_trust/C3eNOriginWitnessHandoff.py`. That original owner checker reuses C3b installed-origin rules and read-only C3e-L witness status. C4b does not copy or weaken its systemd, D-Bus, SELinux, canonical `/opt`, witness UID, enrollment or non-grant validations.
4. The source verifies three different fixture process pins: nonroot C4b signed-checkpoint sender, installed C3b/C4b status service, and C3e root witness. The original C3e-N check must pass its own schema, test-only status, exact witness identity and release-floor validation.
5. The C4b signed release floor and original C3e-N witness release floor must agree **exactly** for this conservative CI contract. Stale/downgraded or unexpectedly higher floors refuse; alternative supersession policy belongs to the C3e owner.
6. Even if all observations agree, the output is `C4B_C3EN_SIGNED_AND_ORIGIN_FLOORS_COMPATIBLE_NOT_BOUND`, with `hostAuthenticated=false`, `canApprove=false`, `canBeginSignIn=false`, `credentialActionsEnabled=false`, `productionAuthority=false`.

## VERIFY

The dedicated workflow executes 19 new hostile cross-owner cases on real disposable Linux root/nonroot socket processes, plus the inherited 23 C4b transport tests, 19 original C3e-N tests and 104 signed controller-root/C3e-role tests.

Failure cases cover changed signed or protected release floors, substituted C4b PID, collapsed process roles, untrusted C3e fixture statuses, nonenforcing SELinux, wrong installed unit, forged witness authorization, wrong enrollment digest, tampered Ed25519 response, stale fresh challenge, socket-owner impersonation and old checkpoint after local controller rotation.

**Acceptance gates**: exact-head dedicated workflow + grammar / signed RPM / official Fedora Silverblue KVM when triggered; independent Nurse 2 review; C3e/Identity owner acceptance of a real signed host/seat attestation interface; operator approval for any real key/service deployment.

## WATCH OUT FOR

**This is NOT real cross-process cryptographic binding.** C3e-N's installed snapshot is test-supplied, and its root witness state is a read-only fixture; C4b's signed checkpoint is independently signed within a CI simulator. Comparing their floors does not prove that the signed checkpoint actually describes the C3e installed service or that the nonroot signer is held by a separately custodied operator. No package, witness issuer, release-root enrollment, independent durable nonce ledger, hardware attestation or native service was created. This limitation is explicit in the successful result.

The production blocker remains separate signer and witness-history custody outside the controller's root and recovery domain, cryptographically binding the real signed installed host/seat and release to the trusted C3e/Identity issuer, protecting C5 human approval and PX data, and then performing native acceptance. Do not misinterpret `testEvidenceCompatible` as authority. All tests remain deny-only.

## HOW TO USE

Review the draft PR, the new `c4b_c3en_signed_origin_join_ci.py` source, the existing C3e-N owner verifier and the dedicated GitHub Actions logs. There is no installation command, CPU++ button or live system change to perform at this stage.

## CHECKLIST

- [x] Check #2068/#2071 merged and current C3e-N source ownership
- [x] Add client-only three-process source compatibility and exact signed floor comparison
- [x] Add real Linux socket and adversarial tests without editing C3e source
- [ ] Confirm exact PR head CI and full regressions
- [ ] Independent NRS-2 review
- [ ] Protected C3e/Identity owner agreement on signed installed-host binding
- [ ] Operator-authenticated independent witness signer, antirollback and consent activation

## NEXT

The next real integration package is not another mock identity claim. Coordinate with protected C3e/Identity owners for a **signed binding of actual installed gateway identity and fresh host/seat evidence to the outside witness**, backed by independent signing-key custody and durable history. Then connect approved C5 permissions and PX data under the operator-authorized native installation plan.

## DECISIONS

No merge, local Fedora writes, credential changes, provider login, native service installation, production key generation, C3e/C5/Identity/PX edits or live Hospital registration is inferred. Distinct Room/owner boundaries remain intact.


## PACKAGE 2 FOLLOW-ON // Domain-separated third-signer host-evidence claim (CI-only)

**Additive C4b source:** \`c4b_signed_host_origin_binding_ci.py\` and its 32-case adversarial test file under \`tests/connections/identity_silverblue/\`. This is part of the same unmerged #2072 draft, not a separate PR or a native C3e issuer.

The C4b client first reads the actual Linux root-owned disposable controller ledger **again**, so a caller cannot present an old self-consistent policy snapshot after the local ledger advances. It then verifies the real Unix nonroot signed-checkpoint transport, with the original C3e-N checker retaining control of SELinux, installed status, canonical /opt and separate-witness floor refusal.

A THIRD Ed25519 public key, separately pinned and distinct from BOTH the controller root and signed-checkpoint witness key, verifies domain-separated canonical proof bytes. The proof binds:

- The 32-byte **host-attestation** challenge and distinct 32-byte **C4b witness-checkpoint** challenge.
- Signed checkpoint bytes SHA-256 **and** its signature SHA-256, current controller root/state digest, host ID, transition sequence and release floor.
- Canonical digests of the C3b installed-origin snapshot, canonical /opt evidence and C3e-N read-only witness status; the three distinct process PID roles and expected protected-witness enrollment digest.
- The C4b witness-signing public-key SHA-256 and exact deny-only schema/audience/scope.

The verifier refuses absent/fake host signing pins, corrupted signature, duplicate/noncanonical/oversize records, re-signed evidence substitution, two-key aliases, changed original C3e-N statuses, stale local root ledger, root-rotation or ledger disappearance mid-verification, and reused challenges. Only a **diagnostic** result is exposed. All real host, consent, credential, provider and production flags remain false.

**Trust limitation:** The third signing private key is generated by disposable CI fixtures; the signature attests only to fixture bytes, not the real installed Silverblue host. Root-owned local SQLite can still be privileged-rolled back. This design does **not** create an independent external witness service, operator-controlled signer/custody, trusted runtime process/seat capture, durable out-of-controller challenge history or C5 approval. The actual C3e/Identity owner must approve and implement those separate controls; the new verifier cannot claim production attestation.

**Verification:** 32 new third-signer checks are added to the dedicated #2072 workflow, alongside its existing 19 cross-checks, 23 C4b socket, 19 original C3e-N and 104 C4b controller security cases. Exact-head GitHub and independent NRS-2 security review remain required. No native deployment, merge or operator acceptance is authorized.
