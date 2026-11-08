# 🏥💜 C2v → C4b // Real Silverblue rollback-command error evidence (draft)

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · C2v Silverblue rollback / C4b dependency  
STAFF ROLE // External Hospital-compatible DOC (no live registration claimed)  
ASSIGNMENT // Isolated, failure-only diagnostic proposal for C2v owner review  
C4b IMPLEMENTATION // [PR #1555](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1555), merged at `bb68168c627bfc60304da5ee4b38f28d8d0535bb`  
C2v OWNER ISSUE // [#1568](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1568)  
PRODUCTION // HOLD

## IMPLEMENTATION

The last real [official Fedora Silverblue 44 C4b run #42511961729](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42511961729) passed C3b independent D-Bus/PID/UID/systemd/SELinux OS origin, signed confined fake host, unauthorized/negative client checks, explicit D-Bus-name release, all three test users/groups absent, and venv cleanup. The guest entered `BOOTED_RUNTIME_ACCEPTED` and the runtime controller exited `rc=0`.

It subsequently failed the shared C2v controller's `rpm-ostree rollback --reboot` command before the actual **second real reboot**. The independent serial relay showed `C4B_DIAG_CONTROLLER_FATAL // RPM_OSTREE_ROLLBACK_FAILED`, but **not** the rollback command's exact stderr or numeric exit code. No rollback-completion or signed-policy/keyring removal markers were produced.

This draft changes only the C2v controller's narrow **failure-evidence seam**, its static test and the C4b CI preflight wiring:

1. Preserve the genuine original `rpm-ostree rollback --reboot` invocation in the correct `layer_pending` branch, with `rollback_pending` written before requesting the reboot. Redirect only the command's combined stdout/stderr to a root-owned `/run` log; if it fails, retain the exact numeric return status.
2. On nonzero return, capture the command output, bounded *read-only* `rpm-ostree status --json`, `ostree admin status`, systemd unit state and rpm-ostreed/c2v journals. Save them under `/run` and relay a size-limited report to the primary serial and, for opt-in C4b, independent UART1.
3. Always proceed to the original fatal `failure "RPM_OSTREE_ROLLBACK_FAILED"` path on command failure. A zero command result emits only a diagnostic note that the **second actual boot is still required**, not a C2v PASS.
4. The existing `rollback_pending)` branch still demands a genuinely booted clean RPM-OSTree deployment, absence of layered fixture, signed fake service and policy package, custom SELinux module/trust and service/users, and strict SELinux Enforcing before host-side success.
5. New static adversarial checks prevent a rollback bypass, synthetic success, unbounded diagnostic reads or any false-positive acceptance marker. Original C3b/C3c, C3d, C4b signed service, production credentials/permissions and SELinux logic are untouched.

## HOW TO USE

Review this **draft** under C2v/C2z ownership in [issue #1568](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1568). Its complete C4b workflow is deliberately the same **real signed, offline Silverblue two-reboot VM**, not a mocked rollback. If CI reproduces the fault, inspect the `C2V_DIAG_ROLLBACK_*` markers on UART0/UART1 and identify the contemporaneous code, error, transaction, systemd service state and journal before proposing a change to the actual rollback command or its timing.

The source of truth remains the GitHub Actions exact-head run. These diagnostics are **not** proof that rollback passed.

## VERIFY

- [x] C4b signed host and first-boot real origin/cleanup previously passed.
- [x] No C3b/C3c, C3d, C4b guest, SELinux policy, production or workstation code edits in this branch.
- [x] Existing rollback command, stage checkpoint and post-second-boot acceptance gates preserved in source.
- [ ] New exact-head preflight and grammar pass.
- [ ] Real signed VM reproduces the rollback failure **with exact return code and command error** or proves that the rollback now works.
- [ ] C2v owner reviews evidence and authorizes any attributable follow-up fix.
- [ ] A complete new real 2-reboot VM proves clean deployment and removal of signed RPMs, custom SELinux policy, trust assets, files, users/groups with no production activation.
- [ ] Operator final technical acceptance after all verification.

## WATCH OUT FOR

A raw `rpm-ostree rollback --reboot` might itself initiate a poweroff/reboot before returning. The zero-return path never grants C2v acceptance; only the second boot's exact absence checks and final host acceptance can do that. The diagnostic probes use bounded read-only calls and are only executed after a **nonzero** rollback result. They are not installation or recovery actions, and cannot authorize a service or reboot.

C2v/C2z owner boundaries remain in force. No attempt to reverse merge #1555, no local Silverblue changes, no unbounded repeated CI retries, and no merge of this draft as a fix before owner review and evidence.

## CHECKLIST / NEXT / DECISIONS

[x] Recover current merged C4b and C2v control state.  
[x] Isolate a failure-only C2v diagnostic branch for owner review.  
[x] Add fail-closed source regressions and C4b preflight.  
[ ] Inspect exact-head CI and UART failure evidence.  
[ ] C2v owner disposition and, if indicated, minimum correction.  
[ ] Real Silverblue rollback PASS and operator technical acceptance.  

DECISIONS // This branch is a **draft diagnostic**, not a C2v ownership transfer, a release fix, or an acceptance claim. Production HOLD.
