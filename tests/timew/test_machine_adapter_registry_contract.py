#!/usr/bin/env python3
"""Universal adapter *declarations* must not create runtime capabilities."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
registry = (root / "services/time/MachineAdapterRegistry.py").read_text()
schema = (root / "services/time/MachineSessionIdentityV2.py").read_text()
store = (root / "services/time/MachineCheckpointStore.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
docs = (root / "docs/timew-machine-m2c-universal-adapters.md").read_text()

for required in (
    "def validate_manifest(manifest):",
    "def build_registry(additional_manifests=()):",
    "def find_declared_adapter(registry, adapter_id, app_id):",
    "def list_schema_capabilities(additional_manifests=()):",
    "MAX_ADAPTERS = 64",
    '"schema_only"',
    '"linux_wayland"',
    '"linux_x11"',
    '"windows"',
    '"macos"',
    '"installed_adapter_count": 0',
    '"live_capture_supported": False',
    '"live_reopen_supported": False',
):
    assert required in registry, required
for required in (
    "from MachineAdapterRegistry import RegistryError, build_registry, find_declared_adapter",
    "def validate_sidecar(document, *, v1_checkpoint=None, adapter_manifests=()):",
    "registry = build_registry(adapter_manifests)",
    "descriptor = find_declared_adapter(registry, adapter, app)",
    'kind not in descriptor["item_kinds"]',
    '"exact_session_match": False',
    '"safe_actions": []',
):
    assert required in schema, required
for banned in (
    "subprocess", "swaymsg", "os.system", "os.spawn", "Popen(",
    "importlib", "__import__(", "exec(", "eval(",
    "sqlite3", "open(", "write(", "urllib", "requests",
    "MachineMoveApproval", "MachineWindowMovePilot",
):
    assert banned not in registry, banned
    assert banned not in schema, banned
assert "MachineAdapterRegistry.py" not in qml
assert "MachineSessionIdentityV2.py" not in qml
assert "SCHEMA_VERSION = 1" in store
assert '_keys(entry, ("app_id", "workspace", "floating"))' in store
for required in ("Brave", "Firefox", "Chrome", "Ghostty", "VS Code",
                 "REVIVE", "RESTORE", "not", "schema-only"):
    assert required.lower() in docs.lower(), required
print("MACHINE M2C: UNIVERSAL DECLARATIONS ONLY / NO LIVE APP ACTION PASS")
