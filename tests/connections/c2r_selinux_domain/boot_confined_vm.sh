#!/usr/bin/env bash
# C2q: one-time Fedora Cloud VM service test, invoked only from trusted CI.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true ]] && [[ "$GITHUB_ACTOR" == kudokudo1 ]] || {
  echo "C2R_REFUSED_OUTSIDE_OPERATOR_CI"; exit 2;
}
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d "$RUNNER_TEMP/c2q-vm-XXXXXX")"
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
  echo "C2R_BLOCKED // KVM_UNAVAILABLE"; exit 2;
}
echo "C2R_PREFLIGHT // KVM_AVAILABLE"
image="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
image_sha="28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
curl --fail --location --retry 2 --connect-timeout 15 --max-time 240 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/$image" \
  --output "$tmp/$image"
echo "$image_sha  $tmp/$image" | sha256sum --check --status || {
  echo "C2R_BLOCKED // FEDORA_IMAGE_HASH_MISMATCH"; exit 2;
}
echo "C2R_PASS // PINNED_FEDORA_CLOUD_IMAGE_SHA256"

python3 -m pip download --disable-pip-version-check --no-deps --only-binary=:all: \
  --dest "$tmp" "dbus-next==0.2.3"
wheel="$tmp/dbus_next-0.2.3-py3-none-any.whl"
wheel_sha="58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b"
echo "$wheel_sha  $wheel" | sha256sum --check --status || {
  echo "C2R_BLOCKED // PYPI_WHEEL_HASH_MISMATCH"; exit 2;
}
echo "C2R_PASS // PINNED_DBUS_NEXT_WHEEL_SHA256"

add_file() {
  local source="$1" filename="$2"
  [[ -f "$source" ]] || { echo "C2R_MISSING_FIXTURE // $filename"; exit 2; }
  printf '  - path: /root/c2q/%s\n    permissions: "0600"\n    owner: root:root\n    encoding: b64\n    content: %s\n' \
    "$filename" "$(base64 -w0 "$source")" >> "$tmp/user-data"
}
printf '%s\n' '#cloud-config' 'disable_root: true' 'ssh_pwauth: false' 'write_files:' \
  > "$tmp/user-data"
add_file "$root/tests/connections/c2r_selinux_domain/guest_confined_smoke.sh" "guest_status_smoke.sh"
add_file "$root/tests/connections/c2r_selinux_domain/C2rStatusHost.py" "FakeStatusHost.py"
add_file "$root/tests/connections/c3b_origin/C3bOriginCheck.py" "C3bOriginCheck.py"
add_file "$root/tests/connections/c2o_fedora/BusPolicyClient.py" "BusPolicyClient.py"
add_file "$root/services/connections/experiments/c2n_package/postapollo-connections-status.service.template" "status.service"
add_file "$root/services/connections/experiments/c2n_package/org.postapollo.ConnectionsStatus1.conf.template" "status.conf"
add_file "$wheel" "dbus_next.whl"
add_file "$RUNNER_TEMP/c2r-policy/postapollo_connections.pp" "postapollo_connections.pp"
cat >> "$tmp/user-data" <<'EOF'
runcmd:
  - ["/usr/bin/bash", "-lc", "/usr/bin/bash /root/c2q/guest_status_smoke.sh >/var/tmp/c2r-guest-output.log 2>&1; rc=$?; tail -n 110 /var/tmp/c2r-guest-output.log >/dev/ttyS0 2>&1 || true; echo C2R_VM_GUEST_SCRIPT_EXIT_CODE=$rc >/dev/ttyS0; if [ $rc -eq 0 ]; then echo C2R_VM_PASS >/dev/ttyS0; else echo C2R_VM_FAIL >/dev/ttyS0; fi; exit $rc"]
EOF
printf '%s\n' 'instance-id: c2r-ci-disposable-20261106' \
  'local-hostname: c2r-fedora-test' > "$tmp/meta-data"
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
    if grep -q C2R_VM_PASS "$tmp/serial.log"; then result=PASS; break; fi
    if grep -q C2R_VM_FAIL "$tmp/serial.log"; then result=FAIL; break; fi
  fi
  if ! kill -0 "$vm_pid" 2>/dev/null; then result=VM_EXITED; break; fi
  sleep 2
done
grep -a -E 'C2R_|C3B_|cloud-init.*(Error|FAIL)' "$tmp/serial.log" 2>/dev/null \
  | tail -n 75 || true
# The C3b guest proof is mandatory, never inferred from C2r's older success.
if [[ "$result" == PASS ]] && \
    ! grep -a -Fq 'C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY' "$tmp/serial.log"; then
  result=C3B_EVIDENCE_MISSING
fi
if [[ "$result" != PASS ]]; then
  echo "C2R_BLOCKED // GUEST_RESULT=$result"
  echo "C2R_GUEST_SERIAL_DIAGNOSTIC // last 140 lines"
  tail -n 140 "$tmp/serial.log" 2>/dev/null || true
  tail -n 40 "$tmp/qemu.log" || true
  exit 1
fi
echo "C2R_PASS // ENFORCING_GUEST_SERVICE_AND_DBUS_POLICY"
echo "C2R_LIMITATION // TEST_ONLY_CUSTOM_DOMAIN_UNSIGNED_NOT_READY_FOR_DESKTOP"
