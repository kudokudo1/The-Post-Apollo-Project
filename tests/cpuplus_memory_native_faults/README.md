# CPU++ M1c.3a.5b // Native recovery fault fixture (staged, not connected)

This is a separate test-only preparation while #2461's first native smoke is running. It does not change the running workflow or trigger another VM. It is not a production tool. The exact reviewed #2456 helper blob is pinned. No helper/source or UI changes.

## Required future runner wiring

Only after normal-path guest provisioning has been verified, stage this script at a dedicated root-owned path in that same fresh offline VM alongside the exact pinned helper. Create a second root-only fixture marker /etc/postapollo-memory-native-fault-ci-only containing DISPOSABLE_CPU_MEMORY_FAULT_V1. Do not create this marker outside the disposable test VM. The guest must have the two verified normal cycles already archived, active 4 GiB base + 4 GiB extension, SELinux enforcing, Btrfs and the original fixture marker.

1. Run prepare in the guest after the normal-cycle marker. The fixture performs a third real withdraw/reactivate cycle, kills its own test-only archive process immediately after the first original journal unlink, verifies the archive-pending fence and remaining records, explicitly resumes the archive, then withdraws once more and records a durable boot witness.
2. Require the three preparation PASS markers exactly once, no FAIL. Stop the one-shot service from repeating its initialization on reboot. Have the host controller shut down/reboot the guest cleanly (not the workstation), retain the same qcow2, boot it again without installer media, and invoke after-reboot exactly once from a dedicated guest one-shot stage.
3. Verify changed kernel boot ID, active persistent base and inactive retained extension, same file inodes/sizes, unchanged withdrawal records and all three archived histories, continued mutation fence and no automatic replay. A Btrfs device-number change is reported as FILE_IDENTITY_MISMATCH; it is not silently approved.
4. Require both postboot PASS markers exactly once and no FAIL. Retain bounded serial evidence and classify missing markers/provisioning as BLOCKED.

## Limits

The fault is an actual process SIGKILL after archive retirement starts, not a power loss at that instruction. The reboot is controlled and clean, not proof of sudden power-loss fsync ordering. This does not inject pressure, kill util-linux during swapoff, or prove external root actor exclusion, protected installer provenance, or safe deletion. It does not execute or change kernel state on the runner host. Native reclaim and production reduction remain HOLD.

Do not execute the guest script directly on a real workstation, run it outside the dedicated VM, or treat this committed fixture as completed native evidence. A future runner integration PR and independent review are required.
