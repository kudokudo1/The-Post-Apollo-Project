#!/usr/bin/env bash
# C2p GitHub runner only. Launches a disposable, read-only Fedora Cloud VM.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true ]] || { echo "C2P_REFUSED_NOT_GITHUB_ACTIONS"; exit 2; }
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d "$RUNNER_TEMP/c2p-vm-XXXXXX")"
vm_pid=""
cleanup() {
  if [[ -n "$vm_pid" ]]; then kill "$vm_pid" 2>/dev/null || true; wait "$vm_pid" 2>/dev/null || true; fi
  rm -rf "$tmp"
}
trap cleanup EXIT

if [[ ! -c /dev/kvm ]] || [[ ! -r /dev/kvm ]] || [[ ! -w /dev/kvm ]]; then
  echo "C2P_BLOCKED // HOSTED_RUNNER_HAS_NO_USABLE_KVM"
  exit 2
fi
echo "C2P_PREFLIGHT // KVM_DEVICE_AVAILABLE"

name="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
url="https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/$name"
sha="28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
curl --fail --location --retry 2 --connect-timeout 15 --max-time 240 \
  "$url" -o "$tmp/$name"
echo "$sha  $tmp/$name" | sha256sum --check --status || {
  echo "C2P_BLOCKED // FEDORA_IMAGE_SHA256_MISMATCH"
  exit 2
}
echo "C2P_IMAGE_VERIFIED // OFFICIAL_FEDORA_44_QCOW2_SHA256"

probe_b64="$(base64 -w0 "$root/tests/connections/c2p_fedora_vm/read_only_selinux_probe.sh")"
cat > "$tmp/user-data" <<EOF
#cloud-config
disable_root: true
ssh_pwauth: false
write_files:
  - path: /root/c2p-read-only-probe.sh
    permissions: '0500'
    owner: root:root
    encoding: b64
    content: $probe_b64
runcmd:
  - ["/usr/bin/bash", "-lc", "/usr/bin/bash /root/c2p-read-only-probe.sh >/dev/ttyS0 2>&1; rc=\$?; if [ \$rc -eq 0 ]; then echo C2P_VM_TEST_PASS >/dev/ttyS0; else echo C2P_VM_TEST_FAIL >/dev/ttyS0; fi; exit \$rc"]
EOF
printf '%s\n' 'instance-id: c2p-ci-single-use' 'local-hostname: c2p-fedora-test' > "$tmp/meta-data"
genisoimage -quiet -volid cidata -joliet -rock -output "$tmp/seed.iso" "$tmp/user-data" "$tmp/meta-data"
qemu-img create -q -f qcow2 -F qcow2 -b "$tmp/$name" "$tmp/work.qcow2"
qemu-system-x86_64 \
  -machine accel=kvm -m 2560 -smp 2 -display none \
  -monitor none -serial "file:$tmp/serial.log" \
  -drive "if=virtio,format=qcow2,file=$tmp/work.qcow2" \
  -drive "media=cdrom,file=$tmp/seed.iso,readonly=on" \
  -nic none -no-reboot > "$tmp/qemu.log" 2>&1 &
vm_pid="$!"

result=""
for i in $(seq 1 180); do
  if [[ -f "$tmp/serial.log" ]]; then
    if grep -q 'C2P_VM_TEST_PASS' "$tmp/serial.log"; then result="PASS"; break; fi
    if grep -q 'C2P_VM_TEST_FAIL' "$tmp/serial.log"; then result="FAIL"; break; fi
  fi
  if ! kill -0 "$vm_pid" 2>/dev/null; then result="VM_EXITED"; break; fi
  sleep 2
done

grep -a -E 'C2P_|cloud-init.*(Error|FAIL)' "$tmp/serial.log" 2>/dev/null | tail -n 35 || true
if [[ "$result" != PASS ]]; then
  echo "C2P_BLOCKED // GUEST_RESULT=$result"
  tail -n 50 "$tmp/qemu.log" || true
  exit 1
fi
echo "C2P_PASS // SEPARATE_FEDORA_GUEST_KERNEL_ENFORCING"
echo "C2P_LIMITATION // NO_SIGNED_DEPLOYMENT_OR_CUSTOM_SERVICE_SELINUX_DOMAIN"
