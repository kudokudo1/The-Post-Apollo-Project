#!/usr/bin/bash
# Dedicated offline guest only. The installed unit calls this once per boot.
set -Eeuo pipefail
trap 'echo "CPU_MEM_FAULT_FAIL // phase wrapper line=$LINENO"' ERR
[[ $EUID == 0 && -f /run/ostree-booted ]]
[[ "$(cat /etc/postapollo-memory-ci-only)" == DISPOSABLE_CPU_MEMORY_NATIVE_V1 ]]
[[ "$(cat /etc/postapollo-memory-native-fault-ci-only)" == DISPOSABLE_CPU_MEMORY_FAULT_V1 ]]
[[ "$(systemd-detect-virt --vm)" =~ ^(kvm|qemu)$ ]]
[[ "$(getenforce)" == Enforcing ]]
witness=/var/lib/postapollo-memory-native-fault-witness.json
if [[ -e "$witness" || -L "$witness" ]]; then
    /usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-fault.py after-reboot
    echo "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_REBOOT"
else
    /usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
    /usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-fault.py prepare
    echo "CPU_MEM_FAULT_STAGE // REQUEST_GUEST_POWEROFF_INITIAL"
fi
# Normal guest shutdown, not a SIGKILL or host reboot. The host requires QEMU
# exit and verifies phase-two boot ID from the durable witness.
systemctl --no-block poweroff
