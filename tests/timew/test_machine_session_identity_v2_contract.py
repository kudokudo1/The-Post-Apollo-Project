#!/usr/bin/env python3
"""M2b source guard: v2 proposal never mutates the v1 store or starts apps."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
schema = (root / "services/time/MachineSessionIdentityV2.py").read_text()
store = (root / "services/time/MachineCheckpointStore.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
doc = (root / "docs/timew-machine-m2b-v2-session-identity-sidecar.md").read_text()

for required in (
    "def validate_sidecar(document, *, v1_checkpoint=None):",
    "def describe_coverage(proposal):",
    'SIDECAR_KIND = "machine-session-identity-sidecar"',
    '"checkpoint_id"',
    '"window_key"',
    '"instance_key"',
    '"namespace_key"',
    '"adapter_item_key"',
    "MAX_WINDOWS = 512",
    "MAX_ITEMS = 4096",
    "MAX_BYTES = 2_000_000",
    "Counter(",
    '"exact_session_match": False',
    '"per_window_identity_verified": False',
    '"safe_actions": []',
):
    assert required in schema, required
for banned in (
    "def main(", "subprocess", "swaymsg", "os.system", "os.spawn",
    "subprocess.Popen", "webbrowser", "sqlite3", "open(", "write(",
    "exec(", "eval(", "os.unlink", "shutil", "urllib", "requests",
    "MachineMoveApproval", "MachineWindowMovePilot",
):
    assert banned not in schema, banned
for expected in (
    'SCHEMA_VERSION = 1',
    '"schema_version", "kind", "preview_only"',
    '_keys(entry, ("app_id", "workspace", "floating"))',
    'load_parser = choices.add_parser("load")',
):
    assert expected in store, expected
assert "MachineSessionIdentityV2.py" not in qml
for required in ("v1 stays authoritative", "seven existing checkpoints",
                 "Brave", "Kitty", "REVIVE", "RESTORE", "M2c", "consent"):
    assert required.lower() in doc.lower(), required
print("MACHINE M2B: V2 PURE PROPOSAL / V1 STORE NOT MODIFIED PASS")
