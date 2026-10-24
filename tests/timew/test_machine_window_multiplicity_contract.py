#!/usr/bin/env python3
"""M2a source contract: no app launch, no Sway moves, no v1 database rewrite."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
pure = (root / "services/time/MachineWindowMultiplicity.py").read_text()
store = (root / "services/time/MachineCheckpointStore.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
doc = (root / "docs/timew-machine-revive-restore-worker-plan.md").read_text()

for required in (
    "def compare_v1_layout(saved_document, live_projection):",
    "def _live_document(value):",
    "MAX_WINDOWS = 512",
    '"exact_session_match": False',
    '"session_identity_verified": False',
    '"safe_actions": []',
    '"no_launch_or_move_approved": True',
    "layout_counts_match_identity_unverified",
    "layout_differs_identity_unverified",
    "Counter(",
):
    assert required in pure, required
for banned in (
    "def main(", "subprocess", "swaymsg", "os.system", "os.spawn",
    "subprocess.Popen", "webbrowser", "sqlite3", "open(",
    "exec(", "eval(", "os.unlink", "shutil", "urllib", "requests",
    "MachineMoveApproval", "MachineWindowMovePilot",
):
    assert banned not in pure, banned
assert '"app_id", "workspace", "floating"' in store
assert 'choices.add_parser("save")' in store
assert 'choices.add_parser("list")' in store
assert 'choices.add_parser("load")' not in store  # load parser has variable assignment
assert 'load_parser = choices.add_parser("load")' in store
assert "MachineWindowMultiplicity.py" not in qml
for required in ("REVIVE", "RESTORE", "17 Brave", "Kitty",
                 "seven", "M2a", "M2b", "M2h", "AGENTS.md"):
    assert required in doc, required
print("MACHINE M2A: NO LIVE CONTROL / V1 STORAGE UNTOUCHED CONTRACT PASS")
