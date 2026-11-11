#!/usr/bin/bash
# Disposable real official Silverblue 44, separate C4b Identity boot harness.
# NEVER run on operator Fedora or edit the shared C2v controller.
set -Eeuo pipefail
[[ -v GITHUB_ACTIONS && "$GITHUB_ACTIONS" == true &&
   -v RUNNER_ENVIRONMENT && "$RUNNER_ENVIRONMENT" == github-hosted &&
   -v GITHUB_ACTOR && "$GITHUB_ACTOR" == kudokudo1 &&
   -v POST_APOLLO_ID_SILVERBLUE_CI_ONLY &&
   "$POST_APOLLO_ID_SILVERBLUE_CI_ONLY" == 1 ]] ||
  { echo "C4B_ID_BLOCKED // NOT_AUTHORIZED_DISPOSABLE_GITHUB_CI"; exit 2; }
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]] ||
  { echo "C4B_ID_BLOCKED // GITHUB_RUNNER_KVM_UNAVAILABLE"; exit 2; }
command -v xorriso >/dev/null && command -v genisoimage >/dev/null &&
  command -v qemu-system-x86_64 >/dev/null && command -v qemu-img >/dev/null ||
  { echo "C4B_ID_BLOCKED // MISSING_EPHEMERAL_QEMU_TOOLS"; exit 2; }
[[ $# == 1 ]] || { echo "C4B_ID_BLOCKED // SIGNED_RPM_DIRECTORY_ARGUMENT_REQUIRED"; exit 2; }
repo="$(cd "$(dirname "$0")/../../.." && pwd)"
artifact_dir="$1"
[[ -d "$artifact_dir" && -r "$artifact_dir/identity-silverblue-ci.rpm" &&
   -r "$artifact_dir/identity-artifact-manifest.sha256" ]] ||
  { echo "C4B_ID_BLOCKED // SIGNED_IDENTITY_RPM_MISSING"; exit 2; }
(cd "$artifact_dir" && sha256sum --check --status identity-artifact-manifest.sha256) ||
  { echo "C4B_ID_BLOCKED // SIGNED_RPM_ARTIFACT_HASH_MISMATCH"; exit 2; }
tmp="$(mktemp -d "$RUNNER_TEMP/c4b-identity-official-XXXXXXXX")"
pid=""
cleanup() {
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
  rm -rf -- "$tmp"
}
trap cleanup EXIT
iso=Fedora-Silverblue-ostree-x86_64-44-1.7.iso
iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682
echo "C4B_ID_SOURCE // OFFICIAL_FEDORA_SILVERBLUE_44_ISO_PINNED"
curl --fail --location --retry 2 --connect-timeout 20 --max-time 660 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Silverblue/x86_64/iso/$iso" \
  -o "$tmp/$iso"
printf '%s  %s\n' "$iso_sha" "$tmp/$iso" | sha256sum --check --status ||
  { echo "C4B_ID_BLOCKED // OFFICIAL_SILVERBLUE_ISO_SHA256_MISMATCH"; exit 2; }
mkdir "$tmp/pxe" "$tmp/seed"
xorriso -osirrox on -indev "$tmp/$iso" \
  -extract /images/pxeboot/vmlinuz "$tmp/pxe/vmlinuz" \
  -extract /images/pxeboot/initrd.img "$tmp/pxe/initrd.img" \
  >"$tmp/installer-extract.log" 2>&1 ||
  { echo "C4B_ID_BLOCKED // OFFICIAL_INSTALLER_KERNEL_NOT_FOUND"; exit 2; }
[[ -s "$tmp/pxe/vmlinuz" && -s "$tmp/pxe/initrd.img" ]] ||
  { echo "C4B_ID_BLOCKED // OFFICIAL_INSTALLER_EMPTY"; exit 2; }
for file in identity-silverblue-ci.rpm identity-disposable-rpm-public.asc \
    identity-disposable-rpm-fingerprint.txt identity-artifact-manifest.sha256; do
  install -m 0644 "$artifact_dir/$file" "$tmp/seed/$file"
done
payload="$(base64 -w0 "$repo/tests/connections/identity_silverblue/guest_identity_ostree_cycle.sh")"
helper_payload="$(base64 -w0 "$repo/tests/connections/identity_silverblue/verify_booted_rpm_mtime_only.py")"
cat >"$tmp/seed/ks.cfg" <<EOF
# CI-only disposable offline Silverblue for C4b Identity gateway package.
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
%post --erroronfail --log=/root/c4b-identity-post.log
mkdir -p /usr/local/libexec /etc/systemd/system /var/lib
echo initial > /var/lib/postapollo-id-ci-stage
base64 -d >/usr/local/libexec/postapollo-id-ci-cycle.sh <<'C4B_ID_PAYLOAD'
$payload
C4B_ID_PAYLOAD
chmod 0700 /usr/local/libexec/postapollo-id-ci-cycle.sh
# Separate immutable CI verifier; this is a diagnostics-only fixture, not an
# enrolled host origin or authorized Identity command client.
base64 -d >/usr/local/libexec/postapollo-id-ci-verify-rpm.py <<'C4B_ID_VERIFIER'
$helper_payload
C4B_ID_VERIFIER
chmod 0444 /usr/local/libexec/postapollo-id-ci-verify-rpm.py
cat > /etc/systemd/system/postapollo-id-ci-cycle.service <<'C4B_ID_BOOT_UNIT'
[Unit]
Description=Disposable C4b Identity Silverblue RPM/rollback lifecycle
After=local-fs.target
ConditionPathExists=/run/ostree-booted
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /usr/local/libexec/postapollo-id-ci-cycle.sh
TimeoutStartSec=1400
[Install]
WantedBy=multi-user.target
C4B_ID_BOOT_UNIT
systemctl enable postapollo-id-ci-cycle.service
echo C4B_ID_INSTALLER_POST_STAGED >/dev/ttyS0
%end
EOF
genisoimage -quiet -volid ID4BCI -joliet -rock \
  -o "$tmp/identity-seed.iso" "$tmp/seed"/*
qemu-img create -q -f qcow2 "$tmp/identity-silverblue.qcow2" 40G
echo "C4B_ID_PASS // OFFLINE_SEED_AND_EPHEMERAL_DISK_PREPARED"
qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -kernel "$tmp/pxe/vmlinuz" -initrd "$tmp/pxe/initrd.img" \
  -append "console=ttyS0,115200 inst.repo=cdrom inst.ks=hd:LABEL=ID4BCI:/ks.cfg inst.cmdline rd.neednet=0" \
  -serial "file:$tmp/installer-serial.log" \
  -drive "file=$tmp/identity-silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/$iso,if=ide,media=cdrom,readonly=on,index=0" \
  -drive "file=$tmp/identity-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none -no-reboot >"$tmp/installer-qemu.log" 2>&1 &
pid="$!"
installer_ready=0
for n in $(seq 1 600); do
  if [[ -r "$tmp/installer-serial.log" ]] &&
     grep -Fq 'C4B_ID_INSTALLER_POST_STAGED' "$tmp/installer-serial.log"; then
    installer_ready=1
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 2
done
if [[ "$installer_ready" != 1 ]]; then
  echo "C4B_ID_BLOCKED // OFFICIAL_SILVERBLUE_INSTALLER_NOT_COMPLETE"
  tail -n 70 "$tmp/installer-serial.log" 2>/dev/null || true
  tail -n 25 "$tmp/installer-qemu.log" 2>/dev/null || true
  exit 2
fi
kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
pid=""
echo "C4B_ID_PASS // REAL_OFFLINE_SILVERBLUE_INSTALLED"
qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -serial "file:$tmp/identity-guest-serial.log" \
  -drive "file=$tmp/identity-silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/identity-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none >"$tmp/guest-qemu.log" 2>&1 &
pid="$!"
final=0
for n in $(seq 1 700); do
  if [[ -r "$tmp/identity-guest-serial.log" ]]; then
    if grep -Fq 'C4B_ID_FAIL //' "$tmp/identity-guest-serial.log"; then
      echo "C4B_ID_BLOCKED // GUEST_REPORTED_FAILURE"
      break
    fi
    if grep -Fq 'C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED' \
        "$tmp/identity-guest-serial.log"; then
      final=1
      break
    fi
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  if (( n % 20 == 0 )); then
    echo "C4B_ID_HOST_HEARTBEAT // poll=$n"
    grep -aE 'C4B_ID_(PASS|FAIL|STAGE|BLOCKED|PENDING|RPM_VERIFY_RC|RPM_VERIFY_DETAIL)' \
      "$tmp/identity-guest-serial.log" 2>/dev/null | tail -n 12 || true
  fi
  sleep 2
done
echo "C4B_ID_HOST_EVIDENCE // BOUNDED_REAL_GUEST_MARKERS"
grep -aE 'C4B_ID_(PASS|FAIL|STAGE|BLOCKED|PENDING|RPM_VERIFY_RC|RPM_VERIFY_DETAIL)' \
  "$tmp/identity-guest-serial.log" 2>/dev/null | tail -n 65 || true
if [[ "$final" != 1 ]]; then
  echo "C4B_ID_BLOCKED // ORIGINAL_REAL_IDENTITY_OSTREE_ROLLBACK_NOT_VERIFIED"
  tail -n 100 "$tmp/identity-guest-serial.log" 2>/dev/null || true
  tail -n 25 "$tmp/guest-qemu.log" 2>/dev/null || true
  exit 2
fi
for evidence in \
  'C4B_ID_STAGE // initial' \
  'C4B_ID_PASS // SIGNED_IDENTITY_RPM_VERIFIED_OFFLINE_BEFORE_LAYER' \
  'C4B_ID_PASS // REAL_IDENTITY_RPM_OSTREE_PENDING_DEPLOYMENT' \
  'C4B_ID_STAGE // layer_pending' \
  'C4B_ID_PASS // REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT' \
  'C4B_ID_STAGE // rollback_pending' \
  'C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED' \
  'C4B_ID_PASS // TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED'; do
  [[ "$(grep -aFc "$evidence" "$tmp/identity-guest-serial.log")" == 1 ]] ||
    { echo "C4B_ID_BLOCKED // REQUIRED_SIGNED_BOOT_ROLLBACK_STAGE_MISSING"; exit 2; }
done
! grep -aFq 'C4B_ID_FAIL //' "$tmp/identity-guest-serial.log" ||
  { echo "C4B_ID_BLOCKED // GUEST_FAILURE_MARKER"; exit 2; }
echo "C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK"
echo "C4B_ID_LIMITATION // INERT_GATEWAY_ONLY_NO_SYSTEMD_SELINUX_PROCESS_ATTESTATION"
