# 🏥💜 Identity Center // Installed-Host V1: disposable signed package and supervised gateway

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In native host integration (external Hospital-compatible; no verified live registration)  
**STAFF ROLE //** DOC-compatible implementation worker, Identity source lane  
**DOCTOR / PROVIDER //** ChatGPT / OpenAI  
**ASSIGNMENT //** Implement initial independently pinned installed **Identity Center** gateway release/process witness and exercise the actual gateway in a disposable supervised installation per [issue #1662, DOC direction](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662#issuecomment-6753444642)  
**SOURCE BASE //** `d5a76edadfdefbebfe7bf35bdbc806ff6bd31bdc`  
**PERMISSIONS //** Bounded GitHub source and CI-only test fixture, **no local Fedora writes**; no C3e/C4d Connections status host edits, C4b Silverblue lifecycle edits, C5 consent edits, merge, production activation or real provider login.

## IMPLEMENTATION

Previous merged milestones #1680, #1686, #1692, #1705 and #1710 implement real native BEGIN/STATUS/CANCEL/RECOVER, Ed25519-signed token-free command receipts, pinned independent native client, and an Identity-specific read-only signed Python entrypoint/process probe. The #1710 subprocess used a user-owned script, not a signed installed service. Per the protected Connections DOC handoff, the next milestone must measure **the actual installed Identity gateway**, not C4d's fake Connections status host.

This change adds four bounded artifacts:

1. **`services/identity/installed_gateway_witness_v1.py`:** A strict externally Ed25519-signed, purpose-scoped **installed Identity release manifest** pins package name/SHA-256, release epoch/sequence floor, transient unit name, all installed gateway Python module SHA-256 digests and **the specific receipt-signing Ed25519 public-key SHA-256**. `InstalledGatewayWitness` compares that independent manifest against the **actual dpkg-installed package**, nofollow/root-owned 0555 Python files, systemd `MainPID`/active unit/user/`ControlGroup`, kernel `/proc/PID/stat` start ticks, all UID/GID fields, kernel cgroup and current LSM label. Expected PID/start/cgroup/label/receipt-key values must be independently provided, never inferred from command JSON. Positive results are read-only observation with `production_authority:false`, `host_authenticated:false`, `can_begin_sign_in:false`, `can_connect_provider:false`.
2. **`tests/identity/fixtures/identity_gateway_installed_ci`:** A real installed **`IdentityCommandGateway`** entrypoint, bound to its original AF_UNIX command socket, using the actual installed Ed25519 `ReceiptIssuer`. The fixture will start only with explicit disposable GitHub-hosted CI guards. It **denies every peer, seat and operator-intent check**; its host_factory raises if any OAuth attempt is reached. It cannot launch browser login or provide credentials.
3. **`tests/identity/test_installed_gateway_v1_ci.py`:** A GitHub-hosted Linux controller builds a real disposable `.deb` from exactly the Identity gateway modules, computes module/package digests, generates separate ephemeral release-root and receipt-signing keys, verifies dpkg-installed root ownership, and launches a **transient systemd service** running the actual gateway as the nonroot runner. A separate test process measures the actual kernel and systemd peer/PID/start/cgroup/LSM, externally signs the release manifest, and verifies the host against existing `SignedGatewayOriginProbe` and new `InstalledGatewayWitness`. It sends real signed BEGIN/STATUS/CANCEL/RECOVER requests: all must return **signed UNAVAILABLE**, with no browser or display socket.
4. **`.github/workflows/identity-center-installed-gateway-v1.yml`:** Runs only on disposable GitHub-hosted Ubuntu with explicit CI guards, root installation through `sudo dpkg -i`, transient `systemd-run`, PINNED CI `cryptography` and existing signed gateway/CPU++ default-deny regressions. The test controller performs explicit `systemctl stop`, `dpkg --purge` and ephemeral-key/runtime cleanup. A final `always()` step checks for leftover installed entrypoint.

### V1 manifest completeness hardening (November 10, 2026)

The CI-only `installed-release.ci-v1` role has a **fixed eight-file roster**: its installed entrypoint plus the seven gateway Python modules. The verifier rejects even a correctly release-root-signed manifest that omits a mandatory module or adds an unexpected file; signature validity alone must not turn partial coverage into a complete installed-runtime measurement. The package builder independently checks its payload against the same roster, and CI includes omission/extra-file adversarial cases. This remains deny-only test evidence, **not** production attestation, C5 consent, or authority to enable CPU++ login.

### Adversarial acceptance covered

- Running **actual installed** gateway process and signed command receipt, with real kernel SO_PEERCRED, external systemd PID, package file/module hashes and current LSM/cgroup observations
- Wrong PID/start/UID/GID, wrong pinned release root, wrong cgroup/LSM, changed installed module mode/hash and tampered `.deb` artifact → witness refuses
- Host service stop/restart under a new transient unit and receipt-key rotation → previous PID/start, old signed release and old public key **cannot** authenticate new process/receipt
- Fresh independent CI enrollment for the replacement host and new key restores **read-only coherence only**, not user authentication
- All four actual native signed commands remain denied without real C5 consent, and no browser callback/authorization state can be created
- Every CI fixture package/socket/key/service must be removed before finishing

## HOW TO USE

**No desktop action.** Operator's CPU++ → SETTINGS → CONNECTIONS stays unchanged. Sign In, Cancel and Retry must remain disabled.

Reviewers use the dedicated GitHub Actions job; it is **not** a Fedora or Silverblue installation guide. Do not run the fixture outside a disposable GitHub-hosted test runner. Its keys and authorization inputs are simulated test data and are discarded. The CI installed package is purpose-scoped `post-apollo-identity-ci-fixture`, not the production Identity Center application package.

## VERIFY

The new workflow `.github/workflows/identity-center-installed-gateway-v1.yml` must pass exact-head with real dpkg/systemd/proc/Unix-socket evidence and proper cleanup. Existing default-deny CPU++ tests still run. Do **not** mark the installed-host milestone verified until workflow logs actually show all cases and teardown success; preexisting CI for #1710 does not verify this stage.

## WATCH OUT FOR

**This is not a real signed Silverblue deployment.** The test runner generates both ephemeral release-root and signer keys, builds the `.deb` and controls the witness pins. Its positive observations test consistency, not independent operator-enrolled authority, secure key custody, rpm-ostree boot/pinning, SELinux enforcing policy or signed running Python memory/modules. Linux `/proc/PID/cmdline` and on-disk Python hashes cannot by themselves prove loaded Python module memory integrity. A CI root-controlled release is **not** an independently signed production release.

The `installed_gateway_witness_v1.py` helper has *no permission-granting outputs*; it cannot provide a production positive callback on its own. Future C4b owner-reviewed Silverblue installation and independently witnessed same PID/start/systemd/SELinux/seat must replace test-only fixtures; C5 provides actual one-use operator gesture and provider-scoped consent. Sway compositor lock and real C5 consent are not present. No code path permits CPU++ QML to use the native client or accept experimental `AUTHENTICATED` as a grant. No live user/provider credentials are read.

The CI transient systemd unit and package are intentionally **different** from the protected Connections status host under C3e/C4d, so none of that lane's evidence can be relabeled as Identity Center trust. Host unit user and PINs are supplied by the **test controller**, not the service itself, and require an independent root/supervisor in production.

## CHECKLIST

- [x] Read Syntagma AGENTS/Hospital and direct DOC handoffs (#1662, #1710)
- [x] Verify main and distinct C3e/C4b/C5 owner PRs
- [x] Define externally signed package/modules/receipt-key/systemd PID/start/LSM/cgroup witness contract
- [x] Add real gateway-only disposable installed-service entrypoint with all human commands denied
- [x] Build root-owned dpkg package, transient systemd service, live Unix signed denial and replacement/key-rotation negative tests
- [x] Add no-residue cleanup and isolated CI workflow
- [ ] Exact-head workflow successful and any CI repairs complete
- [ ] Independent C3e/Identity security review of manifest/peer/key trust and no-silent-fallback
- [ ] C4b owner-approved real Silverblue unit/SELinux/rollback test
- [ ] C5 genuine one-use operator consent and reliable seat/lock proof
- [ ] Operator PR merge/acceptance and live native client integration
- [ ] First real approved personal login and provider authorization

## NEXT

**Run and repair the actual installed-gateway GitHub workflow** until all real package/process/signature/restart/seat/no-residue checks pass. Then request independent DOC C3e contract review of the installed release and same-PID/package/key witness. Ask C4b for a **minimal owner-reviewed Identity-specific Silverblue lifecycle fixture** rather than editing their existing C4d/Connections files. C5 must define real one-use operator gesture and seat binding separately. No CPU++ Sign In activation or live-machine write until all these independent gates and operator acceptance pass.

## DECISIONS

Follow the direct Identity Installed-Host V1 assignment without claiming new protected Connections ownership. All work remains in the Identity namespace and CI workflow. This PR is initially **draft** and must not be merged or activated by this worker without explicit operator authorization. External Hospital-compatible worker, not verified live Room attachment. Preserve test-only signing keys, installed-package cleanup, release-root provenance limitations and exact PR HEAD in subsequent checkpoints.

**RECOVERY //** This document, Identity V1 PR/branch, [coordination #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662#issuecomment-6753444642), merged enrollment [#1710](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1710).
