#!/usr/bin/env bash
# C2u runs ONLY on a fresh ephemeral GitHub Actions runner. ISO is official
# Fedora Silverblue 44, not Fedora Cloud and not a Docker replacement.
set -Eeuo pipefail
[[ "$GITHUB_ACTIONS" == true && "$GITHUB_ACTOR" == kudokudo1 ]] ||
  { echo "C2V_REFUSED_OUTSIDE_OPERATOR_GITHUB_CI"; exit 2; }
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]] ||
  { echo "C2V_BLOCKED // HOST_NO_KVM"; exit 2; }
repo="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d "$RUNNER_TEMP/c2v-silverblue-XXXXXX")"
pid=""
cleanup() {
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
  rm -rf "$tmp"
}
trap cleanup EXIT
iso="Fedora-Silverblue-ostree-x86_64-44-1.7.iso"
iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682
echo "C2V_OFFICIAL_SOURCE // Fedora Silverblue 44 OSTree ISO"

# The official Fedora download page publishes this exact x86_64 SHA256.
# A mismatch is a hard failure; NEVER fallback to Cloud Base or a container.
curl --fail --location --retry 2 --connect-timeout 20 --max-time 660 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Silverblue/x86_64/iso/$iso" \
  -o "$tmp/$iso"
echo "$iso_sha  $tmp/$iso" | sha256sum --check --status ||
  { echo "C2V_BLOCKED // OFFICIAL_SILVERBLUE_ISO_SHA256_MISMATCH"; exit 2; }
echo "C2V_PASS // OFFICIAL_FEDORA_SILVERBLUE_44_ISO_SHA256"
du -h "$tmp/$iso"

# Installer image is an OSTree installer, with its own kernel/initrd and repo.
mkdir -p "$tmp/boot"
xorriso -osirrox on -indev "$tmp/$iso" \
  -extract /images/pxeboot/vmlinuz "$tmp/boot/vmlinuz" \
  -extract /images/pxeboot/initrd.img "$tmp/boot/initrd.img" \
  > "$tmp/iso-extract.log" 2>&1 ||
  { cat "$tmp/iso-extract.log"; echo "C2V_BLOCKED // SILVERBLUE_INSTALLER_PXE_KERNEL_MISSING"; exit 2; }
test -s "$tmp/boot/vmlinuz" && test -s "$tmp/boot/initrd.img" ||
  { echo "C2V_BLOCKED // EMPTY_INSTALLER_KERNEL"; exit 2; }
echo "C2V_PASS // INSTALLER_KERNEL_AND_INITRD_PRESENT"

# Build a separate read-only ISO with a single Kickstart file and the already
# tested inert C2t RPM. No passwords, SSH keys, network or test CI private key.
p="$RUNNER_TEMP/c2t-rpms"
seed="$tmp/seed"
mkdir -p "$seed"
for name in c2t-0.1.rpm c2t-0.2.rpm c2t-disposable-public.asc \
            c2t-public-fingerprint.txt c2t-artifact-manifest.sha256; do
  test -s "$p/$name" ||
    { echo "C2V_BLOCKED // TEST_RPM_ARTIFACT_MISSING_$name"; exit 2; }
  cp "$p/$name" "$seed/$name"
done
(cd "$seed" && sha256sum --check --status c2t-artifact-manifest.sha256) ||
  { echo "C2V_BLOCKED // BAD_TEST_RPM_CHECKSUM"; exit 2; }

# C4a opts in ONLY when the new dedicated CI provides the already reviewed
# signed fake-service fixture. Existing C2v/C2x tests remain C2t-only.
c4a_requested=0
if [[ -v C4A_SERVICE_RPM_DIR && -n "$C4A_SERVICE_RPM_DIR" ]]; then
  c4a_requested=1
  for name in c3d-status.rpm c3d-disposable-public.asc \
              c3d-public-fingerprint.txt c3d-artifact-manifest.sha256; do
    [[ -s "$C4A_SERVICE_RPM_DIR/$name" ]] ||
      { echo "C4A_BLOCKED // SIGNED_FAKE_SERVICE_ARTIFACT_MISSING"; exit 2; }
    cp "$C4A_SERVICE_RPM_DIR/$name" "$seed/$name"
  done
  (cd "$seed" && sha256sum --check --status c3d-artifact-manifest.sha256) ||
    { echo "C4A_BLOCKED // SIGNED_STATUS_ARTIFACT_MANIFEST_INVALID"; exit 2; }
  cp "$repo/tests/connections/c4a_silverblue/guest_signed_status_gate.sh" \
    "$seed/c4a-guest-signed-status-gate.sh"
  printf '%s\n' C4A_EXPLICIT_SIGNED_STATUS_CI_ONLY > "$seed/c4a-opt-in.marker"
  echo "C4A_PASS // PUBLIC_SIGNED_TEST_ARTIFACTS_STAGED_WITH_NO_PRIVATE_KEY"
fi

# C4b runtime assets ONLY when the dedicated CI opted in to BOTH C4a
# signed service layering and C4b running-service identity verification.
c4b_requested=0
if [[ -v C4B_RUNTIME_ASSETS_DIR && -n "$C4B_RUNTIME_ASSETS_DIR" ]]; then
  [[ "$c4a_requested" == 1 ]] ||
    { echo "C4B_BLOCKED // C4A_SIGNED_PACKAGE_REQUIRED"; exit 2; }
  c4b_requested=1
  for name in postapollo_connections.pp dbus_next.whl \
              C3bOriginCheck.py BusPolicyClient.py c4b-runtime-manifest.sha256; do
    [[ -s "$C4B_RUNTIME_ASSETS_DIR/$name" ]] ||
      { echo "C4B_BLOCKED // RUNTIME_ASSET_MISSING"; exit 2; }
    cp "$C4B_RUNTIME_ASSETS_DIR/$name" "$seed/$name"
  done
  (cd "$seed" && sha256sum --check --status c4b-runtime-manifest.sha256) ||
    { echo "C4B_BLOCKED // RUNTIME_MANIFEST_MISMATCH"; exit 2; }
  cp "$repo/tests/connections/c4b_silverblue/guest_confined_runtime.sh" \
    "$seed/c4b-guest-confined-runtime.sh"
  printf '%s\n' C4B_CI_ONLY_CONFINED_RUNTIME > "$seed/c4b-opt-in.marker"
  echo "C4B_PASS // OFFLINE_RUNTIME_POLICY_WHEEL_AND_PROBES_STAGED"
fi

payload="$(base64 -w0 "$repo/tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh")"
cat > "$seed/ks.cfg" <<EOF
# C2u fully disposable, offline Fedora Silverblue 44 VM only.
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
autopart --type=plain
bootloader --append="console=ttyS0,115200 console=tty0"
cdrom
ostreesetup --osname=fedora --remote=fedora --url=file:///ostree/repo --ref=fedora/44/x86_64/silverblue --nogpg
%post --erroronfail --log=/root/c2v-post.log
mkdir -p /usr/local/libexec /etc/systemd/system /var/lib
echo initial > /var/lib/c2v-transaction-stage
base64 -d > /usr/local/libexec/c2v-ostree-cycle.sh <<'C2V_SCRIPT_ENCODED'
$payload
C2V_SCRIPT_ENCODED
chmod 0755 /usr/local/libexec/c2v-ostree-cycle.sh
cat > /etc/systemd/system/c2v-ostree-cycle.service <<'C2V_UNIT'
[Unit]
Description=Disposable C2u Silverblue ostree reboot test
After=local-fs.target
ConditionPathExists=/run/ostree-booted

[Service]
Type=oneshot
ExecStart=/usr/bin/bash /usr/local/libexec/c2v-ostree-cycle.sh
TimeoutStartSec=1400

[Install]
WantedBy=multi-user.target
C2V_UNIT
systemctl enable c2v-ostree-cycle.service
echo C2V_PASS // KICKSTART_POST_INSTALL_STAGED >/dev/ttyS0
%end
EOF
genisoimage -quiet -volid C2VCI -joliet -rock -o "$tmp/c2v-seed.iso" "$seed"/*
qemu-img create -q -f qcow2 "$tmp/silverblue.qcow2" 40G
echo "C2V_PASS // ISOLATED_SPARSE_DISK_CREATED"

# The official Fedora installer boots with QEMU's direct kernel loader and
# gets both the installation payload and Kickstart from separate CD-ROMs.
qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -kernel "$tmp/boot/vmlinuz" -initrd "$tmp/boot/initrd.img" \
  -append "console=ttyS0,115200 inst.repo=cdrom inst.ks=hd:LABEL=C2VCI:/ks.cfg inst.cmdline rd.neednet=0" \
  -serial "file:$tmp/installer-serial.log" \
  -drive "file=$tmp/silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/$iso,if=ide,media=cdrom,readonly=on,index=0" \
  -drive "file=$tmp/c2v-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none -no-reboot > "$tmp/installer-qemu.log" 2>&1 &
pid="$!"

result=""
for i in $(seq 1 600); do
  if [[ -f "$tmp/installer-serial.log" ]] &&
     grep -q 'C2V_PASS // KICKSTART_POST_INSTALL_STAGED' "$tmp/installer-serial.log"; then
    result=POST_DONE
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 2
done
echo "C2V_INSTALLER_EVIDENCE // $result"
grep -a -E 'C2V_|Kickstart|anaconda.*(error|failed)|No such file' \
  "$tmp/installer-serial.log" 2>/dev/null | tail -n 55 || true
if [[ "$result" != POST_DONE ]]; then
  echo "C2V_BLOCKED // OFFICIAL_SILVERBLUE_INSTALLER_DID_NOT_COMPLETE"
  tail -n 110 "$tmp/installer-serial.log" 2>/dev/null || true
  tail -n 50 "$tmp/installer-qemu.log" || true
  exit 1
fi

kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
pid=""
echo "C2V_PASS // OFFLINE_SILVERBLUE_INSTALLER_POST_STEP"

# A real persistent disk boot, not a container and not just a staged tree.
# The guest itself will perform: baseline boot -> rpm-ostree layer -> reboot
# -> validate booted layer -> rollback -> reboot -> validate absence -> off.
# C4b-only second UART is a diagnostic output sink, not a reboot/acceptance
# signal. It is independent of the primary ttyS0 console/serial-getty.
c4b_secondary_serial=()
if [[ "$c4b_requested" == 1 ]]; then
  c4b_secondary_serial=(-serial "file:$tmp/c4b-diagnostic-serial.log")
fi
qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -serial "file:$tmp/guest-serial.log" \
  "${c4b_secondary_serial[@]}" \
  -drive "file=$tmp/silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/c2v-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none > "$tmp/guest-qemu.log" 2>&1 &
pid="$!"
result=""
last_serial_bytes=0
for i in $(seq 1 700); do
  if (( i % 20 == 0 )); then
    echo "C2V_HOST_GUEST_HEARTBEAT // $i"
    ps -p "$pid" -o pid=,stat=,etime=,%cpu=,%mem=,rss=,vsz=,comm= || true
    free -m | head -n 3 || true
    if [[ -f "$tmp/guest-serial.log" ]]; then
      current_serial_bytes="$(wc -c < "$tmp/guest-serial.log")"
      echo "C2V_HOST_SERIAL_BYTES // current=$current_serial_bytes previous=$last_serial_bytes"
      last_serial_bytes="$current_serial_bytes"
      grep -a -E 'C2V_(PASS|FAIL|INSTALL_|MONITOR_|PENDING_|BLOCKED|GUEST_PROBE)' "$tmp/guest-serial.log" 2>/dev/null | tail -n 12 || true
    fi
  fi
  if [[ -f "$tmp/guest-serial.log" ]]; then
    if grep -q 'C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER' \
           "$tmp/guest-serial.log"; then
      result=PASS; break
    fi
    if grep -q 'C2V_FAIL' "$tmp/guest-serial.log"; then
      result=FAIL; break
    fi
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    result=VM_EXITED; break
  fi
  sleep 2
done
echo "C2V_HOST_MONITOR_EVIDENCE // from complete guest serial"
grep -a -E 'C2V_(MONITOR_|PENDING_DEPLOYMENT_AUTHORITY|INSTALL_FAILED_EXIT|PROBE_OSTREE_ADMIN_STATUS)' \
  "$tmp/guest-serial.log" 2>/dev/null | tail -n 72 || true
grep -a 'C2V_' "$tmp/guest-serial.log" 2>/dev/null | tail -n 70 || true
if [[ "$result" != PASS ]]; then
  echo "C2V_BLOCKED // SILVERBLUE_LAYER_REBOOT_ROLLBACK_RESULT=$result"
  if [[ "$c4b_requested" == 1 ]]; then
    echo "C4B_HOST_DIAGNOSTIC_UART_BEGIN"
    if [[ -r "$tmp/c4b-diagnostic-serial.log" ]]; then
      echo "C4B_HOST_DIAGNOSTIC_UART_BYTES // $(wc -c < "$tmp/c4b-diagnostic-serial.log")"
      tail -n 130 "$tmp/c4b-diagnostic-serial.log" || true
    else
      echo "C4B_HOST_DIAGNOSTIC_UART_MISSING"
    fi
  fi
  echo "C2V_HOST_VM_LAST_PROCESS_STATE"
  ps -p "$pid" -o pid=,stat=,etime=,%cpu=,%mem=,rss=,vsz=,comm= || true
  echo "C2V_HOST_MEMORY_STATE"
  free -m | head -n 4 || true
  echo "C2V_HOST_SERIAL_BYTES // $(wc -c < "$tmp/guest-serial.log" 2>/dev/null || echo missing)"
  tail -n 130 "$tmp/guest-serial.log" 2>/dev/null || true
  tail -n 45 "$tmp/guest-qemu.log" || true
  exit 1
fi
# The ordinary C2v success marker is necessary but not sufficient for C4a.
# Only exact runtime evidence from the real rebooted guest is accepted.
if [[ "$c4a_requested" == 1 ]]; then
  for evidence in \
    'C4A_PASS // TEST_SIGNER_UNTRUSTED_BEFORE_EXPLICIT_IMPORT' \
    'C4A_PASS // TEST_ONLY_RPM_SIGNATURE_VERIFIED_ISOLATED_FROM_BOOTED_RPMDB' \
    'C4A_PASS // SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT' \
    'C4A_PASS // FAKE_SERVICE_NEVER_STARTED_OR_ENABLED' \
    'C4A_PASS // SIGNED_FAKE_SERVICE_REMOVED_BY_REAL_BOOTED_ROLLBACK' \
    'C4A_PASS // ISOLATED_TEST_SIGNER_KEYRING_REMOVED'; do
    grep -a -Fq "$evidence" "$tmp/guest-serial.log" ||
      { echo "C4A_BLOCKED // SIGNED_SILVERBLUE_BOOT_ROLLBACK_EVIDENCE_MISSING"; exit 1; }
  done
  echo "C4A_PASS // SIGNED_FAKE_SERVICE_SILVERBLUE_TWO_REBOOT_SEQUENCE"
fi
# The C4b claim is separate from C4a's signed-package two-boot proof.
# A running confined process, D-Bus origin, negative access and service
# removal are independently mandatory; no marker is inferred from exit=0.
if [[ "$c4b_requested" == 1 ]]; then
  for evidence in \
    'C4B_PASS // SELINUX_POLICY_LOADED_WITH_ENFORCING_KERNEL' \
    'C4B_PASS // SIGNED_SILVERBLUE_EXECUTABLE_CONFINED_ENTRYPOINT' \
    'C4B_PASS // UNAUTHORIZED_DBUS_OWNERSHIP_REFUSED' \
    'C4B_PASS // REAL_SELINUX_SERVICE_DOMAIN_AND_NEGATIVE_FILE_DENIAL' \
    'C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY' \
    'C4B_PASS // EXACT_RUNTIME_ORIGIN_AND_DENY_ONLY_CLIENT_CALLS' \
    'C4B_PASS // SERVICE_STOP_RELEASES_DBUS_NAME' \
    'C4B_PASS // RUNTIME_USERS_VENV_AND_SELINUX_POLICY_CLEANED' \
    'C4B_PASS // SIGNED_CONFINED_FAKE_HOST_STOPPED_AND_REAL_SILVERBLUE_ROLLBACK'; do
    grep -a -Fq "$evidence" "$tmp/guest-serial.log" ||
      { echo "C4B_BLOCKED // CONFINED_SILVERBLUE_RUNTIME_EVIDENCE_MISSING"; exit 1; }
  done
  echo "C4B_PASS // REAL_SILVERBLUE_SIGNED_FAKE_SERVICE_OS_ORIGIN_AND_ROLLBACK"
fi
echo "C2V_PASS // ACTUAL_SILVERBLUE_BOOTED_LAYER_AND_ROLLBACK_SEQUENCE"
echo "C2V_LIMITATION // EPHEMERAL_SELF_SIGNED_INERT_PACKAGE_NOT_PRODUCTION"
