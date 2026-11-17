#!/usr/bin/bash
# P53 // genuine OFFLINE official Fedora 44 Silverblue phone RPM lifecycle.
# Runs exclusively in disposable GitHub KVM guest. No local machine access.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
stage=/var/lib/postapollo-phone-ci-stage
store=/var/lib/postapollo-phone-ci-assets
pkg=post-apollo-phone-status-ci
unit=post-apollo-phone-personal-status-ci.service
prefix=/usr/libexec/post-apollo/phone
data=/mnt/postapollo-phone-ci-offline
marker=/run/postapollo-phone-status-test-only/explicit-test.marker

fail() {
  echo "P53_FAIL // $1"
  timeout --signal=TERM --kill-after=2s 10s rpm-ostree status || true
  systemctl poweroff --no-block || true
  exit 78
}
trap 'rc=$?; if (( rc != 0 )); then echo "P53_FAIL // UNEXPECTED_EXIT_$rc"; systemctl poweroff --no-block || true; fi' EXIT

[[ -e /run/ostree-booted && "$(getenforce)" == Enforcing ]] ||
  fail "ENFORCING_OSTREE_BOOT_REQUIRED"
grep -Fq 'Fedora release 44' /etc/fedora-release ||
  fail "FEDORA44_REQUIRED"
ostree admin status | grep -iq silverblue ||
  fail "OFFICIAL_SILVERBLUE_DEPLOYMENT_REQUIRED"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] ||
  fail "OFFLINE_NETWORKLESS_REQUIRED"
[[ ! -e "$marker" ]] || fail "TEST_MARKER_MUST_BE_ABSENT"

phase="$(cat "$stage" 2>/dev/null || echo missing)"
echo "P53_STAGE // $phase"
case "$phase" in
  initial)
    ! rpm -q "$pkg" >/dev/null 2>&1 || fail "PHONE_RPM_PREEXISTS"
    [[ ! -e "$prefix/PhonePersonalStatusHostP49.py" &&
       ! -e /usr/lib/systemd/system/"$unit" ]] ||
      fail "PHONE_INSTALLED_FILES_PREEXIST"
    mkdir -p "$data" "$store"
    chmod 0700 "$store"
    mount -o ro /dev/disk/by-label/PH53CI "$data" ||
      fail "OFFLINE_PHONE_RPM_MEDIA_MISSING"
    (cd "$data" &&
     sha256sum --check --status phone-status-artifact-manifest.sha256 &&
     sha256sum --check --status postapollo_phone_ci.sha256) ||
      fail "OFFLINE_PHONE_ARTIFACT_DIGEST_MISMATCH"

    rpmfile="$data/phone-status-ci.rpm"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")" ==
       "$pkg 0.1 noarch" ]] || fail "WRONG_SIGNED_PHONE_RPM"
    [[ -z "$(rpm -qp --scripts "$rpmfile")" &&
       -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
      fail "AUTOEXEC_SCRIPTLETS_FORBIDDEN"

    # Prove independent untrusted state BEFORE explicitly importing the
    # disposable PHONE-only test RPM public key into an isolated test db.
    db="$store/isolated-phone-rpmdb"
    mkdir -m 0700 "$db"
    rpm --dbpath "$db" --initdb || fail "RPM_TRUST_DB_INIT"
    before="$(rpmkeys --dbpath "$db" --checksig -v "$rpmfile" 2>&1 || true)"
    printf '%s\n' "$before" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      fail "RPM_TEST_KEY_ALREADY_TRUSTED"
    rpmkeys --dbpath "$db" --import "$data/phone-status-disposable-rpm-public.asc" ||
      fail "EXPLICIT_PHONE_TEST_KEY_IMPORT"
    after="$(rpmkeys --dbpath "$db" --checksig -v "$rpmfile" 2>&1)" ||
      fail "PHONE_RPM_SIGNATURE_INVALID"
    printf '%s\n' "$after" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      fail "PHONE_RPM_SIGNATURE_NOT_CONFIRMED"
    if printf '%s\n' "$after" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      fail "PHONE_RPM_SIGNATURE_STILL_UNTRUSTED"
    fi
    install -m 0600 "$rpmfile" "$store/phone-status-ci.rpm"
    install -m 0600 "$data/postapollo_phone_ci.pp" "$store/postapollo_phone_ci.pp"
    echo "P53_PASS // OFFLINE_DISPOSABLE_PHONE_RPM_SIGNATURE_VERIFIED_BEFORE_OSTREE"

    # Refuse network repository fallback while composing the local RPM.
    mkdir -m 0700 "$store/original-repos"
    shopt -s nullglob
    for file in /etc/yum.repos.d/*.repo; do
      cp -a "$file" "$store/original-repos/$(basename "$file")"
      sed -i -E 's/^[[:space:]]*enabled[[:space:]]*=[[:space:]]*[01][[:space:]]*$/enabled=0/' "$file"
    done
    echo "P53_PASS // OFFLINE_REPOSITORIES_DISABLED"
    echo installing > "$stage"

    # Proven C4b pattern: rpm-ostree composition is a separate systemd unit,
    # and an independent monitor checks the *real pending deployment* before
    # any reboot. The invoking process return code cannot authorize reboot.
    cat >/run/p53-phone-layer-worker.sh <<'PHONE_WORKER'
#!/usr/bin/bash
set +e
timeout --signal=TERM --kill-after=15s 480s \
  rpm-ostree install --cache-only \
    /var/lib/postapollo-phone-ci-assets/phone-status-ci.rpm \
    >/var/tmp/p53-phone-install.log 2>&1
printf '%s\n' "$?" >/run/p53-phone-worker-result
PHONE_WORKER
    chmod 0700 /run/p53-phone-layer-worker.sh
    cat >/run/p53-phone-layer-monitor.sh <<'PHONE_MONITOR'
#!/usr/bin/bash
set -Eeuo pipefail
exec >/var/tmp/p53-phone-monitor.log 2>&1
for n in $(seq 1 56); do
  if timeout --signal=TERM --kill-after=3s 12s \
      rpm-ostree status --json >/run/p53-phone-status.json 2>/dev/null; then
    if python3 - /run/p53-phone-status.json <<'P53_PENDING'
import json,re,sys
doc=json.load(open(sys.argv[1],encoding="utf-8"))
deployments=doc.get("deployments") or []
if len(deployments) < 2 or doc.get("transaction") is not None:
    sys.exit(1)
head=deployments[0]
pending=bool(head.get("staged") or head.get("pending")) or head.get("booted") is False
entries=head.get("requested-local-packages") or []
pattern=r"^(?:sha256:[a-fA-F0-9]{64}:)?post-apollo-phone-status-ci-0\.1-1\.fc44\.noarch$"
if not pending or not isinstance(entries,list) or not any(
    isinstance(v,str) and re.fullmatch(pattern,v) for v in entries
):
    sys.exit(1)
print("P53_PENDING // EXACT_PHONE_OSTREE_DEPLOYMENT_OBSERVED")
P53_PENDING
    then
      if [[ -s /run/p53-phone-worker-result ]]; then
        [[ "$(cat /run/p53-phone-worker-result)" == 0 ]] || break
      fi
      echo layer_pending >/var/lib/postapollo-phone-ci-stage
      echo "P53_PASS // REAL_PHONE_RPM_OSTREE_PENDING_DEPLOYMENT" >/dev/ttyS0
      sync
      systemctl reboot --no-block
      exit 0
    fi
  fi
  [[ -s /run/p53-phone-worker-result &&
     "$(cat /run/p53-phone-worker-result)" != 0 ]] && break
  sleep 15
done
echo "P53_FAIL // PHONE_OSTREE_PENDING_DEPLOYMENT_NOT_VERIFIED" >/dev/ttyS0
tail -n 35 /var/tmp/p53-phone-install.log >/dev/ttyS0 || true
systemctl poweroff --no-block || true
exit 78
PHONE_MONITOR
    chmod 0700 /run/p53-phone-layer-monitor.sh
    systemd-run --quiet --unit=p53-phone-layer-monitor --property=Type=exec \
      /usr/bin/bash /run/p53-phone-layer-monitor.sh ||
      fail "PHONE_LAYER_MONITOR_START"
    systemd-run --quiet --unit=p53-phone-layer-worker --property=Type=exec \
      /usr/bin/bash /run/p53-phone-layer-worker.sh ||
      fail "PHONE_LAYER_WORKER_START"
    echo "P53_STAGE // SEPARATE_PHONE_OSTREE_WORKER_MONITOR_RUNNING"
    ;;
  installing)
    fail "UNAUTHORIZED_REBOOT_BEFORE_PENDING_STATUS"
    ;;
  layer_pending)
    [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}' "$pkg")" ==
       "$pkg 0.1 noarch" ]] || fail "SIGNED_PHONE_RPM_NOT_BOOTED"
    [[ -f "$prefix/PhonePersonalStatusHostP49.py" &&
       -f "/usr/lib/systemd/system/$unit" ]] ||
      fail "INSTALLED_PHONE_UNIT_OR_CODE_MISSING"
    [[ "$(rpm -ql "$pkg" | grep -Ec '^/usr/lib(exec)?/')" == 6 ]] ||
      fail "PHONE_RPM_PAYLOAD_NOT_SIX_FILES"
    # OSTree may use content-addressed hardlinks. Do not demand nlink=1.
    # rpm -V --nomtime still verifies all size/digests/owner/mode/group.
    verify=/var/tmp/p53-phone-booted-rpm-verify.log
    rc=0
    timeout --signal=TERM --kill-after=3s 35s rpm -V --nomtime "$pkg" \
      >"$verify" 2>&1 || rc=$?
    if [[ "$rc" != 0 || -s "$verify" ]]; then
      sed -n '1,24p' "$verify" |
        sed 's/^/P53_RPM_VERIFY_DETAIL \/\//g' || true
      fail "BOOTED_PHONE_RPM_DIGEST_OR_MODE_REFUSED"
    fi
    for name in \
      PhonePersonalHostSocketP47.py PhonePersonalPeerEvidenceP48.py \
      PhonePersonalStatusHostP49.py PhonePersonalInstalledReleaseP50.py; do
      path="$prefix/$name"
      [[ -f "$path" && ! -L "$path" &&
         "$(stat -c '%u:%g:%a' "$path")" == '0:0:555' &&
         "$(rpm -qf --qf '%{NAME}' "$path")" == "$pkg" ]] ||
        fail "BOOTED_PHONE_INSTALLED_MODULE_REFUSED"
    done
    for path in "$prefix/systemd/$unit" "/usr/lib/systemd/system/$unit"; do
      [[ -f "$path" && ! -L "$path" &&
         "$(stat -c '%u:%g:%a' "$path")" == '0:0:644' ]] ||
        fail "BOOTED_PHONE_UNIT_MISMATCH"
    done
    active="$(systemctl show "$unit" --property=ActiveState --value)"
    [[ "$active" != active && ! -e "$marker" ]] ||
      fail "INERT_PHONE_SERVICE_ALREADY_ACTIVATED"
    enabled="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
    [[ "$enabled" == static || "$enabled" == disabled ]] ||
      fail "PHONE_UNIT_AUTOMATICALLY_ENABLED"
    echo "P53_PASS // BOOTED_PHONE_SIGNED_RPM_EXACT_FILES_AND_INERT_UNIT"

    probe=/usr/local/libexec/p53-phone-guest-service-probe.sh
    [[ -f "$probe" && ! -L "$probe" &&
       "$(stat -c '%u:%g:%a' "$probe")" == 0:0:700 ]] ||
      fail "INDEPENDENT_PHONE_SERVICE_PROBE_MISSING"
    rc=0
    timeout --signal=TERM --kill-after=6s 540s \
      /usr/bin/bash "$probe" >/var/tmp/p53-phone-service-probe.log 2>&1 || rc=$?
    if [[ "$rc" != 0 ]]; then
      sed -n '1,90p' /var/tmp/p53-phone-service-probe.log |
        sed 's/^/P53_PROBE_DETAIL \/\//g' || true
      fail "INSTALLED_PHONE_SERVICE_PROBE_REFUSED"
    fi
    [[ ! -d /run/systemd/system/"$unit".d &&
       ! -e "$marker" ]] || fail "PROBE_LEFT_SERVICE_OVERRIDE"
    ! getent passwd postapollo-phone-status-ci >/dev/null ||
      fail "PROBE_LEFT_TEST_ACCOUNT"
    ! semodule -l | grep -Eq '^postapollo_phone_ci([[:space:]]|$)' ||
      fail "PROBE_LEFT_TEST_SELINUX_MODULE"
    echo "P53_PASS // REAL_PHONE_ENFORCING_SERVICE_PROBE_FINISHED_AND_CLEAN"
    echo rollback_pending > "$stage"
    echo "P53_STAGE // rollback_command_started"
    rpm-ostree rollback --reboot || fail "PHONE_OSTREE_ROLLBACK_COMMAND_REFUSED"
    ;;
  rollback_pending)
    ! rpm -q "$pkg" >/dev/null 2>&1 || fail "PHONE_RPM_SURVIVED_OSTREE_ROLLBACK"
    for path in \
      "$prefix/PhonePersonalHostSocketP47.py" \
      "$prefix/PhonePersonalPeerEvidenceP48.py" \
      "$prefix/PhonePersonalStatusHostP49.py" \
      "$prefix/PhonePersonalInstalledReleaseP50.py" \
      "$prefix/systemd/$unit" \
      "/usr/lib/systemd/system/$unit"; do
      [[ ! -e "$path" ]] || fail "PHONE_FILE_SURVIVED_OSTREE_ROLLBACK"
    done
    [[ "$(getenforce)" == Enforcing &&
       ! -e "$marker" &&
       ! -d /run/postapollo-phone-status-test-only &&
       ! -d /run/systemd/system/"$unit".d ]] ||
      fail "SELINUX_OR_TEST_RUNTIME_REMAINED_AFTER_ROLLBACK"
    ! getent passwd postapollo-phone-status-ci >/dev/null ||
      fail "PHONE_TEST_USER_REMAINS_AFTER_ROLLBACK"
    ! semodule -l | grep -Eq '^postapollo_phone_ci([[:space:]]|$)' ||
      fail "PHONE_TEST_SELINUX_POLICY_REMAINS_AFTER_ROLLBACK"
    for file in "$store"/original-repos/*.repo; do
      [[ -f "$file" ]] || continue
      cp -a "$file" "/etc/yum.repos.d/$(basename "$file")"
    done
    rm -rf -- "$store"
    [[ ! -e "$store" ]] || fail "PHONE_DISPOSABLE_KEYRING_OR_RPM_REMAINS"
    echo complete > "$stage"
    echo "P53_PASS // REAL_SILVERBLUE_PHONE_RPM_LAYER_REMOVED_AFTER_TWO_REBOOTS"
    echo "P53_PASS // PHONE_TEST_SIGNER_AND_RUNTIME_REMOVED_NO_SAVE"
    systemctl poweroff --no-block || fail "FINAL_POWER_OFF"
    ;;
  complete)
    systemctl poweroff --no-block
    ;;
  *)
    fail "INVALID_PHONE_OSTREE_STAGE"
    ;;
esac
