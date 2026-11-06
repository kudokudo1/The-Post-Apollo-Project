#!/usr/bin/env bash
# C2q: one-time Fedora Cloud VM service test, invoked only from trusted CI.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true ]] && [[ "$GITHUB_ACTOR" == kudokudo1 ]] || {
  echo "C2T_REFUSED_OUTSIDE_OPERATOR_CI"; exit 2;
}
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d "$RUNNER_TEMP/c2t-vm-XXXXXX")"
vm_pid=""
cleanup() {
  if [[ -n "$vm_pid" ]]; then
    kill "$vm_pid" 2>/dev/null || true
    wait "$vm_pid" 2>/dev/null || true
  fi
  rm -rf "$tmp"
}
trap cleanup EXIT

[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]] || {
  echo "C2T_BLOCKED // KVM_UNAVAILABLE"; exit 2;
}
echo "C2T_PREFLIGHT // KVM_AVAILABLE"
image="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
image_sha="28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
curl --fail --location --retry 2 --connect-timeout 15 --max-time 240 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/$image" \
  --output "$tmp/$image"
echo "$image_sha  $tmp/$image" | sha256sum --check --status || {
  echo "C2T_BLOCKED // FEDORA_IMAGE_HASH_MISMATCH"; exit 2;
}
echo "C2T_PASS // PINNED_FEDORA_CLOUD_IMAGE_SHA256"

add_file() {
  local source="$1" filename="$2"
  [[ -f "$source" ]] || { echo "C2T_MISSING_FIXTURE // $filename"; exit 2; }
  printf '  - path: /root/c2t/%s\n    permissions: "0600"\n    owner: root:root\n    encoding: b64\n    content: %s\n' \
    "$filename" "$(base64 -w0 "$source")" >> "$tmp/user-data"
}
printf '%s\n' '#cloud-config' 'disable_root: true' 'ssh_pwauth: false' 'write_files:' \
  > "$tmp/user-data"
# Import only two signed test RPMs and an *ephemeral public* CI key.
# No private key is ever mounted, logged or transported into the VM.
stage="$RUNNER_TEMP/c2t-rpms"
for filename in c2t-0.1.rpm c2t-0.2.rpm c2t-disposable-public.asc c2t-public-fingerprint.txt c2t-artifact-manifest.sha256; do
  add_file "$stage/$filename" "$filename"
done
add_file "$root/tests/connections/c2t_signed_rpm/guest_signed_rpm_transactions.sh" "guest_signed_rpm_transactions.sh"
echo "C2T_PASS // ONLY_SIGNED_TEST_RPMS_AND_PUBLIC_SIGNER_STAGED"
cat >> "$tmp/user-data" <<'EOF'
runcmd:
  - ["/usr/bin/bash", "-lc", "/usr/bin/bash /root/c2t/guest_signed_rpm_transactions.sh >/var/tmp/c2t-guest-output.log 2>&1; rc=$?; tail -n 110 /var/tmp/c2t-guest-output.log >/dev/ttyS0 2>&1 || true; echo C2T_VM_GUEST_SCRIPT_EXIT_CODE=$rc >/dev/ttyS0; if [ $rc -eq 0 ]; then echo C2T_VM_PASS >/dev/ttyS0; else echo C2T_VM_FAIL >/dev/ttyS0; fi; exit $rc"]
EOF
printf '%s\n' 'instance-id: c2t-ci-disposable-20261106' \
  'local-hostname: c2t-fedora-test' > "$tmp/meta-data"
genisoimage -quiet -volid cidata -joliet -rock -output "$tmp/seed.iso" \
  "$tmp/user-data" "$tmp/meta-data"
qemu-img create -q -f qcow2 -F qcow2 -b "$tmp/$image" "$tmp/guest.qcow2"
qemu-system-x86_64 \
  -machine accel=kvm -m 2560 -smp 2 -display none -monitor none \
  -serial "file:$tmp/serial.log" \
  -drive "if=virtio,format=qcow2,file=$tmp/guest.qcow2" \
  -drive "media=cdrom,file=$tmp/seed.iso,readonly=on" \
  -nic none -no-reboot > "$tmp/qemu.log" 2>&1 &
vm_pid="$!"
result=""
for i in $(seq 1 210); do
  if [[ -f "$tmp/serial.log" ]]; then
    if grep -q C2T_VM_PASS "$tmp/serial.log"; then result=PASS; break; fi
    if grep -q C2T_VM_FAIL "$tmp/serial.log"; then result=FAIL; break; fi
  fi
  if ! kill -0 "$vm_pid" 2>/dev/null; then result=VM_EXITED; break; fi
  sleep 2
done
grep -a -E 'C2T_|cloud-init.*(Error|FAIL)' "$tmp/serial.log" 2>/dev/null \
  | tail -n 65 || true
if [[ "$result" != PASS ]]; then
  echo "C2T_BLOCKED // GUEST_RESULT=$result"
  echo "C2T_GUEST_SERIAL_DIAGNOSTIC // last 140 lines"
  tail -n 140 "$tmp/serial.log" 2>/dev/null || true
  tail -n 40 "$tmp/qemu.log" || true
  exit 1
fi
echo "C2T_PASS // SIGNED_RPM_TRANSACTION_AND_ROLLBACK_INTACT"
echo "C2T_LIMITATION // DISPOSABLE_SELF_SIGNED_RPM_NOT_DEPLOYABLE"
