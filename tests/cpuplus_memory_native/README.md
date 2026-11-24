# CPU++ M1c.3a.5a // Disposable native cycle evidence

This CI-only fixture exercises exact reviewed #2456 helper blob eec7a83cc9068303c3fbc6f4ae9c98e78f7b67ad inside a newly installed offline Silverblue 44 KVM guest. The pinned ISO hash and installation model come from the existing Connections native runner; no Connections files are changed. No operator machine, host swap or physical disk is passed through. The guest receives a fresh 72 GiB virtual disk and 6 GiB memory. The test fails closed if runner resources, installer, Btrfs, SELinux enforcing, kernel readback, or markers are missing. This is not production installer or protected authorization acceptance.

Normal-path coverage: actual base add, systemd enablement, extension add, zero-used withdrawal, protected inspection, retained reactivation, archive, second cycle with identical file identity, independent kernel capacity/priority readback, unchanged other swap devices, history hash and receipt checks. Base persistence enablement is not proof of reboot activation.

Still required before reclamation implementation/production approval:
- Reboot with retained inactive extension; boot identity and Btrfs identity continuity, persistent base actual activation; reconcile stale or mismatched records.
- Actual util-linux child/parent lifetime and SIGKILL inside disposable guest; late occupancy/pressure, blocking syscall, lock contention and other mutator refusal. Do not blindly kill or retry live swapoff.
- Fault matrix around journal publication, fsync, archive pending, partial retirement, power loss and reboot. Preserve root-owned evidence across interrupted archival.
- External systemd/root actor conflict; stale helper version; SELinux label and authorization boundary; kernel thresholds calibrated under controlled workloads.
- Reclaim contract only after verified inactive file, exact identity, durable archived records outside extension, new protected reclaim intent and explicit authorization. Never delete active or unknown files, never delete base or archived history. No recursive cleanup. Actual available-space delta readback must be separate from nominal swap capacity.
- Independent Nurse 2 review and operator release of HOLD. No automatic execution or production installation.

A missing native prerequisite is BLOCKED, not PASS. The fixture does not yet inject pressure, kill native commands or reboot the guest. A successful normal-path run is necessary evidence, not sufficient acceptance.
