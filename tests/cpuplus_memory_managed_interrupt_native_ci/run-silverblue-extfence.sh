#!/usr/bin/bash
set -Eeuo pipefail
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_ENVIRONMENT" == github-hosted &&
   "$GITHUB_ACTOR" == kudokudo1 && "$POST_APOLLO_MEMORY_NATIVE_CI_ONLY" == 1 ]]
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]
[[ $# == 1 && -f "$1" && "$POST_APOLLO_MEMORY_EXTFENCE_CI_ONLY" == 1 ]]
helper="$1"
repo="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d /tmp/cpu-memory-extfence-XXXXXXXX)"
pid=
cleanup() {
    if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; fi
    rm -rf -- "$tmp"
}
trap cleanup EXIT
iso=Fedora-Silverblue-ostree-x86_64-44-1.7.iso
# Same pinned official ISO already used by the repository's C4b native harness.
iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682
curl --fail --location --retry 2 --connect-timeout 20 --max-time 660 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Silverblue/x86_64/iso/$iso" -o "$tmp/$iso"
printf '%s  %s\n' "$iso_sha" "$tmp/$iso" | sha256sum -c --status
mkdir "$tmp/pxe" "$tmp/seed"
xorriso -osirrox on -indev "$tmp/$iso" -extract /images/pxeboot/vmlinuz "$tmp/pxe/vmlinuz" -extract /images/pxeboot/initrd.img "$tmp/pxe/initrd.img" >"$tmp/extract.log" 2>&1
[[ -s "$tmp/pxe/vmlinuz" && -s "$tmp/pxe/initrd.img" ]]
payload="$(base64 -w0 "$repo/tests/cpuplus_memory_native/guest-cycle.sh")"
fault_payload="$(base64 -w0 "$repo/tests/cpuplus_memory_native_faults/guest-recovery.py")"
phase_payload="$(base64 -w0 "$repo/tests/cpuplus_memory_managed_interrupt_native_ci/guest-extfence-phase.sh")"
extfence_payload="$(base64 -w0 "$repo/tests/cpuplus_memory_managed_interrupt_native_ci/guest-extfence.py")"
helper_payload="$(base64 -w0 "$helper")"
writer_payload="$(base64 -w0 "$repo/reviewed-memory-source/tests/cpuplus_memory_protected_custody_ci/candidate.py")"
managed_payload="$(base64 -w0 "$repo/reviewed-memory-source/tests/cpuplus_memory_managed_reclaim_native_ci/managed.py")"
helper_sha="$(sha256sum "$helper" | cut -d' ' -f1)"
cat >"$tmp/seed/ks.cfg" <<EOF
cmdline
lang en_US.UTF-8
keyboard --xlayouts=us
timezone Etc/UTC --utc
shutdown
eula --agreed
rootpw --lock
firstboot --disable
selinux --enforcing
zerombr
ignoredisk --only-use=vda
clearpart --all --initlabel --drives=vda
autopart --type=btrfs
bootloader --append="console=ttyS0,115200 console=tty0"
cdrom
ostreesetup --osname=fedora --remote=fedora --url=file:///ostree/repo --ref=fedora/44/x86_64/silverblue --nogpg
%post --erroronfail --log=/root/cpu-memory-ci-install.log
install -d -m 0755 /usr/local/libexec /etc/systemd/system
printf '%s\n' DISPOSABLE_CPU_MEMORY_NATIVE_V1 > /etc/postapollo-memory-ci-only
chmod 0600 /etc/postapollo-memory-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_FAULT_V1 > /etc/postapollo-memory-native-fault-ci-only
chmod 0600 /etc/postapollo-memory-native-fault-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_EXTFENCE_V1 > /etc/postapollo-memory-native-extfence-ci-only
chmod 0600 /etc/postapollo-memory-native-extfence-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_BOOT_BINDING_V1 > /etc/postapollo-memory-native-boot-binding-ci-only
chmod 0600 /etc/postapollo-memory-native-boot-binding-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_PROTECTED_CUSTODY_V1 > /etc/postapollo-memory-native-protected-custody-ci-only
chmod 0600 /etc/postapollo-memory-native-protected-custody-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_PHYSICAL_RECLAIM_V1 > /etc/postapollo-memory-native-physical-reclaim-ci-only
chmod 0600 /etc/postapollo-memory-native-physical-reclaim-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_MANAGED_RECLAIM_V1 > /etc/postapollo-memory-native-managed-reclaim-ci-only
chmod 0600 /etc/postapollo-memory-native-managed-reclaim-ci-only
printf '%s\n' DISPOSABLE_CPU_MEMORY_MANAGED_INTERRUPT_V1 > /etc/postapollo-memory-native-managed-interrupt-ci-only
chmod 0600 /etc/postapollo-memory-native-managed-interrupt-ci-only
# Set only the disposable guest's generator configuration before first boot.
# Fedora's RAM-derived default varied by one MiB between the prior boots.
# Keep the complete exact swap signature comparison, including ZRAM.
install -d -m 0755 /etc/systemd/zram-generator.conf.d
cat > /etc/systemd/zram-generator.conf.d/99-postapollo-boot-binding-ci.conf <<'CPU_MEMORY_ZRAM'
[zram0]
zram-size = 4096
swap-priority = 100
CPU_MEMORY_ZRAM
chmod 0600 /etc/systemd/zram-generator.conf.d/99-postapollo-boot-binding-ci.conf
base64 -d >/usr/local/libexec/postapollo-memory-ci-helper <<'CPU_MEMORY_HELPER'
$helper_payload
CPU_MEMORY_HELPER
base64 -d >/usr/local/libexec/postapollo-memory-ci-cycle.sh <<'CPU_MEMORY_GUEST'
$payload
CPU_MEMORY_GUEST
base64 -d >/usr/local/libexec/postapollo-memory-ci-fault.py <<'CPU_MEMORY_FAULT'
$fault_payload
CPU_MEMORY_FAULT
base64 -d >/usr/local/libexec/postapollo-memory-ci-phase.sh <<'CPU_MEMORY_PHASE'
$phase_payload
CPU_MEMORY_PHASE
base64 -d >/usr/local/libexec/postapollo-memory-ci-extfence.py <<'CPU_MEMORY_EXTFENCE'
$extfence_payload
CPU_MEMORY_EXTFENCE
chmod 0700 /usr/local/libexec/postapollo-memory-ci-extfence.py
install -d -m 0755 /usr/local/sbin
install -m 0700 /usr/local/libexec/postapollo-memory-ci-helper /usr/local/sbin/post-apollo-memory-add-swap
base64 -d >/usr/local/libexec/postapollo-memory-ci-custody.py <<'CPU_MEMORY_WRITER'
$writer_payload
CPU_MEMORY_WRITER
chmod 0600 /usr/local/libexec/postapollo-memory-ci-custody.py
base64 -d >/usr/local/libexec/postapollo-memory-ci-managed.py <<'CPU_MEMORY_MANAGED'
$managed_payload
CPU_MEMORY_MANAGED
chmod 0600 /usr/local/libexec/postapollo-memory-ci-managed.py
chmod 0700 /usr/local/libexec/postapollo-memory-ci-helper /usr/local/libexec/postapollo-memory-ci-cycle.sh /usr/local/libexec/postapollo-memory-ci-fault.py /usr/local/libexec/postapollo-memory-ci-phase.sh
printf '%s  %s\n' "$helper_sha" postapollo-memory-ci-helper >/usr/local/libexec/postapollo-memory-ci-helper.sha256
chmod 0600 /usr/local/libexec/postapollo-memory-ci-helper.sha256
cat > /etc/systemd/system/postapollo-memory-ci-cycle.service <<'CPU_MEMORY_UNIT'
[Unit]
Description=Disposable CPU++ external reclaim fence fixture
After=local-fs.target swap.target dev-ttyS1.device
Requires=dev-ttyS1.device
ConditionPathExists=/etc/postapollo-memory-ci-only
[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'exec /usr/bin/bash /usr/local/libexec/postapollo-memory-ci-phase.sh >/dev/ttyS1 2>&1'
TimeoutStartSec=600
[Install]
WantedBy=multi-user.target
CPU_MEMORY_UNIT
systemctl mask serial-getty@ttyS1.service
systemctl enable postapollo-memory-ci-cycle.service
systemctl set-default multi-user.target
echo CPU_MEM_NATIVE_INSTALLER_STAGED >/dev/ttyS0
%end
EOF
genisoimage -quiet -volid CPUMEMCI -joliet -rock -o "$tmp/seed.iso" "$tmp/seed"/*
qemu-img create -q -f qcow2 "$tmp/guest.qcow2" 72G
# Only a fresh sparse image is writable. No host storage passthrough, network,
# or shared filesystem. Both installation media drives are read-only.
qemu-system-x86_64 -machine accel=kvm -m 6144 -smp 3 -display none -monitor none \
  -kernel "$tmp/pxe/vmlinuz" -initrd "$tmp/pxe/initrd.img" \
  -append "console=ttyS0,115200 inst.repo=cdrom inst.ks=hd:LABEL=CPUMEMCI:/ks.cfg inst.cmdline rd.neednet=0" \
  -serial "file:$tmp/install-serial.log" \
  -drive "file=$tmp/guest.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/$iso,if=ide,media=cdrom,readonly=on,index=0" \
  -drive "file=$tmp/seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none -no-reboot >"$tmp/install-qemu.log" 2>&1 &
pid="$!"
for ((n=0;n<750;n++)); do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 2
done
if kill -0 "$pid" 2>/dev/null; then
    echo "CPU_MEM_NATIVE_BLOCKED // INSTALL_TIMEOUT"
    tail -n 40 "$tmp/install-serial.log" || true
    exit 2
fi
wait "$pid"; pid=
grep -aFq CPU_MEM_NATIVE_INSTALLER_STAGED "$tmp/install-serial.log" || {
    echo "CPU_MEM_NATIVE_BLOCKED // INSTALL_NOT_VERIFIED"
    tail -n 40 "$tmp/install-serial.log" || true
    exit 2
}
# Run the same installed guest twice. Never treat process termination or a
# guest-authored marker alone as success: each phase must exit normally, and
# phase two independently checks the kernel boot ID and preserved state.
run_phase() {
    local stage="$1" log="$tmp/guest-$1-serial.log" console="$tmp/guest-$1-console.log"
    qemu-system-x86_64 -machine accel=kvm -m 6144 -smp 3 -display none -monitor none \
      -serial "file:$console" -serial "file:$log" \
      -drive "file=$tmp/guest.qcow2,if=virtio,format=qcow2" \
      -nic none -no-reboot >"$tmp/guest-$stage-qemu.log" 2>&1 &
    pid="$!"
    for ((n=0;n<360;n++)); do
        if grep -aEq 'CPU_MEM_(NATIVE|FAULT|EXTFENCE)_FAIL //' "$log" 2>/dev/null; then
            tail -n 80 "$log" || true
            tail -n 30 "$console" || true
            echo "CPU_MEM_NATIVE_BLOCKED // GUEST_FAILURE phase=$stage"
            return 2
        fi
        if ! kill -0 "$pid" 2>/dev/null; then break; fi
        if (( n % 30 == 0 )); then
            echo "CPU_MEM_NATIVE_STAGE // phase=$stage poll=$n"
            grep -aE 'CPU_MEM_(NATIVE|FAULT|EXTFENCE)_(PASS|FAIL|STAGE|DIAG) //' "$log" 2>/dev/null | tail -n 14 || true
        fi
        sleep 2
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo "CPU_MEM_NATIVE_BLOCKED // GUEST_SHUTDOWN_TIMEOUT phase=$stage"
        tail -n 80 "$log" || true
        tail -n 35 "$console" || true
        return 2
    fi
    if ! wait "$pid"; then
        pid=
        echo "CPU_MEM_NATIVE_BLOCKED // GUEST_EXIT_FAILED phase=$stage"
        tail -n 80 "$log" || true
        return 2
    fi
    pid=
    grep -aE 'CPU_MEM_(NATIVE|FAULT|EXTFENCE)_(PASS|FAIL|BLOCKED|STAGE|DIAG) //|VERIFIED (ACTIVE|PERSISTENCE|EXPANSION|REDUCTION|REACTIVATION|CYCLE ARCHIVE):|RECOVERY INSPECTION:|REDUCTION (BLOCKED|RECOVERY):|REFUSED/FAILED:' "$log" | tail -n 100 || true
    ! grep -aEq 'CPU_MEM_(NATIVE|FAULT|EXTFENCE)_FAIL //' "$log"
}
require_marker() {
    local stage="$1" marker="$2"
    [[ "$(grep -aFc "$marker" "$tmp/guest-$stage-serial.log")" == 1 ]] || {
        echo "CPU_MEM_NATIVE_BLOCKED // REQUIRED_GUEST_EVIDENCE_MISSING phase=$stage marker=$marker"
        tail -n 60 "$tmp/guest-$stage-serial.log" || true
        return 2
    }
}
run_phase initial
for marker in SILVERBLUE_BTRFS_ENFORCING_GUEST BASE_PERSISTENCE_AND_EXTENSION_ACTIVE CYCLE_1_VERIFIED CYCLE_2_VERIFIED TWO_REAL_CYCLES_HISTORY_RETAINED; do
    require_marker initial "CPU_MEM_NATIVE_PASS // $marker"
done
require_marker initial "CPU_MEM_EXTFENCE_STAGE // EXACT_CANDIDATE 9dfd8331445ecf60d3a37ea630d08b1f3f6789a2"
require_marker initial "CPU_MEM_EXTFENCE_PASS // FIXED_GUEST_ZRAM_4GIB"
require_marker initial "CPU_MEM_EXTFENCE_PASS // ABSENT_EXTENSION_ALL_ENTRYPOINTS_BLOCKED"
require_marker initial "CPU_MEM_EXTFENCE_PASS // BOUND_ARCHIVED_CYCLES_ACTIVE_REFUSED"
require_marker initial "CPU_MEM_EXTFENCE_PASS // SAME_BOOT_INACTIVE_WITNESS_AND_PUBLIC_RECEIPT"
require_marker initial "CPU_MEM_EXTFENCE_PASS // LEGACY_AND_MALFORMED_WITNESS_REFUSED"
require_marker initial "CPU_MEM_EXTFENCE_PASS // ARCHIVE_ONLY_EIGHT_ENTRYPOINTS_REFUSED"
require_marker initial "CPU_MEM_EXTFENCE_STAGE // ACTUAL_UNLINK_AND_FSYNC_BEFORE_SIGKILL"
require_marker initial "CPU_MEM_EXTFENCE_PASS // SIGKILL_PARTIAL_RELEASE_NO_SUCCESS_RECEIPT"
require_marker initial "CPU_MEM_EXTFENCE_PASS // FENCE_AND_WITHDRAWAL_WITNESS_DURABLE"
require_marker initial "CPU_MEM_EXTFENCE_STAGE // REQUEST_GUEST_POWEROFF_INITIAL"
[[ "$(grep -aFc 'CPU_MEM_EXTFENCE_STAGE // EIGHT_PROTECTED_ENTRYPOINTS_REFUSED' "$tmp/guest-initial-serial.log")" == 2 ]]
run_phase reboot
require_marker reboot "CPU_MEM_EXTFENCE_STAGE // EXACT_CANDIDATE 9dfd8331445ecf60d3a37ea630d08b1f3f6789a2"
require_marker reboot "CPU_MEM_EXTFENCE_PASS // FIXED_GUEST_ZRAM_4GIB"
require_marker reboot "CPU_MEM_EXTFENCE_STAGE // EIGHT_PROTECTED_ENTRYPOINTS_REFUSED"
require_marker reboot "CPU_MEM_EXTFENCE_PASS // INTERRUPTED_RELEASE_REBOOT_RETAINED_NO_REPLAY"
require_marker reboot "CPU_MEM_EXTFENCE_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
! grep -aFq 'CPU_MEM_NATIVE_PASS // CYCLE_1_VERIFIED' "$tmp/guest-reboot-serial.log"
echo "CPU_MEM_BOOT_BINDING_PASS // EXACT_CANDIDATE_SAME_BOOT_AND_REBOOT"
echo "CPU_MEM_EXTFENCE_LIMITATION // NO_PRODUCTION_DELETION_OR_PHYSICAL_POWER_LOSS"
