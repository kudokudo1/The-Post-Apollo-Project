#!/usr/bin/bash
set -Eeuo pipefail
trap 'echo "CPU_MEM_KERNEL_FAIL // wrapper line=$LINENO"' ERR
[[ $EUID == 0 && -f /run/ostree-booted ]]
[[ "$(cat /etc/postapollo-memory-ci-only)" == DISPOSABLE_CPU_MEMORY_NATIVE_V1 ]]
[[ "$(cat /etc/postapollo-memory-native-fault-ci-only)" == DISPOSABLE_CPU_MEMORY_FAULT_V1 ]]
[[ "$(cat /etc/postapollo-memory-native-kernel-ci-only)" == DISPOSABLE_CPU_MEMORY_KERNEL_V1 ]]
[[ "$(systemd-detect-virt --vm)" =~ ^(kvm|qemu)$ ]]
[[ "$(getenforce)" == Enforcing ]]
/usr/bin/bash /usr/local/libexec/postapollo-memory-ci-cycle.sh
/usr/bin/python3 -I -B /usr/local/libexec/postapollo-memory-ci-kernel.py
echo "CPU_MEM_KERNEL_STAGE // REQUEST_GUEST_POWEROFF"
/usr/bin/systemctl --no-block poweroff
