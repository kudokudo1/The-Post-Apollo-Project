#!/usr/bin/env python3
"""Hospital source-owned Room authorization bridge and backend error contract."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "services/hospital/native/hospital_room_request_client.c"
HARNESS = ROOT / "tests/hospital/hospital_native_request_client_test.c"
SERVICE = (ROOT / "services/hospital/HospitalRoomLifecycleService.qml").read_text()
BIN = (ROOT / "services/hospital/HospitalRoomBinService.qml").read_text()
ROOM = (ROOT / "widgets/HospitalRegisteredWorkerView.qml").read_text()
ISSUER = (ROOT / "services/connections/hospital/HospitalNativeIssuerCore.py").read_text()
SERVER = (ROOT / "services/connections/hospital/HospitalNativeIssuerService.py").read_text()
TRASH = (ROOT / "modules/Trash.qml").read_text()

def require(needle, text, label):
    assert needle in text, f"{label}: missing {needle}"

# Guard the *real* C5-H2 schema and READY-first packet order.
for marker in ('REQUEST_SCHEMA = "postapollo.connections.hospital.native-request.v1"',
               'RECEIPT_SCHEMA = "postapollo.hospital.protected-writer-receipt.v1"'):
    require(marker, ISSUER, "native signer counterpart")
for marker in ('socket.SOCK_SEQPACKET', '"status": "READY"',
               '_same_peer(client, peer, policy["clientExecutableSha256"])'):
    require(marker, SERVER, "native issuer handshake")

source = CLIENT.read_text()
for marker in (
    '#define CLIENT_PATH "/usr/libexec/post-apollo/hospital/hospital-room-request"',
    '#define ISSUER_SOCKET "/run/post-apollo/hospital/issuer.sock"',
    'SOCK_SEQPACKET | SOCK_CLOEXEC', 'SO_PEERCRED',
    'stat("/proc/self/exe"', 'installed_client_trusted()',
    'installed_issuer_socket_trusted()', 'READY_FRAME',
    'perform_exchange(sock, argv[1], argv[2]', 'strcmp(argv[1], "TRASH")',
    'strcmp(argv[1], "RESTORE")',
):
    require(marker, source, "native pinned client")
for forbidden in ('getenv(', 'setenv(', 'system(', 'popen(', 'execvp(', 'execve(',
                  '--signed-authorization-file', 'BURN_ALL'):
    assert forbidden not in source, f"native source must not have {forbidden}"

for marker in (
    'readonly property bool permissionReady:',
    'active && nativeClientInstalled',
    'nativeClientPath, action, room',
    'executeProcess.exec([nativeClientPath, action, room]);',
    'payload.status !== "COMMITTED"',
    'payload.schema !== "postapollo.connections.hospital-native-issuer-response.v1"',
    'payload.action !== root.pendingAction',
    'payload.roomId !== root.pendingRoomId',
    'payload.originalPreserved !== true',
    '!Number.isSafeInteger(payload.revision)',
    'payload.burnAllowed !== false',
    'HOSPITAL BACKEND NOT READY',
):
    require(marker, SERVICE, "QML source-only transport")
assert 'room-lifecycle-trash' not in SERVICE
assert 'room-lifecycle-restore' not in SERVICE
assert '"--signed-authorization-file"' not in SERVICE
assert 'review.operatorAuthenticated === true' not in SERVICE

for marker in (
    'ownerApproved: false', 'policyReviewed: false',
    'protectedResource: true', 'retentionHold: true',
    'burnCapable: false',
    'REQUEST NATIVE APPROVAL // TRASH ROOM',
    'root.roomMatches && root.active',
    'roomLifecycle.execute(action);',
    'REQUEST NATIVE APPROVAL // RESTORE ROOM',
    'onTriggered: root.armLifecycleAction("TRASH")',
    'onTriggered: root.armLifecycleAction("RESTORE")',
):
    require(marker, ROOM, "Room deck remains explicitly deny-only")
require('HOSPITAL BACKEND NOT READY // PX ROOM BIN UNAVAILABLE', BIN, "bin not-ready")
require('visible: trashEntry.modelData.entryType !== "hospital"', TRASH, "Hospital never GIO Burn")
require('hospitalRestore.execute("RESTORE", witness)', TRASH, "existing bin Restore request")
assert "room-lifecycle-burn" not in SERVICE + BIN + source

with tempfile.TemporaryDirectory(prefix="hospital-native-client-src-") as tmp:
    production = Path(tmp) / "hospital-room-request"
    suite = Path(tmp) / "hospital-room-client-unit"
    subprocess.run([
        "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-O2", "-o", str(production), str(CLIENT),
    ], check=True, timeout=30)
    subprocess.run([
        "gcc", "-std=c11", "-Wall", "-Wextra", "-O2",
        "-o", str(suite), str(HARNESS),
    ], check=True, timeout=30)
    result = subprocess.run([str(production), "--check"], capture_output=True,
                            text=True, timeout=10)
    assert result.returncode != 0, result
    assert "PINNED_NATIVE_EXECUTABLE_NOT_INSTALLED" in result.stderr
    assert "COMMITTED" not in result.stdout
    result = subprocess.run([str(suite)], capture_output=True,
                            text=True, timeout=10, check=True)
    assert "HOSPITAL C5-H2 NATIVE CLIENT // PASS" in result.stdout

print("HOSPITAL NATIVE REQUEST BRIDGE // PASS // no CLI mutation, no key to QML, not-ready denial, exact room/action receipt")
