#!/usr/bin/env bash
# C2q: one-time Fedora Cloud VM service test, invoked only from trusted CI.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true ]] && [[ "$GITHUB_ACTOR" == kudokudo1 ]] || {
  echo "C2S_REFUSED_OUTSIDE_OPERATOR_CI"; exit 2;
}
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d "$RUNNER_TEMP/c2s-vm-XXXXXX")"
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
  echo "C2S_BLOCKED // KVM_UNAVAILABLE"; exit 2;
}
echo "C2S_PREFLIGHT // KVM_AVAILABLE"
image="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
image_sha="28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
curl --fail --location --retry 2 --connect-timeout 15 --max-time 240 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/$image" \
  --output "$tmp/$image"
echo "$image_sha  $tmp/$image" | sha256sum --check --status || {
  echo "C2S_BLOCKED // FEDORA_IMAGE_HASH_MISMATCH"; exit 2;
}
echo "C2S_PASS // PINNED_FEDORA_CLOUD_IMAGE_SHA256"

python3 -m pip download --disable-pip-version-check --no-deps --only-binary=:all: \
  --dest "$tmp" "dbus-next==0.2.3"
wheel="$tmp/dbus_next-0.2.3-py3-none-any.whl"
wheel_sha="58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b"
echo "$wheel_sha  $wheel" | sha256sum --check --status || {
  echo "C2S_BLOCKED // PYPI_WHEEL_HASH_MISMATCH"; exit 2;
}
echo "C2S_PASS // PINNED_DBUS_NEXT_WHEEL_SHA256"

add_file() {
  local source="$1" filename="$2"
  [[ -f "$source" ]] || { echo "C2S_MISSING_FIXTURE // $filename"; exit 2; }
  printf '  - path: /root/c2s/%s\n    permissions: "0600"\n    owner: root:root\n    encoding: b64\n    content: %s\n' \
    "$filename" "$(base64 -w0 "$source")" >> "$tmp/user-data"
}
printf '%s\n' '#cloud-config' 'disable_root: true' 'ssh_pwauth: false' 'write_files:' \
  > "$tmp/user-data"
# Construct a manifest-checked fixture bundle, never a signed production package.
pkg="$tmp/c2s-package-input"
mkdir -m 0700 "$pkg"
cp "$root/tests/connections/c2r_selinux_domain/C2rStatusHost.py" "$pkg/FakeStatusHost.py"
cp "$root/tests/connections/c2o_fedora/BusPolicyClient.py" "$pkg/BusPolicyClient.py"
cp "$root/services/connections/experiments/c2n_package/postapollo-connections-status.service.template" "$pkg/status.service"
cp "$root/services/connections/experiments/c2n_package/org.postapollo.ConnectionsStatus1.conf.template" "$pkg/status.conf"
cp "$RUNNER_TEMP/c2r-policy/postapollo_connections.pp" "$pkg/postapollo_connections.pp"
cp "$wheel" "$pkg/dbus_next.whl"
names=(BusPolicyClient.py FakeStatusHost.py dbus_next.whl postapollo_connections.pp status.conf status.service)
(cd "$pkg" && sha256sum "${names[@]}" > SHA256SUMS)
tar -czf "$tmp/bundle.tar.gz" -C "$pkg" "${names[@]}" SHA256SUMS
(cd "$tmp" && sha256sum bundle.tar.gz > bundle.sha256)
echo "C2S_PASS // SOURCE_BUNDLE_MANIFEST_CREATED_FOR_VM_ONLY"
add_file "$root/tests/connections/c2s_bundle_rollback/guest_install_rollback.sh" "guest_install_rollback.sh"
add_file "$root/tests/connections/c2r_selinux_domain/guest_confined_smoke.sh" "c2r-guest-smoke.sh"
add_file "$tmp/bundle.tar.gz" "bundle.tar.gz"
add_file "$tmp/bundle.sha256" "bundle.sha256"
cat >> "$tmp/user-data" <<'EOF'
runcmd:
  - ["/usr/bin/bash", "-lc", "/usr/bin/bash /root/c2s/guest_install_rollback.sh >/var/tmp/c2s-guest-output.log 2>&1; rc=$?; tail -n 110 /var/tmp/c2s-guest-output.log >/dev/ttyS0 2>&1 || true; echo C2S_VM_GUEST_SCRIPT_EXIT_CODE=$rc >/dev/ttyS0; if [ $rc -eq 0 ]; then echo C2S_VM_PASS >/dev/ttyS0; else echo C2S_VM_FAIL >/dev/ttyS0; fi; exit $rc"]
EOF
printf '%s\n' 'instance-id: c2s-ci-disposable-20261106' \
  'local-hostname: c2s-fedora-test' > "$tmp/meta-data"
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
    if grep -q C2S_VM_PASS "$tmp/serial.log"; then result=PASS; break; fi
    if grep -q C2S_VM_FAIL "$tmp/serial.log"; then result=FAIL; break; fi
  fi
  if ! kill -0 "$vm_pid" 2>/dev/null; then result=VM_EXITED; break; fi
  sleep 2
done
grep -a -E 'C2S_|cloud-init.*(Error|FAIL)' "$tmp/serial.log" 2>/dev/null \
  | tail -n 65 || true
if [[ "$result" != PASS ]]; then
  echo "C2S_BLOCKED // GUEST_RESULT=$result"
  echo "C2S_GUEST_SERIAL_DIAGNOSTIC // last 140 lines"
  tail -n 140 "$tmp/serial.log" 2>/dev/null || true
  tail -n 40 "$tmp/qemu.log" || true
  exit 1
fi
echo "C2S_PASS // GUEST_PACKAGE_ROLLBACK_INTACT"
echo "C2S_LIMITATION // UNSIGNED_BUNDLE_EXPERIMENT_NOT_DEPLOYABLE"
