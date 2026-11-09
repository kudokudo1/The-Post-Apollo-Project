#!/usr/bin/env python3
"""Native probe optional-permission and no-capability source contracts."""
import ast
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
folder = root / "integrations/machine/brave-topology"
manifest = json.loads((folder / "manifest.json").read_text())
html = (folder / "popup.html").read_text()
ui = (folder / "native-probe-ui.mjs").read_text()
protocol = (folder / "native-probe-protocol.mjs").read_text()
inventory = (folder / "popup.mjs").read_text()
host = (root / "services/time/MachineBraveNativeProbe.py").read_text()
generator = (root / "services/time/MachineBraveNativeManifest.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()

assert manifest["manifest_version"] == 3
assert manifest["incognito"] == "not_allowed"
assert manifest["permissions"] == []
assert manifest["optional_permissions"] == ["nativeMessaging"]
assert manifest["host_permissions"] == []
assert not any(k in manifest for k in (
    "background", "content_scripts", "externally_connectable",
    "optional_host_permissions", "web_accessible_resources",
))
assert '<script type="module" src="native-probe-ui.mjs"></script>' in html
for marker in ("allow-local", "test-local", "revoke-local", "local-status"):
    assert marker in html
assert 'chrome.permissions.request(permission)' in ui
assert 'chrome.permissions.contains(permission)' in ui
assert 'chrome.permissions.remove(permission)' in ui
assert 'chrome.runtime.sendNativeMessage(' in ui
assert 'chrome.permissions.contains(permission)' in ui.split(
    'chrome.runtime.sendNativeMessage(')[0]
for event in ('run("allow")', 'run("test")', 'run("revoke")'):
    assert event in ui
assert ui.count('.addEventListener("click"') == 3
assert 'setInterval' not in ui and 'setTimeout' not in ui
assert 'localStorage' not in ui and 'sessionStorage' not in ui
assert 'chrome.runtime.sendNativeMessage' not in inventory
assert 'chrome.permissions.request' not in inventory
assert 'inspectOnce();' in inventory
assert 'chrome.windows.getAll' not in ui
assert 'chrome.tabs.' not in ui
assert 'chrome.sessions.' not in ui
assert 'chrome.debugger.' not in ui
assert 'JSON.stringify(' not in ui
assert 'checkProbeResponse(challenge, response)' in ui
assert 'window_identity_verified: false' in protocol
assert 'session_restorable: false' in protocol
assert 'safe_actions: []' in protocol
assert "restore_allowed !== false" in protocol

for code in (host, generator):
    module = ast.parse(code)
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(module) if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".", 1)[0]
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imports.intersection({
        "subprocess", "socket", "urllib", "requests", "shutil",
        "sqlite3", "MachineSwayRead", "MachineGeometryV2",
        "MachineCheckpointStore",
    }), imports
for forbidden in (
    "MachineSwayRead", "swaymsg", "MachineGeometry", "MachineCheckpoint",
    "subprocess.run(", "socket.connect(", "urllib.request.",
    "requests.get(", "shutil.copy",
    "os.system", "os.environ", "open(", "write_text", "write_bytes",
    "sqlite3", "exec(", "eval(", "pickle", "pathlib.Path.home",
    "chmod(", "mkdir(", "unlink(", "chrome.tabs", "nativeMessagingHost",
):
    assert forbidden not in host, forbidden
assert '"restore_allowed": False' in host
assert '"session_capture_allowed": False' in host
assert '"extension_origin_authenticated": False' in host
assert '"browser_window_identity_verified": False' in host
assert 'MAX_INPUT = 4096' in host
assert 'struct.pack("=I"' in host and 'struct.unpack("=I"' in host
assert 'read_request(in_pipe)' in host
assert 'write_response(out_pipe, reply)' in host
assert 'read_only' in host
assert 'print(' not in host
assert 'def generate(' in generator
assert 'def main(' in generator
assert 'write_text' not in generator and 'open(' not in generator

# The host has no running platform integration or chosen browser ID yet.
assert "MachineBraveNativeProbe" not in qml
assert "MachineBraveNativeProbe" not in legacy
assert "SCHEMA_VERSION = 1" in legacy
assert qml.count("Process {") == 15
properties = re.findall(
    r"^    (?:readonly )?property\s+\w+\s+(\w+)\s*[:=]",
    qml, flags=re.MULTILINE)
assert properties and len(properties) == len(set(properties))
print("MACHINE Brave // optional grant + explicit probe, zero runtime authority PASS")
