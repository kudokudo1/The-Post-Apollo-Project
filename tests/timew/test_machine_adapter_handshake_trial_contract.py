#!/usr/bin/env python3
"""M2d2 static contract for a non-operative, simulation-only policy module."""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / "services/time/MachineAdapterHandshakeTrial.py").read_text()
tree = ast.parse(source)
qml = (root / "widgets/TimeW.qml").read_text()
store = (root / "services/time/MachineCheckpointStore.py").read_text()
doc = (root / "docs/timew-machine-m2d2-handshake-trial.md").read_text()

allowed_imports = {
    "uuid", "__future__", "MachineAdapterRegistry",
}
actual_imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        actual_imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        actual_imports.add((node.module or "").split(".")[0])
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            assert node.func.id not in {
                "eval", "exec", "open", "compile", "__import__", "input",
            }, node.func.id
        if isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {
                "system", "popen", "Popen", "run", "check_call",
                "unlink", "write", "write_text", "connect",
            }, node.func.attr
assert actual_imports <= allowed_imports, actual_imports
for token in (
    "class SyntheticHandshakeSession:",
    "def begin(self, *, nonce, host_observation_id, app_id, adapter_id,",
    "def verify(self, nonce, host_echo, app_echo, *, now_seconds):",
    "probe = self.pending.pop(nonce, None)",
    "self.all_nonces.add(nonce)",
    "self.used_instances.add(identity)",
    '"real_app_identity_verified": False',
    '"real_host_binding_verified": False',
    '"operator_consent_verified": False',
    '"exact_session_match": False',
    '"action_allowed": False',
    '"safe_actions": []',
    "MAX_TTL_SECONDS = 30",
):
    assert token in source, token
assert "MachineAdapterHandshakeTrial.py" not in qml
assert "SCHEMA_VERSION = 1" in store
assert 'load_parser = choices.add_parser("load")' in store
for phrase in ("REVIVE", "RESTORE", "17 Brave", "four Kitty",
               "Firefox", "VS Code", "Ghostty", "simulation",
               "no silent", "operator"):
    assert phrase.lower() in doc.lower(), phrase
print("MACHINE M2D2: PURE SYNTHETIC HANDSHAKE CONTRACT PASS")
