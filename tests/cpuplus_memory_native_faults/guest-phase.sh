#!/usr/bin/bash
# Dedicated offline guest only. The installed unit calls this once per boot.
set -Eeuo pipefail
trap 'echo "CPU_MEM_FAULT_FAIL // phase wrapper line=$LINENO"' ERR
[[ $EUID == 0 && -f /run/ostree-booted ]]
[[ "$(cat /etc/postapollo-memory-ci-only)" == DISPOSABLE_CPU_MEMORY_NATIVE_V1 ]]
[[ "$(cat /etc/postapollo-memory-native-fault-ci-only)" == DISPOSABLE_CPU_MEMORY_FAULT_V1 ]]
[[ "$(cat /etc/postapollo-memory-native-headroom-ci-only)" == DISPOSABLE_CPU_MEMORY_HEADROOM_V1 ]]
[[ "$(systemd-detect-virt --vm)" =~ ^(kvm|qemu)$ ]]
[[ "$(getenforce)" == Enforcing ]]
# Dedicated COM2 evidence, separate from kernel console and login getty.
# A bounded read-only observer reports process states even if the fixture
# stops printing. It never signals a helper, retries, or changes swap.
(
    for ((sample=0;sample<24;sample++)); do
        sleep 15
        printf 'CPU_MEM_FAULT_DIAG // process sample=%s\n' "$sample"
        ps -eo pid,ppid,stat,wchan:24,comm | awk 'NR==1 || $NF ~ /^(python3|swapon|swapoff|btrfs|systemd-escape|systemctl)$/'
        awk '/^MemAvailable:|^SwapFree:/ {print}' /proc/meminfo
        cat /proc/pressure/memory
    done
) &
observer=$!
# Stop only our read-only observer after the test exits, not swap children.
trap 'kill "$observer" 2>/dev/null || true; wait "$observer" 2>/dev/null || true' EXIT
witness=/var/lib/postapollo-memory-native-fault-witness.json
echo "CPU_MEM_FAULT_STAGE // WRAPPER_BEGIN"
if [[ -e "$witness" || -L "$witness" ]]; then
    /usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-fault.py after-reboot
    echo "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
else
    /usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
    echo "CPU_MEM_HEADROOM_STAGE // BEGIN_AFTER_NORMAL_CYCLES"
    /usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-headroom.py
    echo "CPU_MEM_FAULT_STAGE // NORMAL_CYCLES_COMPLETE_PREPARE_NEXT"
    /usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-fault.py prepare
    echo "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_INITIAL"
fi
# Normal guest shutdown, not a SIGKILL or host reboot. The host requires QEMU
# exit and verifies phase-two boot ID from the durable witness.
systemctl --no-block poweroff
