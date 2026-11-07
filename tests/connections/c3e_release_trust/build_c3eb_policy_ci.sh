#!/usr/bin/env bash
# C3e-B disposable CI *independent root* simulator. Never production key setup.
set -Eeuo pipefail
[[ "$#" -eq 2 && -v GITHUB_ACTIONS && "$GITHUB_ACTIONS" == true &&
    -d "$1" && -d "$2" ]] || {
  echo "C3EB_REFUSED_NOT_DISPOSABLE_RUNNER"
  exit 2
}
candidate="$(realpath "$1")"
root_dir="$(realpath "$2")"
[[ "$candidate" != "$root_dir" && "$root_dir" != "$candidate/"* ]] || exit 2
for file in c3d-status.rpm c3d-disposable-public.asc c3d-public-fingerprint.txt \
            c3eb-release-manifest.json c3eb-release-manifest.sig; do
  [[ -f "$candidate/$file" && ! -L "$candidate/$file" ]] ||
    { echo "C3EB_REFUSED_MISSING_CANDIDATE_FILE"; exit 2; }
done

# This independent root is generated on the CI runner, NOT by the RPM builder.
# A production root must instead be created/approved out of band.
umask 077
home="$root_dir/isolated-root-private"
mkdir -m 0700 -p "$home"
gpg --homedir "$home" --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key \
  "Post Apollo C3eB Disposable Independent Root <c3eb-root@example.invalid>" \
  ed25519 sign 0 >/dev/null 2>&1
fingerprint="$(gpg --homedir "$home" --batch --with-colons --fingerprint \
    --list-keys | awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" =~ ^[A-Fa-f0-9]{40}$ ]] || exit 2
gpg --homedir "$home" --batch --armor --export "$fingerprint" \
  > "$root_dir/root-public.asc"
printf '%s\n' "$fingerprint" > "$root_dir/root-pin.txt"

python3 - "$candidate" "$root_dir" <<'PY'
import hashlib
import json
import pathlib
import sys
candidate = pathlib.Path(sys.argv[1])
root_dir = pathlib.Path(sys.argv[2])
artifact = candidate / "c3d-status.rpm"
manifest = json.loads((candidate / "c3eb-release-manifest.json").read_text())
data = artifact.read_bytes()
digest = hashlib.sha256(data).hexdigest()
if manifest != {
    "schema": "postapollo.connections.release-manifest.v1",
    "release_id": "postapollo-connections-status",
    "sequence": 1,
    "sha256": digest,
    "size": len(data),
}:
    raise SystemExit("C3EB_REFUSED_MANIFEST_NOT_ACTUAL_RPM")
fpr = (candidate / "c3d-public-fingerprint.txt").read_text().strip()
if len(fpr) != 40 or any(c not in "0123456789ABCDEF" for c in fpr):
    raise SystemExit("C3EB_REFUSED_BAD_RPM_SIGNER")
policy = {
    "schema": "postapollo.connections.release-policy.v1",
    "release_id": "postapollo-connections-status",
    "epoch": 1,
    "min_sequence": 1,
    "signers": [{"fingerprint": fpr, "state": "active"}],
    "approved_artifacts": [{
        "sequence": 1, "sha256": digest, "size": len(data)
    }],
}
(root_dir / "root-policy.json").write_text(
    json.dumps(policy, sort_keys=True, separators=(",", ":")), encoding="utf-8"
)
PY
gpg --homedir "$home" --batch --yes --pinentry-mode loopback --passphrase '' \
    --local-user "$fingerprint" --detach-sign \
    --output "$root_dir/root-policy.sig" "$root_dir/root-policy.json"

# The root's private key, signed policy and pinned root are stored separately
# from all candidate artifacts and never staged inside the Fedora VM.
echo "C3EB_PASS // SEPARATE_EPHEMERAL_ROOT_SIGNED_EXACT_RPM_POLICY"
echo "C3EB_LIMITATION // ROOT_PIN_CREATED_BY_CI_NOT_OPERATOR_ENROLLED"
