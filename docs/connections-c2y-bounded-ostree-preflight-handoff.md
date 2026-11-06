# 🏥💜 Connections // C2y Bounded RPM-OSTree Preflight Recovery

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Universal Connections · CPU++ SETTINGS
STAFF ROLE // Hospital-compatible external doctor, OPEN AI // CHATGPT; no live Hospital registration verified
ASSIGNMENT // Close pre-install diagnostic hang and enforce real immutable deployment and rollback checks
BASE // main 7c43cee22639d47031e2a51a718c7dbf7dc1b766 (C2x #1383 merged)
PERMISSION // GitHub draft PR and disposable CI only; no workstation edits or production activation

## IMPLEMENTATION

C2x PR #1383 merged on November 6, 2026, while its Silverblue full test remained FAILED (run 42282318917, job 128114192039). The official Ubuntu mirror fixed QEMU setup; the official Fedora 44 Silverblue ISO hash, installation, boot, offline C2VCI media and enforcing SELinux baseline passed. The guest printed C2V_RPM_OSTREE_VERSION and the first 1800 bytes of the unbounded rpm-ostree status --json diagnostic, but NEVER logged the expected install watchdog or a bounded rpm-ostree install command outcome. The host's 900-second guest monitor timed out without the required package layering and reboot proof.

C2y copies only the unmerged diagnostic corrections from the old branch into a new branch based on the verified main after #1383 merged. A former unbounded pre-install rpm-ostree status --json pipeline is replaced with a 15-second, kill-after-5-second diagnostic; it records success/error/timeout markers and a bounded excerpt rather than blocking indefinitely. Failure-time status inspection also gets a timeout. C2V_INSTALL_COMMAND_BEGIN is now emitted immediately before the original 480-second real local RPM install. GitHub CI statically checks these markers and bounds. All upstream tests, the official Fedora ISO pinned hash, no guest network, SELinux Enforcing, and two actual reboot proof conditions remain required.

## HOW TO USE

None on your desktop. The PR's GitHub runner builds a temporary signed inert RPM, boots an ephemeral Fedora Silverblue 44 guest, and reports diagnostic/reboot status in CI.

## VERIFY

First verify the official Ubuntu runner provisioning, Silverblue ISO hash, successful Fedora 44 guest first boot, offline media, and PRECHECK_BEGIN followed by PRECHECK_SUCCESS or PRECHECK_TIMEOUT_OR_ERROR. Then the guest must log INSTALL_COMMAND_BEGIN and either INSTALL_RETURNED_SUCCESS or a bounded INSTALL_FAILED_EXIT with journal and disk diagnostics. Only a booted layered package after the first reboot AND absence after rpm-ostree rollback --reboot count as complete acceptance. Do not infer success from only the static validate checks or a merged pull request.

## WATCH OUT FOR

This is a diagnostic boundary fix, not a demonstrated solution to offline rpm-ostree cache composition. If the real installation fails or stalls, stop and use its failure evidence to design a constrained next change. Do not enable networking inside the guest, weaken SELinux, install software on the operator's desktop, or turn on shared Connections credentials. The RPM fixture and signing identity are disposable and inert.

## CHECKLIST

- [x] Verify merged #1383 and latest main, no other open Connections PR
- [x] Reconcile exact failed Silverblue CI
- [x] Isolate old branch's post-merge changes in a new branch
- [x] Bound preinstall status query and failure inspection
- [x] Preserve strict two-reboot rollback assertions and add CI regression checks
- [ ] Verify full CI on exact new head
- [ ] Review any actual offline rpm-ostree failure and independently verify successful rollback
- [ ] Obtain operator acceptance; no merge or production enablement by this worker

## NEXT

If new CI fails, identify its first failed guest marker and inspect rpm-ostreed journal before changing the solver, offline metadata, test-media provenance, or deployment layer. Keep ownership and recovery pointers in this PR.

## DECISIONS

Draft review only, no live Hospital connection, no operator workstation writes, API keys, credentials, TASKS edits, provider calls, signed production package, or production grant.
