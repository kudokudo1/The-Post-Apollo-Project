#!/usr/bin/bash
# C4b Identity-specific official Fedora Silverblue 44 real OSTree lifecycle.
# Installed only by the separate GitHub disposable VM controller. No desktop use.
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1
stage=/var/lib/postapollo-id-ci-stage
store=/var/lib/postapollo-id-ci-assets
pkg=post-apollo-identity-silverblue-ci
unit=post-apollo-identity-silverblue-ci.service
prefix=/usr/libexec/post-apollo/identity
marker=/run/postapollo-identity-silverblue-ci-only/authorized-test.marker
data=/mnt/postapollo-id-ci-offline
fail() {
  echo "C4B_ID_FAIL // $1"
  timeout --signal=TERM --kill-after=3s 12s rpm-ostree status || true
  systemctl poweroff --no-block || true
  exit 2
}
trap 'rc=$?; if [[ "$rc" != 0 ]]; then echo "C4B_ID_FAIL // UNEXPECTED_EXIT_$rc-LINE_$LINENO"; systemctl poweroff --no-block || true; fi' EXIT
[[ -e /run/ostree-booted && "$(getenforce)" == Enforcing ]] ||
  fail "REAL_ENFORCING_OSTREE_REQUIRED"
grep -Fq 'Fedora release 44' /etc/fedora-release ||
  fail "FEDORA_44_REQUIRED"
ostree admin status | grep -iq silverblue || fail "OFFICIAL_SILVERBLUE_REF_REQUIRED"
[[ -z "$(find /sys/class/net -maxdepth 1 -type l ! -name lo -printf '%f ')" ]] ||
  fail "OFFLINE_NO_NETWORK_REQUIRED"
[[ ! -e "$marker" ]] || fail "TEST_SERVICE_MARKER_MUST_BE_ABSENT"
phase="$(cat "$stage" 2>/dev/null || echo missing)"
echo "C4B_ID_STAGE // $phase"
case "$phase" in
  initial)
    if rpm -q "$pkg" >/dev/null 2>&1; then fail "PACKAGE_PREEXISTS"; fi
    [[ ! -e "$prefix/identity-gateway-ci" &&
       ! -e /usr/lib/systemd/system/"$unit" ]] ||
      fail "IDENTITY_GATEWAY_PREEXISTS"
    mkdir -p "$data" "$store"
    chmod 0700 "$store"
    mount -o ro /dev/disk/by-label/ID4BCI "$data" ||
      fail "OFFLINE_ASSET_MEDIA_MISSING"
    (
      cd "$data"
      sha256sum --check --status identity-artifact-manifest.sha256
    ) || fail "OFFLINE_ARTIFACT_SHA_REFUSED"
    rpmfile="$data/identity-silverblue-ci.rpm"
    [[ "$(rpm -qp --qf '%{NAME} %{VERSION} %{ARCH}' "$rpmfile")" == "$pkg 0.1 noarch" ]] ||
      fail "WRONG_SIGNED_RPM_ROLE"
    [[ -z "$(rpm -qp --scripts "$rpmfile")" &&
       -z "$(rpm -qp --triggers "$rpmfile")" ]] ||
      fail "AUTOEXEC_SCRIPTLET_REFUSED"
    # An isolated disposable key database, not the guest's system rpmdb.
    keydb="$store/isolated-rpmdb"
    mkdir -m 0700 "$keydb"
    rpm --dbpath "$keydb" --initdb || fail "ISOLATED_KEYDB_FAILED"
    pretrust="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1 || true)"
    printf '%s\n' "$pretrust" | grep -Eiq 'NOKEY|NOTTRUSTED|MISSING' ||
      fail "SIGNED_RPM_PRETRUST_MUST_FAIL"
    rpmkeys --dbpath "$keydb" --import "$data/identity-disposable-rpm-public.asc" ||
      fail "ISOLATED_KEY_IMPORT_FAILED"
    verified="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)" ||
      fail "ISOLATED_SIGNED_RPM_VERIFICATION_FAILED"
    printf '%s\n' "$verified" | grep -Eiq 'Signature.*OK|RSA.*OK|PGP.*OK|Header.*OK' ||
      fail "RPM_SIGNATURE_NOT_CONFIRMED"
    if printf '%s\n' "$verified" | grep -Eiq 'NOKEY|NOTTRUSTED|NOT OK|MISSING|BAD'; then
      fail "SIGNATURE_CONTAINS_UNTRUSTED_MARKER"
    fi
    install -m 0600 "$rpmfile" "$store/identity-silverblue-ci.rpm"
    install -m 0600 "$data/identity-artifact-manifest.sha256" "$store/seed-manifest"
    echo "C4B_ID_PASS // SIGNED_IDENTITY_RPM_VERIFIED_OFFLINE_BEFORE_LAYER"
    # Never let disabled Internet repositories supply a replacement package.
    backup="$store/original-repos"
    mkdir -m 0700 -p "$backup"
    shopt -s nullglob
    for file in /etc/yum.repos.d/*.repo; do
      cp -a "$file" "$backup/$(basename "$file")"
      sed -i -E 's/^[[:space:]]*enabled[[:space:]]*=[[:space:]]*[01][[:space:]]*$/enabled=0/' "$file"
    done
    echo "C4B_ID_PASS // NETWORKLESS_REPOSITORIES_DISABLED"
    echo installing > "$stage"
    # The original C2v observed a real rpm-ostree transition outliving
    # the original oneshot. Use an independent monitor and installer cgroup;
    # a worker exit code by itself cannot authorize a reboot.
    cat >/run/id-ci-layer-worker.sh <<'ID_WORKER'
#!/usr/bin/bash
set +e
timeout --signal=TERM --kill-after=15s 480s \
  rpm-ostree install --cache-only /var/lib/postapollo-id-ci-assets/identity-silverblue-ci.rpm \
  >/var/tmp/id-ci-install.log 2>&1
printf '%s\n' "$?" >/run/id-ci-worker-result
ID_WORKER
    chmod 0700 /run/id-ci-layer-worker.sh
    cat >/run/id-ci-layer-monitor.sh <<'ID_MONITOR'
#!/usr/bin/bash
set -Eeuo pipefail
exec >/var/tmp/id-ci-monitor.log 2>&1
pkg=post-apollo-identity-silverblue-ci
for n in $(seq 1 56); do
  if timeout --signal=TERM --kill-after=3s 12s \
      rpm-ostree status --json >/run/id-ci-status.json 2>/dev/null; then
    if python3 - /run/id-ci-status.json "$pkg" <<'ID_PENDING'
import json, re, sys
with open(sys.argv[1], encoding="utf-8") as fp:
    doc=json.load(fp)
ds=doc.get("deployments") or []
if len(ds) < 2 or doc.get("transaction") is not None:
    sys.exit(1)
head=ds[0]
pending=bool(head.get("staged") or head.get("pending")) or head.get("booted") is False
refs=head.get("requested-local-packages") or []
expected=r"^(?:sha256:[0-9a-fA-F]{64}:)?"+re.escape(sys.argv[2])+r"-0\.1-1\.fc44\.noarch$"
if not pending or not isinstance(refs,list) or not any(
        isinstance(v,str) and re.fullmatch(expected,v) for v in refs):
    sys.exit(1)
print("C4B_ID_PENDING_EXACT_IDENTITY_DEPLOYMENT")
ID_PENDING
    then
      if [[ -s /run/id-ci-worker-result ]]; then
        [[ "$(cat /run/id-ci-worker-result)" == 0 ]] || break
      fi
      echo layer_pending >/var/lib/postapollo-id-ci-stage
      echo "C4B_ID_PASS // REAL_IDENTITY_RPM_OSTREE_PENDING_DEPLOYMENT" >/dev/ttyS0
      sync
      systemctl reboot --no-block
      exit 0
    fi
  fi
  if [[ -s /run/id-ci-worker-result ]] &&
     [[ "$(cat /run/id-ci-worker-result)" != 0 ]]; then
    break
  fi
  sleep 15
done
echo "C4B_ID_FAIL // RPM_OSTREE_IDENTITY_PENDING_NEVER_PROVEN" >/dev/ttyS0
tail -n 35 /var/tmp/id-ci-install.log >/dev/ttyS0 || true
tail -n 35 /var/tmp/id-ci-monitor.log >/dev/ttyS0 || true
systemctl poweroff --no-block || true
exit 2
ID_MONITOR
    chmod 0700 /run/id-ci-layer-monitor.sh
    # The monitor is launched first, before any RPM composition begins.
    systemd-run --quiet --unit=id-ci-layer-monitor --property=Type=exec \
      /usr/bin/bash /run/id-ci-layer-monitor.sh ||
      fail "MONITOR_UNIT_START_REFUSED"
    systemd-run --quiet --unit=id-ci-layer-worker --property=Type=exec \
      /usr/bin/bash /run/id-ci-layer-worker.sh ||
      fail "WORKER_UNIT_START_REFUSED"
    echo "C4B_ID_PASS // SEPARATE_INSTALL_WORKER_AND_MONITOR_STARTED"
    ;;
  installing)
    # If first-boot monitor exited without verified pending deployment, fail
    # rather than treating a reboot as proof.
    fail "UNAUTHORIZED_REBOOT_DURING_INSTALL"
    ;;
  layer_pending)
    [[ "$(rpm -q --qf '%{NAME} %{VERSION} %{ARCH}' "$pkg")" == "$pkg 0.1 noarch" ]] ||
      fail "LAYER_NOT_IN_BOOTED_RPMDB"
    [[ -e "$prefix/identity-gateway-ci" &&
       -f "/usr/lib/systemd/system/$unit" ]] ||
      fail "IDENTITY_ENTRYPOINT_OR_UNIT_NOT_BOOTED"
    # No condition marker is installed and user/group do not exist. This unit
    # must remain unable to start; separately proving a real confined service
    # is the next C4b milestone, NOT inferred from successful RPM layering.
    if systemctl is-active --quiet "$unit"; then
      fail "DENY_ONLY_IDENTITY_UNIT_UNEXPECTEDLY_ACTIVE"
    fi
    # A unit with no [Install] section is "static"; systemctl is-enabled
    # may return success for that legitimate inert state. Inspect the actual
    # state rather than treating exit code zero as auto-enablement.
    enabled_state="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
    [[ "$enabled_state" == static || "$enabled_state" == disabled ]] ||
      fail "IDENTITY_UNIT_WAS_AUTOENABLED_OR_MASKED"
    [[ ! -e "$marker" ]] || fail "SERVICE_MARKER_UNEXPECTEDLY_PRESENT"
    count="$(rpm -ql "$pkg" | grep -E '^/usr/lib(exec)?/' | wc -l)"
    [[ "$count" == 9 ]] || fail "IDENTITY_BOOTED_PAYLOAD_NOT_NINE_FILES"
    # rpm-ostree may check out immutable /usr files as hardlinks to objects
    # in its content-addressed OSTree store. A link count >1 is therefore not
    # evidence of a writable or replaced Identity file. The original RPM
    # was signature-verified with an isolated keyring before composition;
    # verify every installed file's size, digest, mode, ownership, and type
    # against the booted RPM database before accepting this CI boot.
    verify_file=/var/tmp/id-ci-booted-rpm-verify.log
    verify_rc=0
    # Durable bounded diagnostics before a deliberate poweroff. Last failure
    # left an empty captured value and no readable rpm -V refusal specifics.
    timeout --signal=TERM --kill-after=3s 35s rpm -V "$pkg" >"$verify_file" 2>&1 ||
      verify_rc="$?"
    if [[ "$verify_rc" != 0 || -s "$verify_file" ]]; then
      printf 'C4B_ID_RPM_VERIFY_RC // %s\n' "$verify_rc" >/dev/ttyS0
      # Preserve every bounded diagnostic record through the host collector.
      sed -n '1,24p' "$verify_file" |
        sed -E 's/^/C4B_ID_RPM_VERIFY_DETAIL \/\/ /' >/dev/ttyS0 || true
      if [[ ! -s "$verify_file" ]]; then
        echo "C4B_ID_RPM_VERIFY_DETAIL // NO_STDOUT_OR_STDERR" >/dev/ttyS0
      fi
    fi
    # Full signed-rpmdb verification above must show ONLY timestamp changes
    # on exact allowlisted file paths. Invalid flags, unknown or duplicate
    # paths and unexplained nonzero errors still fail closed. This is not
    # permission to suppress payload digest, owner, mode or path checks.
    helper=/usr/local/libexec/postapollo-id-ci-verify-rpm.py
    [[ -f "$helper" && ! -L "$helper" && "$(stat -c '%u:%g:%a' "$helper")" == '0:0:444' ]] ||
      fail "GUEST_RPM_VERIFIER_HELPER_MISSING_OR_MODIFIED_MODE"
    python3 -I -B "$helper" "$verify_file" "$verify_rc" ||
      fail "SIGNED_IDENTITY_BOOTED_RPM_VERIFY_REFUSED"
    # Secondary RPM verifier must return strictly clean when mtime-only
    # comparison is excluded; never override a rejection above.
    nomtime_file=/var/tmp/id-ci-booted-rpm-nomtime.log
    nomtime_rc=0
    timeout --signal=TERM --kill-after=3s 35s rpm -V --nomtime "$pkg" >"$nomtime_file" 2>&1 ||
      nomtime_rc="$?"
    if [[ "$nomtime_rc" != 0 || -s "$nomtime_file" ]]; then
      echo "C4B_ID_RPM_NOMTIME_RC // $nomtime_rc" >/dev/ttyS0
      sed -n '1,24p' "$nomtime_file" |
        sed -E 's/^/C4B_ID_RPM_NOMTIME_DETAIL \/\/ /' >/dev/ttyS0 || true
      fail "SIGNED_IDENTITY_BOOTED_RPM_NON_TIMESTAMP_DISCREPANCY"
    fi
    echo "C4B_ID_PASS // SIGNED_INSTALLED_IDENTITY_RPM_FILE_DIGESTS_AND_MODES"
    for name in identity-gateway-ci desktop_command_gateway_v0.py \
      desktop_host_lifecycle_v0.py desktop_context_projection_v0.py \
      desktop_session_host_v0.py native_loopback_callback_v0.py \
      private_context_ipc_v0.py signed_command_receipt_v0.py; do
      path="$prefix/$name"
      [[ -f "$path" && ! -L "$path" ]] ||
        fail "INSTALLED_IDENTITY_MODULE_MISSING"
      observed="$(stat -c '%u:%g:%a:%h' "$path")" ||
        fail "INSTALLED_IDENTITY_MODULE_STAT_REFUSED"
      printf 'C4B_ID_INSTALLED_FILE_OBSERVED // %s %s\n' "$name" "$observed"
      [[ "$observed" =~ ^0:0:555:[1-9][0-9]*$ ]] ||
        fail "INSTALLED_IDENTITY_MODULE_MODE_WRONG"
      [[ "$(rpm -qf --qf '%{NAME}' "$path")" == "$pkg" ]] ||
        fail "INSTALLED_IDENTITY_MODULE_PACKAGE_OWNER_WRONG"
    done
    echo "C4B_ID_PASS // REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT"
    echo rollback_pending > "$stage"
    rpm-ostree rollback --reboot || fail "REAL_IDENTITY_ROLLBACK_COMMAND_FAILED"
    ;;
  rollback_pending)
    if rpm -q "$pkg" >/dev/null 2>&1; then
      fail "IDENTITY_RPM_REMAINS_AFTER_ROLLBACK"
    fi
    [[ ! -e "$prefix/identity-gateway-ci" &&
       ! -e "/usr/lib/systemd/system/$unit" ]] ||
      fail "IDENTITY_EXEC_OR_UNIT_REMAINS_AFTER_ROLLBACK"
    for name in desktop_command_gateway_v0.py desktop_host_lifecycle_v0.py \
      desktop_context_projection_v0.py desktop_session_host_v0.py \
      native_loopback_callback_v0.py private_context_ipc_v0.py \
      signed_command_receipt_v0.py; do
      [[ ! -e "$prefix/$name" ]] ||
        fail "IDENTITY_MODULE_REMAINS_AFTER_ROLLBACK"
    done
    [[ "$(getenforce)" == Enforcing && ! -e "$marker" ]] ||
      fail "POSTROLLBACK_SELINUX_OR_MARKER_FAILED"
    # Remove separately staged test keyring, local RPM and repo modifications.
    for original in "$store"/original-repos/*.repo; do
      [[ -f "$original" ]] || continue
      cp -a "$original" "/etc/yum.repos.d/$(basename "$original")"
    done
    rm -rf -- "$store"
    [[ ! -e "$store" ]] || fail "IDENTITY_TEST_SIGNER_KEYRING_RESIDUE"
    echo complete > "$stage"
    echo "C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED"
    echo "C4B_ID_PASS // TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED"
    systemctl poweroff --no-block || fail "FINAL_POWEROFF_FAILED"
    ;;
  complete)
    echo "C4B_ID_PASS // COMPLETED_REQUIRES_ALREADY_VERIFIED_LOG"
    systemctl poweroff --no-block
    ;;
  *)
    fail "INVALID_STAGE"
    ;;
esac
