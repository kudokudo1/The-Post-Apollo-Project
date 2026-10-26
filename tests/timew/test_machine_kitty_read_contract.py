#!/usr/bin/env python3
"""No live MACHINE activation; adapter is an explicit, dormant native reader."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
code = (root/"services/time/MachineKittyRead.py").read_text()
tree=ast.parse(code)
qml=(root/"widgets/TimeW.qml").read_text()
store=(root/"services/time/MachineCheckpointStore.py").read_text()
doc=(root/"docs/timew-machine-m2d3-kitty-native-read.md").read_text()
assert "MachineKittyRead.py" not in qml
assert "SCHEMA_VERSION = 1" in store
assert 'load_parser = choices.add_parser("load")' in store
for fragment in (
    "def normalize_kitty_ls(payload):",
    "def read_existing_kitty_inventory(*, target, runtime_directory, opt_in,",
    '["kitten", "@", "--to", endpoint, "ls", "--output-format=json"]',
    'if opt_in != "explicit_read_only_kitty_inventory":',
    '"host_window_binding_verified": False',
    '"checkpoint_session_match": False',
    '"runtime_ids_ephemeral": True',
    '"safe_actions": []',
    '"capture_enabled": False',
    '"restore_enabled": False',
    "stat.S_ISSOCK(leaf.st_mode)",
    "subprocess.run",
):
    assert fragment in code, fragment
for phrase in ("Kitty","REVIVE","RESTORE","seven","private",
               "no live", "GitHub","owner","socket","no silent"):
    assert phrase.lower() in doc.lower(), phrase
# Import time must not query a socket or spawn any command.
assert all(
    not isinstance(child, (ast.Expr, ast.Assign, ast.AnnAssign,
                           ast.If, ast.For, ast.With, ast.Try))
    for child in tree.body if isinstance(child, ast.If)
) is True
assert not any(isinstance(n, ast.FunctionDef) and n.name=="main"
               for n in ast.walk(tree))
assert "if __name__" not in code
for forbidden in ("os.system(", "shell=True", "swaymsg", "sqlite3",
                  "MachineWindowMovePilot", "MachineMoveApproval",
                  "unlink(", "write_text(", "mkdir(", "input("):
    assert forbidden not in code, forbidden
print("MACHINE M2D3: DORMANT NATIVE KITTY INVENTORY NO-ACTIVATION CONTRACT PASS")
