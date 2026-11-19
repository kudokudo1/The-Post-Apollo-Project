# 🏥💜 Connections C4b → C3e-AG // Actual official Silverblue gateway process observation

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** C4b Identity Silverblue · real signed RPM / official Fedora guest origin  
**STAFF ROLE:** Operator-authorized external Hospital-compatible DOC successor returning to C4b assignment; live Hospital registration not verified.  
**PREREQUISITES:** Previously merged [C4b #2044](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2044) controller-policy intake, [#2046](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2046) C3e role alignment and merged C5-H2 Hospital native signer [#2056](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2056) (separate owner/scope).  
**DEPENDENCY HANDOFF:** [C4b/C3e issue #2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018).  
**CURRENT TRUST:** **CI-only diagnostic, all production authorizations false.**

## IMPLEMENTATION // Real OS process, not a mocked host

C4b's existing Fedora 44 KVM executes the **genuine offline official Silverblue image**, verifies its signed Identity RPM and offline cryptography RPMs, boots into enforcing SELinux, installs/starts the inert deny-only gateway and verifies its real Ed25519-signed BEGIN/STATUS/CANCEL/RECOVER UNAVAILABLE receipts with real kernel `SO_PEERCRED` and a fresh external controller nonce. It then uninstalls the package/ephemeral SELinux assets, reboots and requires a clean second-boot rollback.

Before this change, the protected C3e-AG kernel verifier had passed real Linux `/proc` tests only on a separate Ubuntu fixture. It had never been invoked against **the same actual installed Fedora gateway** during that real C4b boot.

This change keeps the original C3e-owned file **unchanged** and only modifies C4b-owned guest harness/probe:

1. The existing offline image seed includes a copy of `tests/connections/c3e_release_trust/C3eAGIdentityKernelObserver.py` at root-owned `/usr/local/libexec/postapollo_id_ci_c3eag_observer.py`, mode `0444`. It contains no private signing seed and is **not** part of the production RPM or a persistent system service.
2. After C4b's original four verified signed denials and guest-local release/actual receipt-key consistency check, while the exact original systemd MainPID is **still running**, the root-only probe imports that unmodified C3e module under its strict existing `mode="c4b-guest-candidate"`.
3. Passes expected signed-package/script and kernel-process *guest diagnostics*: exact gateway unit, actual MainPID and start ticks, nonroot UID/GID, root-owned copied Fedora Python interpreter SHA-256, RPM-installed gateway script SHA-256, exact cgroup and enforcing SELinux context. The observer independently checks real `pidfd_open`, `/proc/PID/exe`, script inode, process command line, UID/GID, cgroup, SELinux and systemd MainPID both before and after observation. The hash values come from the installed guest filesystem **after the source-owned signed-RPM verification**; they are not externally signed host-enrollment pins.
4. Requires actual observation candidate true and **every authority flag false**. Wrong PID, start tick, service UID, interpreter hash and script hash are explicitly rejected by the actual kernel observer, without changing the installed service.
5. Emits only the two fixed bounded public CI markers after actual positive/negative observation:
   - `C4B_ID_PASS // REAL_C3EAG_RUNNING_GATEWAY_KERNEL_SNAPSHOT`
   - `C4B_ID_PASS // REAL_C3EAG_MUTATED_KERNEL_AND_SCRIPT_PINS_REFUSED`
6. The existing Fedora host's rollback acceptance now **requires exactly one of each marker**, in addition to its unchanged four signed denials, controller-signed fresh nonce proof, enforcing SELinux, cleanup and two-reboot rollback requirements. The observer runs before `systemctl stop` and never survives the ephemeral guest. No private key/public grant is exported.

### What this proves and does NOT prove

It proves a **real instance-level compatibility test** between C3e's existing process observer and the actual booted C4b gateway, with strict process-continuity and substituted-input refusal. It is stronger evidence than a pair of unrelated Ubuntu/guest fixtures because the same PID, cgroup, SELinux domain and installed script are inspected while the original signed deny-only service runs.

It still **does not prove authenticated remote host authority**. The test's expected snapshots are read from the guest, and the guest itself can emit UART markers. The verifier root and signed receipt public key are not enrolled by an independently controlled operator authority. The original host controller's public nonce establishes freshness, not remote machine identity. This new C3e-AG observation is not an attestation signed by a protected externally trusted witness. It cannot establish independently protected root custody, revoke/rotate authority, one-use C5 human consent or live sign-in. No `hostAuthenticated`, credential release, production or operator-authorized flags change.

## HOW TO USE

No workstation action. The existing `.github/workflows/connections-identity-silverblue-real-boot.yml` executes the official Fedora KVM, now with C3e-AG observation required during its guest. A small fast `.github/workflows/connections-c4b-real-guest-c3eag-observer-ci.yml` runs 12 C4b boot-wiring refusal/source cases and the existing C3e-AG 25 real Linux process tests before the costly official VM finishes.

The upstream `C3eAGIdentityKernelObserver.py` itself is not edited. This is a C4b-owned producer/use-site change, not C3e verifier ownership transfer.

## VERIFY

- [ ] 12 new C4b owner seam/source and Python probe syntax tests pass
- [ ] 25 existing actual Linux kernel observer refusal tests pass unchanged
- [ ] Official Fedora 44 Silverblue real KVM explicitly runs C3e-AG against original live service before teardown
- [ ] Two new diagnostic markers each appear once only after positive observation and 5 substituted-input refusals
- [ ] Original fresh controller nonce proof, signed RPM, four denials, SELinux negative test and two-reboot rollback still PASS
- [ ] All workflow checks at exact head pass
- [ ] Independent Nurse 2 security and source review; operator merge approval

## WATCH OUT FOR

- The guest's `GITHUB_ACTIONS` and `RUNNER_ENVIRONMENT` variables are **deliberate test-only simulated metadata**, not independent CI authority on the installed machine. Do not expose the guest observation as protected C3e admission or as `hostAuthenticated`.
- The expected hashes originate from the already checked **installed guest files**. Only a separately controlled root-backed signed release mapping plus independent protected host/seat witness can turn them into a trustworthy cross-machine binding.
- Do not modify the C3e observer to loosen exact script, executable, SELinux, root-owner, PID or process rules if the real guest test fails. Diagnose the exact kernel source mismatch and seek the protected C3e owner before any semantics change.
- No private root key copies in the RPM/ISO, no production credential, no network, no local host changes, no QML permission toggles and no permanent Burn or Hospital source changes.

## CHECKLIST

- [x] Re-read current Syntagma AGENTS/Hospital/authority rules, verify merged #2044/#2046/#2056 and no competing open C4b branch
- [x] Use existing unmodified C3e-AG source and guest-root diagnostics while original C4b service is active
- [x] Retain original C4b exact signed denial, controller nonce, SELinux and rollback checks
- [x] Add explicit wrong-process/script/hash negatives and separate fast/real guest verification workflows
- [ ] GitHub exact-head checks and official KVM PASS
- [ ] NRS-2 independent audit and operator merge acceptance
- [ ] Operator-approved external root/key custody, revocation, actual release-to-process/seat attestation and eventual C3e/C5 production integration

## NEXT

Once the real official VM confirms that the identical C3e-AG source can inspect the installed service, provide the C3e owner the exact diagnostic record/contract in [issue #2018](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2018), and request independent review. The remaining fundamental work is protected **outside-the-guest root enrollment, host/seat witness and revocation**, not more synthetic process simulations. Do not start a parallel issuer implementation without an operator custody decision.

## DECISIONS

The operator retains final authority. No merge, installed signing roots, protected C3e source edit, local machine mutation, production Identity sign-in, human consent grant or new Hospital work. Passing the real Silverblue regression establishes only the tightly described diagnostic seam.
