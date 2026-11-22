#!/usr/bin/env python3
"""H1 Doctor directory UI: native-only staged route with explicit write HOLD.

Source/contract checks only. They do not install, launch or alter Hospital.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/hospital/HospitalDoctorService.qml").read_text()
POLICY = (ROOT / "services/hospital/HospitalDoctorDirectoryExitPolicy.js").read_text()
NATIVE = (ROOT / "services/hospital/native/hospital_room_read_client.py").read_text()
HOST = (ROOT / "widgets/HospitalW.qml").read_text()
NAME = (ROOT / "services/hospital/HospitalDoctorNameService.qml").read_text()

def require(value, content, context):
    assert value in content, f"{context}: missing {value}"

for field in (
    'readonly property string nativeReaderPath:',
    '"/usr/libexec/post-apollo/hospital/hospital-room-read"',
    'readonly property bool protectedDoctorWritesReady: false',
    'property bool listResponseAccepted: false',
    'import "HospitalDoctorDirectoryExitPolicy.js" as DoctorReadPolicy',
    'function refresh()',
    'loaded = false;',
    'listResponseAccepted = false;',
    'doctors = [];',
    'property var activeRead: null',
    'property var activeWatchdog: null',
    'property int readGeneration: 0',
    'readonly property int readTimeoutMs: 12000',
    'readGeneration += 1;',
    'doctorReadFactory.createObject(root, {',
    'doctorWatchdogFactory.createObject(root, {',
    'ownerProcess: process,',
    'requestGeneration: generation',
    'process.exec([nativeReaderPath, "doctor-directory"]);',
    'function isCurrentDoctorRead(process, generation)',
    'function advanceDoctorRead(process, generation, next)',
    'function completeDoctorRead(process, generation, result)',
    'function failDoctorRead(process, generation, reason)',
    'if (!next.complete)',
    'process.pendingRead = null;',
    'activeRead = null;',
    'if (result.accepted)',
    'activeWatchdog = null;',
    'watchdog.stop();',
    'process.running = false;',
    'function timeoutDoctorRead(watchdog, process, generation)',
    'if (!watchdog || activeWatchdog !== watchdog)',
    'onTriggered: root.timeoutDoctorRead(',
    'requestWatchdog, requestWatchdog.ownerProcess,',
    'requestWatchdog.requestGeneration',
    'watchdog.destroy();',
    'process.destroy();',
    'loaded = true;',
    'doctors = result.records;',
    'DoctorReadPolicy.captureStdout(',
    'DoctorReadPolicy.captureStderr(',
    'DoctorReadPolicy.captureExit(',
    'HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER',
    'HOSPITAL DOCTOR WRITE // PROTECTED ROUTE NOT ENABLED',
    'doctorsRefreshed();',
):
    require(field, SERVICE, "Native Doctor list mode")

for forbidden in (
    'function pxArgs(',
    'listProcess.exec(pxArgs(',
    'saveProcess.exec(',
    'id: saveProcess',
    '"doctor-put"',
    '"hospital",',
    '"--json"',
    '$HOME/.local',
    'sqlite3',
    'store-command',
    'root.doctors = doctors;',
    'root.doctors = result.map(',
    'listProcess.pendingRead',
    'doctorReadWatchdog',
    'root.activeRead, root.readGeneration',
):
    assert forbidden not in SERVICE, "LEGACY_DOCTOR_ROUTE_STILL_ACTIVE: " + forbidden

# The pure policy is exercised by test_doctor_directory_exit_policy.js
# together with the ACTUAL QML refresh, accept, fail and retirement methods,
# including old-process callbacks after a new generation starts.
for field in (
    'function begin()',
    'function captureStdout(state, text)',
    'function captureStderr(state, text)',
    'function captureExit(state, code, exitStatus)',
    'if (!next.stdoutSeen || !next.stderrSeen || !next.exitSeen)',
    'next.accepted = next.exitAccepted && !next.error;',
    'next.records = next.accepted ? next.staged : [];',
):
    require(field, POLICY, "Doctor reader event-order policy")

# Doctor writes cannot silently fall back to the unprotected PX program.
save = SERVICE.split("function saveDoctor(", 1)[1].split(
    "function releaseDoctor(", 1
)[0]
assert 'return false;' in save
assert 'lastSavedDoctor = null;' in save
assert 'lastError = "HOSPITAL DOCTOR WRITE // PROTECTED ROUTE NOT ENABLED";' in save
release = SERVICE.split("function releaseDoctor(", 1)[1].split(
    "Process {", 1
)[0]
assert "return saveDoctor(" in release
assert "onDoctorSaved:" not in SERVICE

# The source-owned native client remains exactly read-only and pinned. Its
# hostile socket fixture is executed separately in the same workflow.
for marker in (
    'CLIENT = Path("/usr/libexec/post-apollo/hospital/hospital-room-read")',
    'elif operation == "doctor-directory" and room_id is None:',
    '"operation": "doctor-directory"',
    'MAX_DOCTORS = 250',
    'socket.SO_PEERCRED',
    'CLIENT_EXECUTABLE_NOT_PINNED',
):
    require(marker, NATIVE, "Trusted native reader")

# Host's directory-loaded flag must not interpret failed/empty output as
# a successfully loaded list, and must propagate backend failure to UI.
require("HospitalDoctorService {", HOST, "Hospital host")
require("id: doctorService", HOST, "Hospital host")
require("doctorDirectoryLoaded: doctorService.loaded", HOST, "Host readiness")
require("|| doctorService.lastError", HOST, "Host error")

# Distinct, still-unmigrated Doctor-name writer remains on HOLD for native
# cutover. This test does not claim its authority or activate its source.
assert '"doctor-name-set"' in NAME
assert '.local/share/post-apollo-dev-runtime/bin/px' in NAME
print(
    "HOSPITAL H1 DOCTOR LIST UI // PASS // native-only Doctor reads, "
    "no desktop fallback, failed backend not loaded, Doctor writes HOLD, "
    "NO LIVE INSTALL"
)
