#!/usr/bin/bash
set -Eeuo pipefail
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_ENVIRONMENT" == github-hosted &&
   "$GITHUB_ACTOR" == kudokudo1 && "$POST_APOLLO_MEMORY_NATIVE_CI_ONLY" == 1 ]]
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]
[[ $# == 1 && -f "$1" ]]
helper="$1"
repo="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d /tmp/cpu-memory-native-XXXXXXXX)"
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
phase_payload="$(base64 -w0 "$repo/tests/cpuplus_memory_native_faults/guest-phase.sh")"
helper_payload="$(base64 -w0 "$helper")"
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
chmod 0700 /usr/local/libexec/postapollo-memory-ci-helper /usr/local/libexec/postapollo-memory-ci-cycle.sh /usr/local/libexec/postapollo-memory-ci-fault.py /usr/local/libexec/postapollo-memory-ci-phase.sh
printf '%s  %s\n' "$helper_sha" postapollo-memory-ci-helper >/usr/local/libexec/postapollo-memory-ci-helper.sha256
chmod 0600 /usr/local/libexec/postapollo-memory-ci-helper.sha256
cat > /etc/systemd/system/postapollo-memory-ci-cycle.service <<'CPU_MEMORY_UNIT'
[Unit]
Description=Disposable CPU++ memory native cycle and reboot fixture
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
        if grep -aEq 'CPU_MEM_(NATIVE|FAULT)_FAIL //' "$log" 2>/dev/null; then
            tail -n 80 "$log" || true
            tail -n 30 "$console" || true
            echo "CPU_MEM_NATIVE_BLOCKED // GUEST_FAILURE phase=$stage"
            return 2
        fi
        if ! kill -0 "$pid" 2>/dev/null; then break; fi
        if (( n % 30 == 0 )); then
            echo "CPU_MEM_NATIVE_STAGE // phase=$stage poll=$n"
            grep -aE 'CPU_MEM_(NATIVE|FAULT)_(PASS|FAIL|STAGE|DIAG) //' "$log" 2>/dev/null | tail -n 14 || true
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
    grep -aE 'CPU_MEM_(NATIVE|FAULT)_(PASS|FAIL|BLOCKED|STAGE|DIAG) //|VERIFIED (ACTIVE|PERSISTENCE|EXPANSION|REDUCTION|REACTIVATION|CYCLE ARCHIVE):|RECOVERY INSPECTION:|REDUCTION (BLOCKED|RECOVERY):|REFUSED/FAILED:' "$log" | tail -n 100 || true
    ! grep -aEq 'CPU_MEM_(NATIVE|FAULT)_FAIL //' "$log"
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
for marker in REAL_SIGKILL_PARTIAL_RETIREMENT_FENCED EXPLICIT_ARCHIVE_RESUME_HISTORY_INTACT REBOOT_WITNESS_DURABLE; do
    require_marker initial "CPU_MEM_FAULT_PASS // $marker"
done
require_marker initial "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_INITIAL"
! grep -aFq 'CPU_MEM_FAULT_PASS // REAL_REBOOT_BASE_ACTIVE_EXTENSION_INACTIVE' "$tmp/guest-initial-serial.log"
echo "CPU_MEM_NATIVE_PASS // FIRST_GUEST_SHUTDOWN_VERIFIED"
run_phase reboot
require_marker reboot "CPU_MEM_FAULT_PASS // REAL_REBOOT_BASE_ACTIVE_EXTENSION_INACTIVE"
require_marker reboot "CPU_MEM_FAULT_PASS // JOURNALS_AND_HISTORY_PRESERVED_NO_REPLAY"
require_marker reboot "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
! grep -aFq 'CPU_MEM_NATIVE_PASS // CYCLE_1_VERIFIED' "$tmp/guest-reboot-serial.log"
! grep -aFq 'CPU_MEM_FAULT_PASS // REBOOT_WITNESS_DURABLE' "$tmp/guest-reboot-serial.log"
echo "CPU_MEM_NATIVE_PASS // OFFLINE_GUEST_ARCHIVE_SIGKILL_AND_CLEAN_REBOOT"
echo "CPU_MEM_NATIVE_LIMITATION // NO_UTIL_LINUX_INTERRUPTION_PRESSURE_OR_HARD_POWER_LOSS_ACCEPTANCE"
