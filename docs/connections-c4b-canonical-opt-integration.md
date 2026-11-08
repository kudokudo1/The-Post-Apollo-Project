# 🏥💜 C4b // Canonical Silverblue `/opt` origin integration, staged

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · C4b signed confined Silverblue fake status host  
STAFF ROLE // External Hospital-compatible DOC, no verified live registration  
ASSIGNMENT // C4b-owned integration with independently guarded C3b/C3c origin selector  
OWNER DEPENDENCY // [C3b/C3c PR #1553](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1553)  
GOVERNING DECISION // [Issue #1532 correction](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532#issuecomment-6724841170)  
STATE // STAGED ONLY, not a passing real VM, production HOLD

## IMPLEMENTATION

The real official Fedora Silverblue 44 C4b run [#42500764517](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42500764517) proved that `/opt` is a root-owned symlink with literal target `var/opt` resolving to `/var/opt`, and both `/var` and `/var/opt` are genuine root-owned `0755` directories. The original C3b verifier failed closed at `C3C_UNPROTECTED_DIRECTORY`. It also proved signed immutable executable labeling, SELinux Enforcing and confined fake-service negative file access. It did **not** complete service-origin or rollback.

The C3b security owner initially explored physical interpreter relocation, but corrected that design after confirming the C3d-signed executable has the original `#!/opt/postapollo-c2o-venv/bin/python3` shebang. A C4b-only derivative signed executable was **not** authorized as the accepted C3d source. [Physical PR #1551](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1551) was closed without merging. The owner chose a separately gated, CI-only canonical Silverblue link profile in [#1553](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1553).

This **C4b-owned integration branch** changes only the disposable guest's existing C3b invocation to request `--verify-disposable-silverblue-opt`, with `GITHUB_ACTIONS=true`, `POST_APOLLO_C3B_TEST_GUEST=1`, and `POST_APOLLO_C4B_TEST_GUEST=1`. The C3b owner checks these alongside the real guest mode marker, official Fedora Silverblue 44, OSTree boot/ref, offline network and an independently observed exact canonical path. A failed owner check still fails the C4b runtime and blocks rollback acceptance.

C4b's source contracts additionally require the exact independently owned C3b selector and canonical path source, and verify the tracked original C2r host shebang, original signed systemd unit and the absence of the derivative source overlay. C4b does **not** edit `tests/connections/c3b_origin/C3bOriginCheck.py`, C3d/C2r source, SELinux policy or any production file.

## HOW TO USE

1. The C3b/C3c owner completes technical review and merges #1553. No C4b worker merges owner-controlled source solely to unblock a test.
2. Reconcile this staged C4b branch onto the exact new `main` containing the reviewed C3b source. Require source-contract and original C2r Fedora CI to remain green.
3. Run the complete C4b CI workflow using the **unchanged original C3d signed RPM** in the real offline Fedora Silverblue VM, with first reboot, exact service-origin PID/UID/SELinux/D-Bus/cgroup/argv check, strict negative file and client permissions, explicit service shutdown/cleanup and second real OSTree rollback reboot.
4. Prove original package, custom SELinux policy/module, keyrings, service files and test accounts were removed on rollback. Only then seek final operator technical acceptance.

## VERIFIED REAL-VM FAILURE / CLEANUP CORRECTION

The first integrated [C4b run #42508631401](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42508631401) passed the independently observed **C3b OS D-Bus/PID/UID/systemd/SELinux origin** proof (`C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY`), exact read-only and rejected-client calls, SELinux Enforcing, signed confined host, negative dummy-file denial, and explicit service stop/D-Bus-name release. This **resolves the original `/opt` ancestry security blocker** in the real official Silverblue 44 VM, but the complete C4b workflow failed later with `C4B_FAIL // TEST_GROUP_REMOVAL_FAILED`.

The actual guest console line was `groupdel: group 'postapollo-connections' does not exist`. Fedora's `userdel postapollo-connections` had already automatically removed that account's private primary group. This is a cleanup idempotence problem, not an origin-authentication failure. C4b now requires the two other explicitly created test groups to be deleted successfully, conditionally deletes the service primary group **only when still present**, and immediately calls `check_accounts_absent` to reject any surviving service user or test group before marking the guest runtime complete. New source regression tests lock this sequence in place; no source/security checks or default policy are weakened.

**Not yet verified:** this corrected source must pass exact-head CI, then the real guest must finish runtime cleanup and its **second real OSTree rollback reboot**, including removal of the signed policy/service RPMs, custom SELinux module, test keyrings and users. The earlier failing VM does not prove that rollback.

## VERIFY

- [x] Confirm exact C3b owner CLI, environment flags and strict path policy in draft #1553.
- [x] Implement the matching C4b-owned invocation, preserving fail-closed behavior.
- [x] Add static source checks against a derivative signed executable or a fabricated C3b origin.
- [ ] C3b owner PR #1553 merged and accepted on `main`.
- [ ] C4b exact-head static/source and real VM tests PASS.
- [ ] Full signed service identity, client negatives, actual second reboot and rollback prove cleanup.
- [ ] Operator final technical acceptance.

## WATCH OUT FOR

The staged C4b branch alone **cannot pass** its newly added source guards while the C3b owner source remains unmerged. Deliberately do not treat a failing premature branch CI as evidence that the canonical policy is unsafe. Do not copy C3b code into the C4b branch to game CI. The synthetic threat-model [PR #1545](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1545) remains pure synthetic evidence and is not an origin authority.

No production authentication, provider credentials, API grants, systemd drop-ins, SELinux relaxation, `/opt` modification, immutable `/usr` edit, workstation change, real provider traffic or release-signer enrollment is permitted.

## CHECKLIST / NEXT / DECISIONS

[x] Reconstruct latest GitHub status and owner boundary.  
[x] Stage C4b-controlled canonical-profile invocation and original-package protection.  
[ ] Wait for owner-accepted C3b profile, then rebase/source-verify.  
[ ] Run complete real C4b Silverblue CI and close any actual additional blocker.  
[ ] Merge accepted C4b correction under standing GitHub authorization.  

DECISIONS // Staged as a branch, with no PR yet, to avoid launching a guaranteed red VM against old C3b `main`. Production HOLD; final technical acceptance is operator-owned and not implied by merging.
