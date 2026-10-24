#!/usr/bin/env python3
"""M1j source contract: manual, ephemeral window resolution with no execution."""
from pathlib import Path
base = Path(__file__).resolve().parents[2]
qml = (base / "widgets/TimeW.qml").read_text(encoding="utf-8")
resolver = (base / "services/time/MachineWindowResolver.py").read_text(encoding="utf-8")
for piece in (
    "function machineResolveLiveWindows()",
    'label: "RESOLVE LIVE"',
    "onLeftClicked: timew.machineResolveLiveWindows()",
    "property bool machineResolverBusy: false",
    "property string machineResolverCheckpointId:",
    "function machineInvalidateResolver()",
    "machineInvalidateResolver();",
    'Quickshell.shellPath("services/time/MachineWindowResolver.py")',
    "id: machineResolverProcess",
    "stdinEnabled: true",
    "timew.machineResolverPayload + String.fromCharCode(10)",
    'data.kind === "machine-live-window-resolution"',
    'data.read_only === true && data.executable === false',
    'timew.machineResolverCheckpointId === timew.machineSavedItem.id',
    'label: "RESTORE PREVIEW"',
    "NO SCREENSHOTS OR RESTORATION ACTIVE",
    'PLAN ONLY // NO ACTIONS OR RESTARTS',
):
    assert piece in qml, piece
for piece in (
    "def resolve(saved_document, outputs, workspaces, tree):",
    "def capture_and_resolve(document, *, runner=None):",
    "def _walk_live(tree):",
    '"requires_fresh_revalidation": True',
    '"executable": False',
    '"read_only": True',
    '"live_con_id": con_id',
    '"AMBIGUOUS APP INSTANCES"',
    '"TARGET WORKSPACE OR MONITOR ABSENT"',
):
    assert piece in resolver, piece
for prohibited in (
    "shell=True", "os.system(", "subprocess.Popen(", "os.unlink(",
    "run_command(", "move container", "kill", "exec_always",
):
    assert prohibited not in resolver, prohibited
assert 'function applySavedCheckpoint(' not in qml
assert 'function machineApplyRecovery(' not in qml
assert qml.count("Process {") == 12
print("TIMEW MACHINE M1J UI CONTRACT: PASS / EPHEMERAL / READ ONLY")
