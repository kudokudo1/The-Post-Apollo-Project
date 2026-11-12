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
[[ $# == 3 ]] || { echo "C4B_ID_BLOCKED // SIGNED_RPM_FEDORA_RUNTIME_AND_SELINUX_POLICY_DIRECTORIES_REQUIRED"; exit 2; }
repo="$(cd "$(dirname "$0")/../../.." && pwd)"
artifact_dir="$1"
runtime_dir="$2"
policy_dir="$3"
[[ -f "$policy_dir/postapollo_identity_ci.pp" &&
   -r "$policy_dir/postapollo_identity_ci.sha256" ]] ||
  { echo "C4B_ID_BLOCKED // COMPILED_TEST_SELINUX_POLICY_MISSING"; exit 2; }
(cd "$policy_dir" && sha256sum --check --status postapollo_identity_ci.sha256) ||
  { echo "C4B_ID_BLOCKED // COMPILED_TEST_SELINUX_POLICY_DIGEST_REFUSED"; exit 2; }
[[ -f "$runtime_dir/identity-python3-cryptography-f44.rpm" &&
   -r "$runtime_dir/identity-python3-cffi-f44.rpm" &&
   -r "$runtime_dir/identity-python3-pycparser-f44.rpm" &&
   -r "$runtime_dir/identity-fedora44-runtime-public.asc" &&
   -r "$runtime_dir/identity-fedora44-runtime-manifest.sha256" ]] ||
  { echo "C4B_ID_BLOCKED // VERIFIED_OFFLINE_CRYPTO_RUNTIME_MISSING"; exit 2; }
(cd "$runtime_dir" &&
 sha256sum --check --status identity-fedora44-runtime-manifest.sha256) ||
  { echo "C4B_ID_BLOCKED // OFFLINE_CRYPTO_RUNTIME_DIGEST_REFUSED"; exit 2; }
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
for file in identity-python3-cryptography-f44.rpm identity-python3-cffi-f44.rpm \
    identity-python3-pycparser-f44.rpm identity-fedora44-runtime-public.asc \
    identity-fedora44-runtime-manifest.sha256; do
  install -m 0644 "$runtime_dir/$file" "$tmp/seed/$file"
done
for file in postapollo_identity_ci.pp postapollo_identity_ci.sha256; do
  install -m 0644 "$policy_dir/$file" "$tmp/seed/$file"
done
payload="$(base64 -w0 "$repo/tests/connections/identity_silverblue/guest_identity_ostree_cycle.sh")"
helper_payload="$(base64 -w0 "$repo/tests/connections/identity_silverblue/verify_booted_rpm_mtime_only.py")"
service_probe_payload="$(base64 -w0 "$repo/tests/connections/identity_silverblue/guest_identity_service_probe.sh")"
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
base64 -d >/usr/local/libexec/postapollo-id-ci-service-probe.sh <<'C4B_ID_SERVICE_PROBE'
$service_probe_payload
C4B_ID_SERVICE_PROBE
chmod 0700 /usr/local/libexec/postapollo-id-ci-service-probe.sh
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
# Read-only host diagnostics use QMP query-status/query-cpus-fast only.
qemu-system-x86_64 \
  -machine accel=kvm -m 4096 -smp 3 -display none -monitor none \
  -serial "file:$tmp/identity-guest-serial.log" \
  -qmp "unix:$tmp/identity-qmp.sock,server=on,wait=off" \
  -drive "file=$tmp/identity-silverblue.qcow2,if=virtio,format=qcow2" \
  -drive "file=$tmp/identity-seed.iso,if=ide,media=cdrom,readonly=on,index=1" \
  -nic none >"$tmp/guest-qemu.log" 2>&1 &
pid="$!"
final=0
selinux_load_started=0
service_cleanup_seen=0
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
    # A guest policy unload can stall scheduling AFTER emitting the cleanup
    # marker: the guest watchdog then cannot speak, while the outer 700-poll
    # loop needlessly waits 23 minutes. This separate GitHub-host watchdog
    # observes the real serial file and fails CLOSED if the parent has not
    # advanced within three minutes of confirmed service cleanup.
    if grep -aFq 'C4B_ID_PASS // REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP' \
        "$tmp/identity-guest-serial.log" &&
       ! grep -aFq 'C4B_ID_STAGE // after_service_probe' \
        "$tmp/identity-guest-serial.log"; then
      if (( service_cleanup_seen == 0 )); then service_cleanup_seen=$SECONDS; fi
      if (( SECONDS - service_cleanup_seen > 180 )); then
        echo "C4B_ID_BLOCKED // GUEST_SILENT_AFTER_SERVICE_CLEANUP_NO_ROLLBACK"
        # Only QEMU/host process state, not guest memory or private identities.
        ps -o pid=,ppid=,stat=,wchan:24=,etime=,comm= -p "$pid" 2>/dev/null |
          sed 's/^/C4B_ID_STAGE // HOST_QEMU_PROCESS \/\/ /' | head -n 2 || true
        timeout --signal=TERM --kill-after=2s 12s \
          python3 - "$tmp/identity-qmp.sock" <<'C4B_QMP_STATUS' || true
import json
import socket
import sys

try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(4)
        connection.connect(sys.argv[1])
        stream = connection.makefile("rb")

        def read_response():
            for _ in range(12):
                raw = stream.readline(4096)
                if not raw:
                    raise RuntimeError("no_qmp_data")
                result = json.loads(raw)
                if "event" not in result:
                    return result
            raise RuntimeError("too_many_async_qmp_events")

        if "QMP" not in read_response():
            raise RuntimeError("invalid_qmp_greeting")
        for name in ("qmp_capabilities", "query-status", "query-cpus-fast"):
            connection.sendall(
                (json.dumps({"execute": name, "id": name}) + "\n").encode()
            )
            response = read_response()
            if response.get("id") != name or "error" in response:
                raise RuntimeError("qmp_query_refused_" + name)
            if name == "query-status":
                state = response.get("return", {})
                print(
                    "C4B_ID_STAGE // HOST_QMP // status="
                    + str(state.get("status", "unknown"))[:35]
                    + " running="
                    + str(state.get("running", "unknown"))[:6],
                    flush=True,
                )
            if name == "query-cpus-fast":
                cpus = response.get("return", [])
                if not isinstance(cpus, list):
                    raise RuntimeError("qmp_cpu_format")
                print(
                    "C4B_ID_STAGE // HOST_QMP // cpu_count=" + str(len(cpus)),
                    flush=True,
                )
except (OSError, RuntimeError, ValueError, TypeError) as exc:
    # Never print a raw QMP response or guest data in CI evidence.
    print(
        "C4B_ID_STAGE // HOST_QMP // QUERY_UNAVAILABLE_"
        + type(exc).__name__,
        flush=True,
    )
C4B_QMP_STATUS
        break
      fi
    else
      service_cleanup_seen=0
    fi
    # Independent elapsed-time watchdog for the precise guest policy-load
    # boundary. It does not grant acceptance or alter guest SELinux state.
    # A stuck semodule/kernelload previously consumed the full QEMU window.
    if grep -aFq 'C4B_ID_SELINUX_STAGE // before_module_install' "$tmp/identity-guest-serial.log" &&
       ! grep -aFq 'C4B_ID_SELINUX_STAGE // after_module_install' "$tmp/identity-guest-serial.log"; then
      if (( selinux_load_started == 0 )); then selinux_load_started=$SECONDS; fi
      if (( SECONDS - selinux_load_started > 205 )); then
        echo "C4B_ID_BLOCKED // REAL_ENFORCING_SELINUX_POLICY_LOAD_STALLED"
        break
      fi
    fi
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  if (( n % 20 == 0 )); then
    echo "C4B_ID_HOST_HEARTBEAT // poll=$n"
    grep -aE 'C4B_ID_(PASS|FAIL|STAGE|BLOCKED|PENDING|RPM_VERIFY_RC|RPM_VERIFY_DETAIL|SERVICE_OBSERVED|SERVICE_JOURNAL|SERVICE_PROBE_DETAIL|SERVICE_PROBE_RC|SELINUX_OBSERVED|SELINUX_STAGE|SELINUX_MODULE_DETAIL|SELINUX_LOAD_DETAIL|SELINUX_UNLOAD_DETAIL|SELINUX_NEGATIVE_DETAIL)' \
      "$tmp/identity-guest-serial.log" 2>/dev/null | tail -n 12 || true
  fi
  sleep 2
done
echo "C4B_ID_HOST_EVIDENCE // BOUNDED_REAL_GUEST_MARKERS"
grep -aE 'C4B_ID_(PASS|FAIL|STAGE|BLOCKED|PENDING|RPM_VERIFY_RC|RPM_VERIFY_DETAIL|SERVICE_OBSERVED|SERVICE_JOURNAL|SERVICE_PROBE_DETAIL|SERVICE_PROBE_RC|SELINUX_OBSERVED|SELINUX_STAGE|SELINUX_MODULE_DETAIL|SELINUX_LOAD_DETAIL|SELINUX_UNLOAD_DETAIL|SELINUX_NEGATIVE_DETAIL)' \
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
  'C4B_ID_PASS // SIGNED_OFFLINE_FEDORA44_ED25519_DEPENDENCY_VERIFIED' \
  'C4B_ID_PASS // REAL_IDENTITY_RPM_OSTREE_PENDING_DEPLOYMENT' \
  'C4B_ID_STAGE // layer_pending' \
  'C4B_ID_PASS // OFFLINE_SIGNED_FEDORA_ED25519_RUNTIME_BOOTED_AND_VERIFIED' \
  'C4B_ID_PASS // REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT' \
  'C4B_ID_PASS // REAL_SYSTEMD_UNIT_REFUSED_WITHOUT_MARKER' \
  'C4B_ID_PASS // DEDICATED_TEST_SELINUX_MODULE_LOADED_ENFORCING' \
  'C4B_ID_PASS // SEPARATE_LABELED_IDENTITY_EXECUTABLE_AND_EPHEMERAL_SYSTEMD_OVERRIDE' \
  'C4B_ID_PASS // REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED' \
  'C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE' \
  'C4B_ID_PASS // REAL_SYSTEMD_IDENTITY_GATEWAY_SOCKET_AND_PROCESS_OBSERVED' \
  'C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_BEGIN' \
  'C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_STATUS' \
  'C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_CANCEL' \
  'C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_RECOVER' \
  'C4B_ID_PASS // KERNEL_PEER_PID_START_AND_SUPERVISOR_RECHECKED_FOR_FOUR_SIGNED_DENIALS' \
  'C4B_ID_PASS // DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP' \
  'C4B_ID_PASS // REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP' \
  'C4B_ID_PASS // REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK' \
  'C4B_ID_STAGE // rollback_pending' \
  'C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED' \
  'C4B_ID_PASS // TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED'; do
  [[ "$(grep -aFc "$evidence" "$tmp/identity-guest-serial.log")" == 1 ]] ||
    { echo "C4B_ID_BLOCKED // REQUIRED_SIGNED_BOOT_ROLLBACK_STAGE_MISSING"; exit 2; }
done
! grep -aFq 'C4B_ID_FAIL //' "$tmp/identity-guest-serial.log" ||
  { echo "C4B_ID_BLOCKED // GUEST_FAILURE_MARKER"; exit 2; }
echo "C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK"
echo "C4B_ID_LIMITATION // CI_ONLY_CONFIRMED_CONFINEMENT_NO_INDEPENDENT_RELEASE_ROOT_SEAT_OR_C5_CONSENT"
