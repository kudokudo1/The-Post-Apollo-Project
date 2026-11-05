#!/usr/bin/bash
# C2p Fedora Cloud guest-only read-only SELinux preflight.
set -euo pipefail
echo "C2P_FEDORA=$(cat /etc/fedora-release)"
echo "C2P_KERNEL=$(uname -r)"
echo "C2P_SYSTEMD=$(systemctl --version | head -n 1)"
echo "C2P_SELINUX_MODE=$(getenforce)"
echo "C2P_SELINUX_PROC=$(cat /sys/fs/selinux/enforce 2>/dev/null || echo absent)"
echo "C2P_SELINUX_USER_CONTEXT=$(id -Z 2>/dev/null || echo unavailable)"
echo "C2P_SELINUX_PIDS=$(ps -eZ | head -n 5 | tr '\n' '|')"
if [[ "$(getenforce)" != Enforcing ]] || [[ "$(cat /sys/fs/selinux/enforce)" != 1 ]]; then
  echo "C2P_FAIL // GUEST_KERNEL_NOT_ENFORCING"
  exit 1
fi
echo "C2P_PASS // REAL_FEDORA_GUEST_KERNEL_ENFORCING"
echo "C2P_LIMITATION // NO_PRODUCTION_SERVICE_OR_SELINUX_DOMAIN_VERIFIED"
