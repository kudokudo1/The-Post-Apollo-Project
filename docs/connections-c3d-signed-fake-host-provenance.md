# 🏥💜 Universal Connections // C3d signed fake-host package provenance

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · protected package provenance  
STAFF ROLE // Nurse 2 · NRS-2, external Hospital-compatible; live Hospital registration NOT verified  
ASSIGNMENT // Connect the C2t signed-RPM mechanism to the C3b/C3c *running fake service* test in an offline Fedora 44 guest  
BASE // `c8d8b25eb7369e27733620095301b6f4c37fcc6f`  
PERMISSIONS // GitHub-only branch, disposable CI, tests, docs; no workstation, credentials, production activation, or merge

## IMPLEMENTATION

C2t proves Fedora native RPM OpenPGP signature verification and rollback for an *inert data-only* status fixture. C3b/C3c prove that a *manually installed* fake status process has consistent systemd, D-Bus, UID/PID, cgroup, SELinux and path ownership evidence. Neither alone proves the *running* fake status files are owned by an installed, integrity-checked RPM.

C3d connects these two already tested seams **without promoting the fake service into production**:

1. `tests/connections/c3d_provenance/signed-status.spec`: packages exactly three existing fake service files into the intended executable, systemd unit, and D-Bus policy locations. The package has no install/remove scriptlets, no automatic service start, no SELinux module installation, no users, keys, or provider access.
2. `build_signed_ci_status.sh`: a disposable Fedora 44 builder creates a throwaway OpenPGP key inside its own container, signs the fake RPM with `rpmsign`, and exports only one signed RPM, its **public** key, a test fingerprint and a SHA-256 manifest. Its private key is destroyed with the container.
3. `guest_signed_service_gate.sh`: in the offline enforcing Fedora Cloud guest, verifies signer untrusted before import; validates the complete payload path allowlist; validates the package's native signature after importing its disposable public key into the **guest-only** rpm trust store; uses native `rpm -Uvh` to install the three files; requires exact rpmdb file ownership and `rpm -V` integrity; deliberately modifies the fake executable and requires RPM verification to refuse it; reinstalls the signed test RPM to restore it; checks installed file integrity again **while the fake host is running**; and, after systemd stops and releases D-Bus ownership, erases the fake RPM and the temporary test signer key.
4. The already reviewed `C2r` enforcing Fedora VM driver gains an **explicit opt-in** test-artifact path. The dedicated C3d workflow stages the signed fixture and requires a C3d cleanup success marker on serial. Normal C2r and C2s runs keep their existing manually staged fixtures and cannot claim C3d provenance.
5. The dedicated CI tests the C3d source/permission contract, the existing C3b/C3c identity checks and the C2n deny-only policy before exercising the full Fedora guest.

The existing fake host still has only read-only GetStatus D-Bus access; C2r's custom SELinux confined domain, NoNewPrivileges and negative shadow_t file denial are preserved. Production QML and credential broker source is untouched.

## HOW TO USE

No action on the operator's desktop. `.github/workflows/connections-c3d-signed-fake-host-vm.yml` is GitHub-only and gated to the owning repository/operator context. It uses a temporary Fedora builder, a disposable Ubuntu GitHub runner with KVM, and the exact official Fedora Cloud 44 guest image SHA-256 already used by C2r. The guest runs with `-nic none`.

The test signer public key is imported **only into the guest's throwaway RPM trust database**, not the workstation or a production signing store.

## VERIFY

For the exact PR head, require:

- [ ] Source tests, bash syntax, package allowlist and disable-only broker assertions pass.
- [ ] Temporary signing key is isolated inside the builder; native RPM header carries a valid OpenPGP signature.
- [ ] Enforcing, offline Fedora guest rejects the signature before public-key import and recognizes it after *test-only* import.
- [ ] Signature-checked RPM contains exactly the three allowlisted fake service paths and no scriptlets/triggers.
- [ ] Native RPM installation does **not** automatically activate the service.
- [ ] `rpm -qf` and `rpm -V` establish exact installed file ownership and package integrity.
- [ ] Deliberate executable tampering fails `rpm -V`, and reinstall of the signed test package restores it.
- [ ] Explicitly started fake service passes all C3b/C3c D-Bus/systemd/PID/UID/cgroup/SELinux checks.
- [ ] Running fake host's installed files still pass native rpmdb ownership and integrity checks.
- [ ] Stopping the service releases D-Bus; RPM erase removes protected fixture files; the guest signing key is removed and the prior RPM trust set is restored.
- [ ] Existing C2r/C2s tests remain separately valid; no production grant is changed.
- [ ] Independent security review and operator merge decision.

## WATCH OUT FOR

**The builder is its own ephemeral signer.** The guest imports that same builder's public key and therefore tests cryptographic *mechanics*, not an independently verified production release authority. The SHA-256 manifest is transported beside the package, not through a separately trusted root. A compromised builder or test bundle could change both. This cannot prove Post-Apollo release authenticity, secure key custody, rotation, transparency, or update policy.

`rpm -V` compares files against the rpmdb, not the bytes currently executing inside a Python interpreter. C3d tests the file immediately before startup and during execution, and C3c checks its command path, but does **not** cryptographically attest in-memory running code. An already privileged/root-compromised system remains out of scope.

This is a *mutable Fedora Cloud guest*, **not** the C2y/C2z Silverblue rpm-ostree two-reboot recovery proof. It uses a fake read-only status server with zero real secrets, network, provider requests, consent, or user identity. Production activation and authenticated per-app grants remain prohibited.

## CHECKLIST

- [x] Recheck current main, open ownership, C3c merge, C2t and C2r fixtures.
- [x] Reuse existing fake host, narrow systemd unit and D-Bus policy.
- [x] Add signed fake-service package builder with a temporary key.
- [x] Add native rpmdb ownership, signature, tampering, repair and cleanup gates.
- [x] Add opt-in C2r guest staging, a dedicated workflow and static deny-only checks.
- [ ] Verify exact-HEAD CI, including both actual signature and running service tests.
- [ ] Independent technical/security review and operator acceptance.
- [ ] Later production-grade trust-root provisioning, signed artifact distribution, key rotation, and fully tested Silverblue activation/rollback.
- [ ] Later authenticated consumer identity, operator consent and revocation.

## NEXT

Inspect full GitHub CI evidence. Address concrete builder/guest errors with minimal changes without weakening the signature requirement, SELinux domain, file allowlist or denial-only broker. Submit a draft PR with final exact-head logs and leave merge/production decisions to the operator.

## DECISIONS

No local desktop writes or installations, no permanent keys, no API credentials, no Social/TASKS changes, no real NASA traffic, no live Connections authorization, and no PR merge. GitHub test development only.
