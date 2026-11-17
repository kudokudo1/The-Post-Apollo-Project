#!/usr/bin/bash
# P53 // Official Fedora 44 Silverblue *offline KVM VM* runner for PHONE only.
# Uses C4b's independently proven ISO SHA/installation pattern but NO Identity
# service, key, policy, screenshot, release root, or consent credentials.
set -Eeuo pipefail

[[ "${GITHUB_ACTIONS:-}" == true &&
   "${RUNNER_ENVIRONMENT:-}" == github-hosted &&
   "${GITHUB_ACTOR:-}" == kudokudo1 &&
   "${POST_APOLLO_PHONE_RPM_CI_ONLY:-}" == 1 ]] ||
  { echo "P53_BLOCKED // GITHUB_DISPOSABLE_ACTOR_REQUIRED"; exit 78; }
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]] ||
  { echo "P53_BLOCKED // ISOLATED_KVM_UNAVAILABLE"; exit 78; }
for app in qemu-img qemu-system-x86_64 xorriso genisoimage curl; do
  command -v "$app" >/dev/null ||
    { echo "P53_BLOCKED // OFFICIAL_SILVERBLUE_VM_TOOLS_MISSING"; exit 78; }
done
[[ $# == 2 ]] ||
  { echo "P53_BLOCKED // EXACT_RPM_AND_POLICY_DIRECTORIES_REQUIRED"; exit 78; }

source_root="$(cd "$(dirname "$0")/../.." && pwd)"
rpm_dir="$1"
policy_dir="$2"
[[ -r "$rpm_dir/phone-status-ci.rpm" &&
   -r "$rpm_dir/phone-status-artifact-manifest.sha256" &&
   -r "$policy_dir/postapollo_phone_ci.pp" &&
   -r "$policy_dir/postapollo_phone_ci.sha256" ]] ||
  { echo "P53_BLOCKED // PHONE_RPM_OR_POLICY_ARTIFACTS_MISSING"; exit 78; }
(cd "$rpm_dir" && sha256sum --check --status phone-status-artifact-manifest.sha256) ||
  { echo "P53_BLOCKED // PHONE_RPM_ARTIFACT_HASH_REFUSED"; exit 78; }
(cd "$policy_dir" && sha256sum --check --status postapollo_phone_ci.sha256) ||
  { echo "P53_BLOCKED // PHONE_SELINUX_POLICY_HASH_REFUSED"; exit 78; }

temp_base="${RUNNER_TEMP:-/tmp}"
tmp="$(mktemp -d "$temp_base/p53-phone-official-silverblue-XXXXXXXX")"
pid=""
cleanup() {
  if [[ -n "$pid" ]]; then
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$tmp"
}
trap cleanup EXIT

iso=Fedora-Silverblue-ostree-x86_64-44-1.7.iso
iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682
echo "P53_SOURCE // EXACT_PINNED_OFFICIAL_FEDORA44_SILVERBLUE_ISO"
curl --fail --location --retry 2 --connect-timeout 20 --max-time 660 \
  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Silverblue/x86_64/iso/$iso" \
  -o "$tmp/$iso" ||
  { echo "P53_BLOCKED // OFFICIAL_SILVERBLUE_DOWNLOAD"; exit 78; }
printf '%s  %s\n' "$iso_sha" "$tmp/$iso" |
  sha256sum --check --status ||
  { echo "P53_BLOCKED // PINNED_OFFICIAL_SILVERBLUE_ISO_DIGEST"; exit 78; }
mkdir "$tmp/pxe" "$tmp/seed"
xorriso -osirrox on -indev "$tmp/$iso" \
  -extract /images/pxeboot/vmlinuz "$tmp/pxe/vmlinuz" \
  -extract /images/pxeboot/initrd.img "$tmp/pxe/initrd.img" \
  >"$tmp/installer-extract.log" 2>&1 ||
  { echo "P53_BLOCKED // OFFICIAL_BOOT_KERNEL_EXTRACTION"; exit 78; }
[[ -s "$tmp/pxe/vmlinuz" && -s "$tmp/pxe/initrd.img" ]] ||
  { echo "P53_BLOCKED // OFFICIAL_INSTALLER_KERNEL_EMPTY"; exit 78; }

for name in phone-status-ci.rpm phone-status-disposable-rpm-public.asc \
  phone-status-disposable-rpm-fingerprint.txt phone-status-artifact-manifest.sha256; do
  install -m 0644 "$rpm_dir/$name" "$tmp/seed/$name"
done
for name in postapollo_phone_ci.pp postapollo_phone_ci.sha256; do
  install -m 0644 "$policy_dir/$name" "$tmp/seed/$name"
done

cycle="$(base64 -w0 "$source_root/tests/phone/p53_guest_phone_ostree_cycle.sh")"
probe="$(base64 -w0 "$source_root/tests/phone/p53_guest_phone_service_probe.sh")"
cat >"$tmp/seed/ks.cfg" <<EOF
# Official Fedora 44 Silverblue booted in offline disposable PHONE-only KVM.
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
%post --erroronfail --log=/root/p53-phone-ks-post.log
mkdir -p /usr/local/libexec /etc/systemd/system /var/lib
echo initial >/var/lib/postapollo-phone-ci-stage
base64 -d >/usr/local/libexec/p53-phone-guest-cycle.sh <<'P53_CYCLE'
$cycle
P53_CYCLE
chmod 0700 /usr/local/libexec/p53-phone-guest-cycle.sh
base64 -d >/usr/local/libexec/p53-phone-guest-service-probe.sh <<'P53_PROBE'
$probe
P53_PROBE
chmod 0700 /usr/local/libexec/p53-phone-guest-service-probe.sh
cat >/etc/systemd/system/p53-phone-guest-cycle.service <<'P53_CYCLE_UNIT'
[Unit]
Description=Disposable PHONE Signed Silverblue RPM/rollback observer, no SAVE
After=local-fs.target
ConditionPathExists=/run/ostree-booted
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /usr/local/libexec/p53-phone-guest-cycle.sh
TimeoutStartSec=1200
[Install]
WantedBy=multi-user.target
P53_CYCLE_UNIT
systemctl enable p53-phone-guest-cycle.service
echo P53_INSTALLER_POST_STAGED >/dev/ttyS0
%end
EOF

genisoimage -quiet -volid PH53CI -joliet -rock \
  -o "$tmp/phone-seed.iso" "$tmp/seed"/*
qemu-img create -q -f qcow2 "$tmp/phone-silverblue.qcow2" 40G
echo "P53_PASS // PINNED_OFFLINE_PHONE_SILVERBLUE_INSTALL_MEDIA_PREPARED"

qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -kernel "$tmp/pxe/vmlinuz" -initrd "$tmp/pxe/initrd.img" \
  -append "console=ttyS0,115200 inst.repo=cdrom inst.ks=hd:LABEL=PH53CI:/ks.cfg inst.cmdline rd.neednet=0" \
  -serial "file:$tmp/installer-serial.log" \
  -drive "file=$tmp/phone-silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/$iso,if=ide,media=cdrom,readonly=on,index=0" \
  -drive "file=$tmp/phone-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none -no-reboot >"$tmp/installer-qemu.log" 2>&1 &
pid="$!"
staged=0
for n in $(seq 1 600); do
  if [[ -r "$tmp/installer-serial.log" ]] &&
     grep -aFq 'P53_INSTALLER_POST_STAGED' "$tmp/installer-serial.log"; then
    staged=1
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 2
done
if [[ "$staged" != 1 ]]; then
  echo "P53_BLOCKED // OFFICIAL_SILVERBLUE_KICKSTART_INSTALL_NOT_VERIFIED"
  tail -n 70 "$tmp/installer-serial.log" 2>/dev/null || true
  tail -n 20 "$tmp/installer-qemu.log" 2>/dev/null || true
  exit 78
fi
kill "$pid" >/dev/null 2>&1 || true
wait "$pid" >/dev/null 2>&1 || true
pid=""
echo "P53_PASS // ACTUAL_OFFLINE_SILVERBLUE_INSTALLED_IN_KVM"

qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -serial "file:$tmp/guest-serial.log" \
  -drive "file=$tmp/phone-silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/phone-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none >"$tmp/guest-qemu.log" 2>&1 &
pid="$!"
completed=0
policy_started=0
post_policy_started=0
post_process_started=0
post_status_started=0
post_cross_uid_started=0
for n in $(seq 1 1850); do
  if [[ -r "$tmp/guest-serial.log" ]]; then
    if grep -aFq 'P53_FAIL //' "$tmp/guest-serial.log"; then
      echo "P53_BLOCKED // OFFLINE_PHONE_GUEST_REPORTED_FAILURE"
      break
    fi
    if grep -aFq 'P53_PASS // REAL_SILVERBLUE_PHONE_RPM_LAYER_REMOVED_AFTER_TWO_REBOOTS' \
         "$tmp/guest-serial.log"; then
      completed=1
      break
    fi
    # Separate host watchdog for expensive SELinux kernel policy load.
    if grep -aFq 'P53_STAGE // before_phone_selinux_install' "$tmp/guest-serial.log" &&
       ! grep -aFq 'P53_STAGE // after_phone_selinux_install' "$tmp/guest-serial.log"; then
      if (( policy_started == 0 )); then policy_started=$SECONDS; fi
      if (( SECONDS - policy_started > 205 )); then
        echo "P53_BLOCKED // REAL_PHONE_SELINUX_KERNEL_LOAD_STALLED"
        break
      fi
    else
      policy_started=0
    fi

    # The first full VM reached a successfully installed PHONE policy and
    # then made no further serial progress until the 70-minute CI cutoff.
    # Separate post-policy deadlines are diagnostic and fail closed: unlike
    # a long outer KVM timer, these identify the *physical* stalled phase.
    if grep -aFq 'P53_PASS // DISTINCT_PHONE_SELINUX_TEST_DOMAIN_LOADED_ENFORCING' "$tmp/guest-serial.log" &&
       ! grep -aFq 'P53_PASS // REAL_ENFORCING_PHONE_DOMAIN_AND_SYSTEMD_PROCESS_OBSERVED' "$tmp/guest-serial.log"; then
      if (( post_policy_started == 0 )); then post_policy_started=$SECONDS; fi
      if (( SECONDS - post_policy_started > 210 )); then
        echo "P53_BLOCKED // PHONE_SERVICE_POST_POLICY_START_STALLED"
        echo "P53_HOST_LAST_PHONE_STAGE // $(grep -aF 'P53_STAGE //' "$tmp/guest-serial.log" | tail -n 1 | cut -c1-155)"
        break
      fi
    else
      post_policy_started=0
    fi
    if grep -aFq 'P53_PASS // REAL_ENFORCING_PHONE_DOMAIN_AND_SYSTEMD_PROCESS_OBSERVED' "$tmp/guest-serial.log" &&
       ! grep -aFq 'P53_PASS // REAL_INSTALLED_PHONE_STATUS_RESPONSE_ALL_SAVE_FLAGS_FALSE' "$tmp/guest-serial.log"; then
      if (( post_process_started == 0 )); then post_process_started=$SECONDS; fi
      if (( SECONDS - post_process_started > 70 )); then
        echo "P53_BLOCKED // PHONE_SERVICE_STATUS_CLIENT_STALLED"
        break
      fi
    else
      post_process_started=0
    fi
    if grep -aFq 'P53_PASS // REAL_INSTALLED_PHONE_STATUS_RESPONSE_ALL_SAVE_FLAGS_FALSE' "$tmp/guest-serial.log" &&
       ! grep -aFq 'P53_PASS // CROSS_UID_HOST_ACCESS_REFUSED' "$tmp/guest-serial.log"; then
      if (( post_status_started == 0 )); then post_status_started=$SECONDS; fi
      if (( SECONDS - post_status_started > 70 )); then
        echo "P53_BLOCKED // PHONE_SERVICE_CROSS_UID_REFUSAL_STALLED"
        break
      fi
    else
      post_status_started=0
    fi
    if grep -aFq 'P53_PASS // CROSS_UID_HOST_ACCESS_REFUSED' "$tmp/guest-serial.log" &&
       ! grep -aFq 'P53_PASS // REAL_PHONE_ENFORCING_SERVICE_PROBE_FINISHED_AND_CLEAN' "$tmp/guest-serial.log"; then
      if (( post_cross_uid_started == 0 )); then post_cross_uid_started=$SECONDS; fi
      if (( SECONDS - post_cross_uid_started > 275 )); then
        echo "P53_BLOCKED // PHONE_SERVICE_STOP_POLICY_UNLOAD_STALLED"
        echo "P53_HOST_LAST_PHONE_STAGE // $(grep -aF 'P53_STAGE //' "$tmp/guest-serial.log" | tail -n 1 | cut -c1-155)"
        break
      fi
    else
      post_cross_uid_started=0
    fi
  fi
  kill -0 "$pid" 2>/dev/null || break
  if (( n % 30 == 0 )); then
    echo "P53_HOST_HEARTBEAT // poll=$n"
    grep -aE '^P53_(PASS|FAIL|STAGE|PENDING|BLOCKED|PROBE_DETAIL|RPM_VERIFY_DETAIL)' \
      "$tmp/guest-serial.log" 2>/dev/null | tail -n 12 || true
  fi
  sleep 2
done
echo "P53_HOST_EVIDENCE // BOUNDED_REAL_PHONE_GUEST_MARKERS"
grep -aE '^P53_(PASS|FAIL|STAGE|PENDING|BLOCKED|PROBE_DETAIL|RPM_VERIFY_DETAIL)' \
  "$tmp/guest-serial.log" 2>/dev/null | tail -n 75 || true
if [[ "$completed" != 1 ]]; then
  echo "P53_BLOCKED // TWO_BOOT_PHONE_RPM_OSTREE_ROLLBACK_NOT_VERIFIED"
  tail -n 75 "$tmp/guest-serial.log" 2>/dev/null || true
  tail -n 20 "$tmp/guest-qemu.log" 2>/dev/null || true
  exit 78
fi

for evidence in \
  'P53_STAGE // initial' \
  'P53_PASS // OFFLINE_DISPOSABLE_PHONE_RPM_SIGNATURE_VERIFIED_BEFORE_OSTREE' \
  'P53_PASS // REAL_PHONE_RPM_OSTREE_PENDING_DEPLOYMENT' \
  'P53_STAGE // layer_pending' \
  'P53_PASS // BOOTED_PHONE_SIGNED_RPM_EXACT_FILES_AND_INERT_UNIT' \
  'P53_PASS // BOOTED_SIGNED_PHONE_UNIT_INERT_WITHOUT_TEST_MARKER' \
  'P53_PASS // DISTINCT_PHONE_SELINUX_TEST_DOMAIN_LOADED_ENFORCING' \
  'P53_PASS // REAL_ENFORCING_PHONE_DOMAIN_AND_SYSTEMD_PROCESS_OBSERVED' \
  'P53_PASS // REAL_INSTALLED_PHONE_STATUS_RESPONSE_ALL_SAVE_FLAGS_FALSE' \
  'P53_PASS // CROSS_UID_HOST_ACCESS_REFUSED' \
  'P53_PASS // REAL_PHONE_ENFORCING_SERVICE_PROBE_FINISHED_AND_CLEAN' \
  'P53_STAGE // rollback_pending' \
  'P53_PASS // REAL_SILVERBLUE_PHONE_RPM_LAYER_REMOVED_AFTER_TWO_REBOOTS' \
  'P53_PASS // PHONE_TEST_SIGNER_AND_RUNTIME_REMOVED_NO_SAVE'; do
  [[ "$(grep -aFc "$evidence" "$tmp/guest-serial.log")" == 1 ]] ||
    { echo "P53_BLOCKED // REQUIRED_REAL_PHONE_BOOT_MARKER_MISSING_OR_DUPLICATE"; exit 78; }
done
! grep -aFq 'P53_FAIL //' "$tmp/guest-serial.log" ||
  { echo "P53_BLOCKED // PHONE_GUEST_HAS_FAILURE"; exit 78; }
echo "P53_PASS // OFFICIAL_SILVERBLUE_SIGNED_PHONE_RPM_CONFINED_SERVICE_TWO_BOOT_ROLLBACK"
echo "P53_LIMITATION // CI_TEST_SIGNER_NOT_ENROLLED_NO_C3E_OR_C5_NO_SAVE"
