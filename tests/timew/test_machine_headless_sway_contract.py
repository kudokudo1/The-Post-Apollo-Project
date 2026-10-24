#!/usr/bin/env python3
"""M1m ensures the compositor smoke test cannot target a user session."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
test = (root / "tests/timew/test_machine_headless_sway.py").read_text()
workflow = (root / ".github/workflows/timew-machine-headless.yml").read_text()
qml = (root / "widgets/TimeW.qml").read_text()

for required in (
    'os.environ.get("CI") != "true"',
    'os.environ.get("GITHUB_ACTIONS") != "true"',
    'TemporaryDirectory(prefix="machine-m1m-")',
    '"XDG_RUNTIME_DIR": str(runtime)',
    '"WLR_BACKENDS": "headless"',
    '"WLR_HEADLESS_OUTPUTS": "1"',
    '"WLR_RENDERER": "pixman"',
    '"SWAYSOCK", "I3SOCK"',
    '["swaymsg", "-s", ipc, *argv[1:]]',
    '["sway", "--config", str(conf)]',
    '"foot", "--app-id=" + app, "sleep", "90"',
    'journal = MoveJournal(base / "journal" / "move-operations.db")',
    'status"] == "verified_moved"',
    'stop_group(compositor)',
):
    assert required in test, required
for forbidden in (
    "swaymsg exit", "execDetached(", "xdg-open", "systemctl",
    "wmctrl", "xdo ", "i3-msg", "pkill -x sway",
):
    assert forbidden not in test, forbidden
assert test.count("move_command(") == 1
assert "MachineWindowMovePilot.py" not in qml
assert "test_machine_headless_sway.py" not in qml
for required in (
    "runs-on: ubuntu-latest",
    "sway foot fonts-dejavu-core",
    "test_machine_headless_sway_contract.py",
    "test_machine_headless_sway.py",
    "workflow_dispatch:",
):
    assert required in workflow
print("MACHINE M1m: CI-ONLY ISOLATED SWAY IPC CONTRACT PASS")
