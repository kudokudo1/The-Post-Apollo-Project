#!/usr/bin/env python3
"""Source-level CI-only native capture guard, not a proof of OS sandboxing."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
script = (root / "tests/timew/test_machine_geometry_headless_sway.py").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/timew-machine-m2-headless-geometry.yml").read_text(encoding="utf-8")
model = (root / "services/time/MachineGeometryV2.py").read_text(encoding="utf-8")

for required in (
    'os.environ.get("CI") != "true"',
    'os.environ.get("GITHUB_ACTIONS") != "true"',
    '"WLR_BACKENDS": "headless"',
    '"WLR_HEADLESS_OUTPUTS": "2"',
    '"WLR_RENDERER": "pixman"',
    'tempfile.TemporaryDirectory(',
    'env.pop(key, None)',
    '["swaymsg", "-s", ipc, *argv[1:]]',
    'socket.parent != runtime',
    'project_geometry(',
    'compare_to_v1(',
    '"2 virtual outputs // 2 tiled duplicate-app windows // 1 floating"',
    'stop_group(compositor)',
):
    assert required in script, required

assert "sway foot fonts-dejavu-core" in workflow
assert "GITHUB_ACTIONS" not in model
assert "subprocess" not in model
assert "get_tree" not in model
assert "machine.db" not in script
assert 'Quickshell.shellPath(' not in script
print("MACHINE M2 HEADLESS // PRIVATE SOCKET SOURCE CONTRACT PASS")
