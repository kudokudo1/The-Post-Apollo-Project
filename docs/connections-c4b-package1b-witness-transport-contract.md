# 🏥💜 Universal Connections // C4b Package 1B Witness Consumer Boundary

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · C4b Silverblue Identity signed gateway  
**STAFF:** External Hospital-compatible successor DOC, live registration not verified  
**ASSIGNMENT:** C4b consumer-side signed external-witness transport integration, not the protected C3e/Identity issuer  
**UPSTREAM:** [merged Package 1 PR #2068](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2068), merged real Silverblue kernel-observer PR #2066  
**STATE:** New separate draft due to Package 1 being merged, not a replacement for #2068  
**LIVE AUTHORITY:** HOLD. No real external witness service, operator-managed roots, credentials, C5 consent or native deployment.

## IMPLEMENTATION

Additive C4b-only source:

- `tests/connections/identity_silverblue/c4b_witness_transport_consumer_ci.py` is the controller **client** for a bounded Linux Unix-domain stream. It is not a witness provider and contains no private signing keys.
- `tests/connections/identity_silverblue/test_c4b_witness_transport_consumer_ci.py` boots a separate, disposable **nonroot Linux process** in real GitHub CI and exercises socket framing, kernel-reported `SO_PEERCRED` PID/UID/GID checks and cryptographic identity.
- `.github/workflows/connections-c4b-package1b-witness-transport-ci.yml` runs the new 21-case suite plus inherited merged Package 1 rotation, C3e role, root-owned ledger and external-checkpoint regressions.

**Actual bytes and processes:**

1. A protected test harness independently selects a 32-byte challenge, current controller ledger state, exact expected peer PID/UID/GID and an Ed25519 witness public key plus digest. All these are **synthetic CI pins**, not operator custody.
2. C4b validates the socket file is a 0600 Unix socket inside an exact 0700, nonroot-owned `/run/c4b-p1-witness-ci-*/` directory; a symlink, wrong owner, unexpected path or wrong file type refuses.
3. Linux `SO_PEERCRED` must agree with the independently supplied peer PID, UID and GID. Merely changing the socket file's owner to match the expected UID is insufficient if the actual listening process runs as root.
4. The client sends one length-prefixed, bounded canonical JSON request with the exact host and challenge digest. The mock peer signs its own fixed history, not the controller's supplied state. The client accepts at most 8192 bytes of response, rejects truncated/oversized, duplicate-key, noncanonical, unknown-field and malformed responses.
5. The response contains only signed canonical checkpoint bytes and an Ed25519 signature. The existing `c4b_signed_external_checkpoint_ci.py` verifies it with the **separately pinned** public key against the expected current ledger state and challenge. It refuses stale state, different host, wrong root, wrong release floor and signature substitution.
6. The verified exact witness-input dictionary can be supplied to the already merged `verify_and_commit_rotation_with_checkpoint_ci_only` diagnostic gate; a separate end-to-end test consumes it and demonstrates the one-use root-owned transaction. The live Connections broker stays disabled.

## VERIFY

The isolated 22-test transport suite covers valid signed remote-process response, end-to-end root-owned rotation, forged socket owner vs real kernel credentials, wrong pinned PID or GID, fake Ed25519 signature, grant-field injection, schema forgery, duplicate/noncanonical JSON, malformed/partial/oversized frames, challenge replay, stale controller history after rotation, unsafe paths and directory permissions, bad public root, host mismatch and hard-disabled authority.

The new workflow must pass at the exact PR head along with the inherited 104 Package 1 cases and C3e-AF alignment. The official Silverblue KVM regression also runs on changes to the repository; check its independent result. Obtain independent Nurse 2 review before considering merge.

## WATCH OUT FOR

**This is not a production remote witness.** A same-machine nonroot process demonstrates kernel UID/PID separation but cannot establish an operator-owned root of trust against a compromised host root. `SO_PEERCRED` confirms the connected process, not who owns a signing key or whether an independent service's historical state survived rollback. All identity pins, challenge bytes, signing key, witness history and test process are supplied by the disposable runner. Real deployment requires a separately owned and approved C3e/Identity witness service, independent signing-key lifecycle, audit and antirollback, a durable external one-use challenge ledger, protected transport with independently enrolled peer/service identity, and a verified Silverblue host/seat witness. C4b **cannot** authorize C5 human consent or credential access.

The code is intentionally guarded by `GITHUB_ACTIONS`, `RUNNER_ENVIRONMENT`, `GITHUB_ACTOR`, an explicit test-only environment switch and Linux root checks, and all returned authority flags remain `False`. Environment flags are test scoping, **not security credentials**.

## CHECKLIST

- [x] Recover merged #2068 and current #2066 source, ownership and last CI
- [x] Build C4b client-only bounded Unix transport and kernel-credential verification
- [x] Add separate nonroot service mock, end-to-end replay, hostile-input tests
- [ ] Exact-head CI and real Silverblue regression
- [ ] Independent Nurse 2 source/security review
- [ ] C3e/Identity operator approval of real witness issuer, custody, transport and recovery
- [ ] Native integration in owning lanes and separately authorized activation

## NEXT

After verifying the new source, the C3e/Identity owners should review only the **consumer interface**, especially expected peer identity provenance, external witness root pinning, freshness/challenge lifecycle and the actual service location. No authority or source ownership is transferred by this draft. The operator separately approves any production key provisioning and service activation.

## DECISIONS

No merge, local workstation writes, signing-root enrollment, provider login, C3e/C5/Identity/PX source changes or production activation. Preserve the merged previous Package 1 and C4b real-KVM checkpoints.
