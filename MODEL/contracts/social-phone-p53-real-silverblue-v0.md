# Social PHONE P53 // Official Fedora Silverblue signed RPM, process and rollback test

**Patient** `kudokudo1/The-Post-Apollo-Project`  
**Staff role** external Hospital-compatible PHONE DOC; live Room/Assignment/Session not verified.  
**Base** P52 [PR #1991](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1991) is OPEN DRAFT, signed Fedora container build/install/erase 2/2 CI passed at `576176024c332820716945f06b37503bd5ab9206`. P53 branch stacks on it, **PR targets `main`**. Review/merge P52 before P53; verify actual files on main.  
**External owners** C4b Identity [PR #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) and C3e-AC [PR #1978](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1978) are merged, but neither grants production PHONE trust, external challenge or human consent. PHONE issue #1885 remains open.

## IMPLEMENTATION

P53 extends the genuine signed PHONE-only RPM from P52 to the **official Fedora 44 Silverblue OSTree guest boot** workflow, modeled after C4b's proven boot mechanics, but with *distinct PHONE-owned scripts, SELinux test domain and keys*. It does not modify C4b, C3e or C5 code.

- `tests/phone/p53_run_official_silverblue_phone.sh` is a GitHub-only KVM controller. It requires GitHub-hosted CI, the authorized GitHub actor, `/dev/kvm`, a signed P52 RPM and a compiled PHONE policy. It downloads the exact official Fedora 44 Silverblue ISO with the previously verified pinned SHA-256, extracts its installer, generates a temporary offline Kickstart seed, creates a 40 GiB ephemeral QCOW2, boots the installer with **`-nic none`**, and boots the actual installed Silverblue guest with the same network denial. A bounded host serial watcher refuses guest error markers, missing stage transitions, missing policy-load progress, repeated evidence and missing full two-boot rollback. No raw private user data, key, environment token or note is exposed.
- `tests/phone/p53_guest_phone_ostree_cycle.sh` runs only inside that official offline Silverblue guest under enforcing SELinux. It demands the official OSTree deployment and Fedora 44, absent pre-existing PHONE RPM/marker, an independent isolated RPM key database initially lacking the disposable PHONE signer and valid signature only after explicit public-key import, then disables all network repositories. It uses a **separate systemd `rpm-ostree` composition worker and independent monitor**. The monitor demands `rpm-ostree status --json` show an exact pending `post-apollo-phone-status-ci-0.1-1.fc44.noarch` before rebooting.
- On the next genuine boot, the guest requires the RPM in its booted database, exactly six root-owned P47-P50 + unit files, `rpm -V --nomtime` clean, package ownership and a static unenabled unit without the test marker. The separate native guest service probe then validates real systemd/PID/UID/GID/SELinux/socket/STATUS. It must remove its service, ephemeral user, runtime, override and SELinux policy *before* rollback.
- `tests/phone/p53_selinux/postapollo_phone_ci.te` and `build_policy_ci.sh`: **new distinct PHONE-specific**, nonpermissive test-only daemon domain `postapollo_phone_ci_t`, executable transition type and `postapollo_phone_ci_run_t` runtime type. It supports a supervised nonroot Python STATUS-only Unix socket, requires `NoNewPrivileges=true`, and includes no TCP/UDP/unconfined grants. Compiles in disposable Fedora; module is loaded only in the offline guest and removed after the probe.
- `tests/phone/p53_guest_phone_service_probe.sh`: verifies the installed signed PHONE systemd unit remains inert without an explicit test marker. In that offline guest only, it installs the compiled PHONE test policy, creates an ephemeral dedicated service account, exact byte-identical **temporary labeled Python entrypoint** and service override (leaving RPM files unmodified), starts the existing P49 STATUS-only service, checks actual systemd MainPID, kernel fourfold UID/GID, cgroup, 0600 Unix socket, and enforcing `system_u:system_r:postapollo_phone_ci_t:s0`. A same-UID client may only receive `HOST_UNTRUSTED_STATUS_ONLY` with all production, consent, key and save flags false; a cross-UID client must fail closed. Stop, cleanup and policy unload are mandatory before returning.
- After successful probe, the guest calls **real `rpm-ostree rollback --reboot`**. Its third observed stage (initial boot, layered boot, rollback boot) must prove the PHONE package and all six installed files absent, no service marker, domain or runtime override, and deletion of the separately imported test signer/cache. This is two actual VM reboots, not ordinary Fedora `rpm -e`.
- `PhonePersonalStatusHostP49.py`: narrowly permits immutable **root-owned 0555 source files within the exact installed `/usr/libexec/post-apollo/phone` path** to have legitimate OSTree content-addressed hardlink counts above one. It still refuses mutable/symlinked/wrong-user source and does not change P47 or the UI.
- Source guard `test_phone_personal_silverblue_p53.py` and dedicated 75-minute official KVM workflow test real signature/policy compilation + offline install/rollback. The VM test must be **explicitly verified green at the P53 commit**. Passing only static checks or a status marker without completed boot evidence is insufficient.

## HOW TO USE

Nothing is installed or altered on your workstation. The systemd unit is static and has no `[Install]` target; the test marker, service account, SELinux module and package signer exist only in disposable GitHub/Fedora environments. Never run guest scripts on the live Silverblue host. No private contact, phone connection, keyring or real Favorites/Notes save is performed.

## VERIFY

Check separate P53 workflow jobs, inspect its genuine KVM serial markers and the final explicit `P53_PASS // OFFICIAL_SILVERBLUE_SIGNED_PHONE_RPM_CONFINED_SERVICE_TWO_BOOT_ROLLBACK` only if the entire boot sequence completed. The guest must independently show signature untrusted before test-key import, pending deployment before first reboot, installed P52 payload/SELinux process identity, successful STATUS-only service, cleanup and package absence after rollback. A fail/timeout/block is NOT a pass.

## WATCH OUT FOR

- The CI RPM signer is disposable and public key import is **not operator-controlled independent release root enrollment**. A real enforcing domain in an ephemeral guest, if verified, is still **not production host authenticity, active logind human seat, C3e externally held one-use challenge, or C5 signed PHONE per-action human intent**.
- P49's Python imports occur before optional P50 caller-key verification. Genuine production needs independently pinned pre-execution package trust and a signing floor held outside the package. P53 test source hardlinks are allowed only when root-owned in the exact installed path; this does not grant authority.
- The user-visible QML SAVE remains hard-false. P35 AES-GCM local vault and P44 two-action transactional tests have not been connected to a trusted service with a host-held one-action lease and actual C5 consent. **Never convert P53's success markers to production key or write permission.**
- This is a 75-minute maximum **real VM test**, not an assumption of success. It must be inspected at the exact commit before claiming completion. CI may reveal Fedora/OSTree/SELinux differences requiring bounded follow-up work; do not weaken the necessary gates to make it green.

## CHECKLIST

- [x] Verify P52 still open/green and current Syntagma/Hospital/owner boundaries.
- [x] Add PHONE-only offline official Silverblue KVM controller and exact signed RPM package stage.
- [x] Add dedicated PHONE SELinux test module/compiler and installed STATUS-only service probe.
- [x] Add real pending OSTree, booted package, separate service cleanup and two-reboot rollback checks.
- [x] Handle immutable, root-owned OSTree source hardlinks without changing save authority.
- [ ] Dedicated P53 real KVM workflow completed and exact-head CI verified; independent review.
- [ ] Operator review/merge P52 first and P53 second; verify final mainline source.
- [ ] Independently enrolled PHONE release root/signer, immutable installed pre-execution host identity, actual logind seat/lock and rollback floor.
- [ ] Genuine C3e one-use challenge/consume/revoke and C5 signed PHONE one-action consent bound to P41b `editHmac`.
- [ ] PHONE Secret Service key custody/rotation/erase, nonforgeable lease across P35 encrypted CAS/fsync/readback; truthful UI SAVE and native operator acceptance.

## NEXT

**Integrate independently authenticated PHONE installed release authority and genuine C3e/C5 consent**, rather than introducing another synthetic signed receipt. Only after that should PHONE implement the actual protected key lease and save/readback path and enable the existing CONTACTS editor SAVE. If P53 real VM CI fails, repair that exact physical installation/rollback evidence first before calling the host installed.

## DECISIONS

External Hospital-compatible PHONE DOC. No live Hospital registration claimed; no production activation, local computer edits, Quickshell reload, keyring enrollment, private user contact write, C4b/C3e/C5 owner file modification, merge or final acceptance. All changes are reviewable GitHub source and CI-only VM paths.
