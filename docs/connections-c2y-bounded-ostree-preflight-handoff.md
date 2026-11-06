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

### Resource evidence and isolated worker recovery

The latest [run 42293464020](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42293464020) and [run 42293463880](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42293463880) (both FAILED) narrowed the issue. The independent guest systemd probe continued ticking throughout the installation phase; Fedora guest memory was about 3.9 GiB total with approximately 3.3 GiB available and its /var filesystem used 7.6 GiB of 38 GiB. Host QEMU process was alive. Crucially the install log reported "Writing rpmdb...done", "Writing OSTree commit...done", "Staging deployment...done", and the exact `postapollo-connections-c2t-fixture-0.1-1.fc44.noarch` added, with changes queued for next boot. **An OSTree deployment was composed and staged, but the original systemd oneshot controller and its in-cgroup watchdog never resumed to verify it, trigger reboot or return a CLI exit code.** The reason that caller stopped progressing is not yet verified; cgroup freeze/units is one plausible explanation, not established fact.

C2y now launches the actual `rpm-ostree install --cache-only` in a separate **transient systemd worker cgroup** and monitors it from the existing guest controller. It requires **independent authoritative `rpm-ostree status --json`** before reboot: at least two deployments, a non-booted staged/pending default, the exact test package in the default deployment's local package metadata, and no active transaction. It accepts an observed worker exit of 0, or explicitly records `C2V_INSTALL_WORKER_EXIT_UNOBSERVED` if the CLI return remains blocked despite complete and verified staging. The *next boot* must then prove the fixture package genuinely exists in the booted RPM database and /usr, followed by a **second boot** after `rpm-ostree rollback --reboot` proving absence. An unverified stage alone is still NOT acceptance. The independent guest probe now reports relevant systemd cgroup.freeze/cgroup.events state, and the GitHub VM guest control unit has a bounded 1400-second deadline to accommodate two real boots. No production service activation, network, credentials or workstation operations.

### Two new failures and independent reboot monitor

Both exact-head runs [42299418948](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42299418948) and [42299419016](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42299419016) failed the reboot acceptance gate. The isolated RPM worker successfully reported `Writing rpmdb...done`, `Writing OSTree commit...done`, `Staging deployment...done`, the exact test RPM added, and changes queued for next boot. Independent systemd probes kept ticking and showed sufficient RAM and disk space, while the original first-boot controller again stopped after `C2V_INSTALL_WATCHDOG // attempt=1`. The tests **never rebooted**. The cause of the first-boot controller stall remains unproven; this is not evidence of a system-wide VM freeze, nor a successful rollback.

Latest C2y implementation moves the **pending-deployment verification and reboot decision into its own independently started transient systemd monitor unit**, separate from both the RPM worker and the original first-boot controller. The original controller waits for the monitor's readiness marker, starts the bounded RPM worker, logs `C2V_MONITOR_HANDOFF_COMPLETE`, then exits without polling `rpm-ostreed`. Only the independent monitor may write the persistent `layer_pending` checkpoint or request reboot, and only after `rpm-ostree status --json` confirms an idle transaction, an actual staged/pending default OSTree deployment and the exact fixture package in the requested/local package metadata. On an observed nonzero RPM install exit, missing package, unavailable status, or elapsed bound, it fails and powers off the disposable guest. If the worker exit is missing but staging independently proves complete, it logs the ambiguity, then requires booted package verification followed by booted rollback verification. All guest network and production-credential gates remain unchanged.
## HOW TO USE

None on your desktop. The PR's GitHub runner builds a temporary signed inert RPM, boots an ephemeral Fedora Silverblue 44 guest, and reports diagnostic/reboot status in CI.

### Two failed Silverblue guest runs, November 6, 2026

Runs [42288289407](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42288289407) (job 128134728232) and [42288289355](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42288289355) (job 128134727592) both successfully booted an offline, Enforcing Fedora Silverblue 44 guest and logged `C2V_STATUS_JSON_PRECHECK_SUCCESS` followed by `C2V_INSTALL_COMMAND_BEGIN`. The host timed out after approximately 900 seconds without `C2V_INSTALL_RETURNED_SUCCESS`, `C2V_INSTALL_FAILED_EXIT`, `C2V_INSTALL_WATCHDOG` or any reboot. **This is not a verified RPM-layering success.** Exact reason is *unknown*; a guest scheduling/resource stall is a hypothesis rather than proven root cause.

The follow-up instrumentation runs a separate, transient systemd guest probe, emitting a ready marker and RAM/disk/rpm-ostree process heartbeat to the serial console every 20 seconds. Host QEMU progress now measures process CPU, RSS, available runner memory and serial byte growth at 40-second intervals. These diagnostics do not modify `rpm-ostree` flags, the guest's network, SELinux or either reboot acceptance check. If the entire guest stalls, host resource evidence remains available even if the guest probe fails to run.

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
- [x] Recover two failures after bounded status precheck and installation entry
- [x] Add independent systemd guest probe and host-side QEMU/RAM/serial visibility
- [x] Establish guest remained responsive, resource-healthy and composed pending OSTree commit
- [x] Separate rpm-ostree worker into its own transient systemd cgroup
- [x] Require exact pending staged deployment with no active rpm-ostree transaction before reboot
- [x] Reproduce isolated-worker controller stall in two official Silverblue VM runs
- [x] Split pending-layer verification and reboot authority into independent transient systemd monitor
- [x] Require monitor readiness before RPM worker starts; original one-shot exits
- [ ] Verify new exact-head CI results, booted RPM layer and booted rollback
- [ ] Review any actual offline rpm-ostree failure and independently verify successful rollback
- [ ] Obtain operator acceptance; no merge or production enablement by this worker

## NEXT

If new CI fails, identify whether the detached worker completed or froze, whether the pending deployment's JSON contains the exact fixture, and whether the separate controller is live. Do not treat a working staged image as a completed rollback. Keep recovery pointers and exact CI logs here.

## DECISIONS

Draft review only, no live Hospital connection, no operator workstation writes, API keys, credentials, TASKS edits, provider calls, signed production package, or production grant.
