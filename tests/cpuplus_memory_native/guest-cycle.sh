#!/usr/bin/bash
# Runs only in the fresh offline Silverblue VM created by the companion harness.
set -Eeuo pipefail
trap 'echo "CPU_MEM_NATIVE_FAIL // guest line=$LINENO"' ERR
[[ $EUID == 0 && -f /run/ostree-booted && -f /etc/postapollo-memory-ci-only ]]
[[ "$(cat /etc/postapollo-memory-ci-only)" == "DISPOSABLE_CPU_MEMORY_NATIVE_V1" ]]
[[ "$(systemd-detect-virt --vm)" =~ ^(kvm|qemu)$ ]]
[[ "$(getenforce)" == Enforcing ]]
helper=/usr/local/libexec/postapollo-memory-ci-helper
(cd /usr/local/libexec && sha256sum -c postapollo-memory-ci-helper.sha256)
base=/var/lib/post-apollo-memory-swap
extra=/var/lib/post-apollo-memory-extension
history=/var/lib/post-apollo-memory-history
[[ ! -e "$base" && ! -e "$extra" && ! -e "$history" ]]
[[ "$(findmnt -n -o FSTYPE -T /var/lib)" == btrfs ]]
mountpoint="$(findmnt -n -o TARGET -T /var/lib)"
[[ "$mountpoint" == / || "$mountpoint" == /var || "$mountpoint" == /var/lib ]]
btrfs filesystem show --raw "$mountpoint" | grep -E 'Total devices[[:space:]]+1([[:space:]]|$)'
echo "CPU_MEM_NATIVE_PASS // SILVERBLUE_BTRFS_ENFORCING_GUEST"
# Record only capacity and priority, never occupied bytes or swap contents.
python3 -I - "$base/swapfile" "$extra/swapfile" <<'PY'
import json,sys
from pathlib import Path
rows = {}
for line in Path("/proc/swaps").read_text().splitlines()[1:]:
    path,kind,size,used,priority=line.split()
    assert path not in sys.argv[1:]
    rows[path]=[kind,int(size),int(priority)]
Path("/run/cpu-memory-fixture-other.json").write_text(json.dumps(rows))
PY
"$helper" status
"$helper" add-authorized 4
"$helper" persist-authorized
"$helper" expand-authorized 8
stat -c '%d:%i:%s' "$base/swapfile" > /run/cpu-memory-fixture-base
stat -c '%d:%i:%s' "$extra/swapfile" > /run/cpu-memory-fixture-extension
verify_state() {
    local active="$1"
    python3 -I - "$active" "$base/swapfile" "$extra/swapfile" <<'PY'
import json,sys
from pathlib import Path
active,base,extra=sys.argv[1:]
rows={}
for line in Path("/proc/swaps").read_text().splitlines()[1:]:
    path,kind,size,used,priority=line.split()
    rows[path]=[kind,int(size),int(priority)]
for path,priority in ((base,10),(extra,9)):
    if path==extra and active=="no":
        assert path not in rows
        continue
    kind,size,actual=rows.pop(path)
    assert kind=="file" and actual==priority and 0<=4*1024**2-size<=1024
assert rows==json.loads(Path("/run/cpu-memory-fixture-other.json").read_text())
PY
    [[ "$(stat -c '%d:%i:%s' "$base/swapfile")" == "$(cat /run/cpu-memory-fixture-base)" ]]
    [[ "$(stat -c '%d:%i:%s' "$extra/swapfile")" == "$(cat /run/cpu-memory-fixture-extension)" ]]
    systemctl is-enabled 'var-lib-post\x2dapollo\x2dmemory\x2dswap-swapfile.swap' | grep -Fx enabled
}
verify_state yes
echo "CPU_MEM_NATIVE_PASS // BASE_PERSISTENCE_AND_EXTENSION_ACTIVE"
for cycle in 1 2; do
    "$helper" reduction-preflight 4 | python3 -I -c 'import json,sys; r=json.load(sys.stdin); assert r["state"]=="READY_ADVISORY",r'
    "$helper" withdraw-authorized 4
    verify_state no
    "$helper" inspect-recovery-authorized | grep -F '"code": "RECORDED_VERIFIED_INACTIVE"'
    "$helper" reactivate-authorized 8
    verify_state yes
    "$helper" inspect-recovery-authorized | grep -F '"code": "REACTIVATION_RECORDED_VERIFIED_ACTIVE"'
    "$helper" archive-cycle-authorized
    verify_state yes
    for record in withdrawal.json withdrawal-result.json reactivation.json reactivation-result.json archive-pending.json; do
        [[ ! -e "$extra/$record" ]]
    done
    python3 -I - "$history" "$cycle" <<'PY'
import hashlib,json,sys
from pathlib import Path
files=list(Path(sys.argv[1]).glob("cycle-*.json"))
assert len(files)==int(sys.argv[2])
for file in files:
    bundle=json.loads(file.read_text())
    assert bundle["state"]=="VERIFIED_ACTIVE_CYCLE" and len(bundle["records"])==4
    digest=hashlib.sha256(json.dumps(bundle["records"],sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")).hexdigest()
    assert bundle["digest"]==digest and file.name=="cycle-"+digest+".json"
    assert bundle["records"][1]["state"]=="VERIFIED" and bundle["records"][3]["state"]=="VERIFIED"
PY
    echo "CPU_MEM_NATIVE_PASS // CYCLE_${cycle}_VERIFIED"
done
echo "CPU_MEM_NATIVE_PASS // TWO_REAL_CYCLES_HISTORY_RETAINED"
# Guest disk is disposable. Do not delete or deactivate the persistent base.
# Shutdown is controlled by the VM host after this marker; never a host reboot.
