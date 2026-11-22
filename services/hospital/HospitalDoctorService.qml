import QtQuick
import Quickshell
import Quickshell.Io
import "HospitalDoctorDirectoryExitPolicy.js" as DoctorReadPolicy

Scope {
    id: root

    property var doctors: []
    property bool loaded: false
    property bool refreshing: false
    property bool saving: false
    property string lastError: ""
    property string lastRefreshedAt: ""
    property var lastSavedDoctor: null
    property bool listResponseAccepted: false
    // Each refresh owns a fresh Process and its own StdioCollector pair.
    // An old process cannot write the staging state of a newer refresh.
    property var activeRead: null
    property int readGeneration: 0
    readonly property int readTimeoutMs: 12000

    // Source-only H1 cutover candidate. This executable must itself prove
    // installed root-owned identity, policy, protected socket and writer peer.
    // Never fall back to desktop PX if the protected reader is unavailable.
    readonly property string nativeReaderPath:
        "/usr/libexec/post-apollo/hospital/hospital-room-read"
    readonly property bool protectedDoctorWritesReady: false

    signal doctorsRefreshed()
    signal doctorSaved(var doctor)

    function compactPxError(value, context) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const rows = detail.split("\n").map(function(row) {
            return String(row || "").trim();
        }).filter(function(row) {
            return row.length > 0;
        });

        let message =
            rows.length > 0
            ? rows[rows.length - 1]
            : detail;

        if (message.length > 240)
            message = message.slice(0, 237) + "...";

        const prefix = String(context || "").trim();
        return prefix ? prefix + " // " + message : message;
    }

    function normalizeDoctor(record) {
        const row = record || {};

        return {
            id: String(row.id || "").trim(),
            name: String(row.name || row.id || "DOCTOR").trim(),
            role: String(row.role || "DOCTOR").trim(),
            status: String(row.status || "ACTIVE").toUpperCase(),
            createdAt: String(row.createdAt || "").trim(),
            updatedAt: String(row.updatedAt || "").trim()
        };
    }

    function doctorById(value) {
        const id = String(value || "").trim();

        for (let i = 0; i < doctors.length; ++i) {
            const row = doctors[i] || {};
            if (String(row.id || "") === id)
                return row;
        }

        return null;
    }

    function refresh() {
        if (refreshing || activeRead)
            return false;

        refreshing = true;
        loaded = false;
        listResponseAccepted = false;
        doctors = [];
        lastRefreshedAt = "";
        lastError = "";
        readGeneration += 1;
        const generation = readGeneration;

        // Allocating one Process per request is essential: an event from
        // the previous StdioCollector must NEVER be assigned a new request's
        // generation merely because a shared Process was reused.
        let process = null;
        try {
            process = doctorReadFactory.createObject(root, {
                requestGeneration: generation
            });
        } catch (error) {
            process = null;
        }
        if (!process) {
            refreshing = false;
            lastError =
                "HOSPITAL BACKEND NOT READY // DOCTOR READER START FAILED";
            doctorsRefreshed();
            return false;
        }
        activeRead = process;
        doctorReadWatchdog.start();

        // Installed native reader verifies root-owned inode/config/socket
        // and the writer's kernel peer. There is NO desktop PX fallback.
        try {
            process.exec([nativeReaderPath, "doctor-directory"]);
        } catch (error) {
            failDoctorRead(process, generation,
                "HOSPITAL BACKEND NOT READY // DOCTOR READER START FAILED");
            return false;
        }
        return true;
    }

    function saveDoctor(idValue, nameValue, roleValue, statusValue) {
        // Do not reuse legacy desktop Doctor mutations after native read
        // cutover. A separately authorized protected write contract must
        // be implemented and accepted before Doctor changes can be saved.
        saving = false;
        lastSavedDoctor = null;
        lastError = "HOSPITAL DOCTOR WRITE // PROTECTED ROUTE NOT ENABLED";
        return false;
    }

    function releaseDoctor(idValue) {
        const doctor = doctorById(idValue) || {};
        return saveDoctor(
            idValue,
            doctor.name || idValue,
            doctor.role || "DOCTOR",
            "RELEASED"
        );
    }

    // A request is accepted only from its *own* Process object and its
    // monotonically changed generation. This is the trust boundary that
    // guards against callbacks from an earlier refresh arriving late.
    function isCurrentDoctorRead(process, generation) {
        return refreshing && !!process && activeRead === process
            && generation === readGeneration && !!process.pendingRead;
    }

    function completeDoctorRead(process, generation, result) {
        if (!isCurrentDoctorRead(process, generation) || !result)
            return false;

        // Revoke the request BEFORE touching Process.running, destroying
        // anything, or publishing a signal that could synchronously refresh.
        process.pendingRead = null;
        activeRead = null;
        refreshing = false;
        doctorReadWatchdog.stop();
        if (process.running)
            process.running = false; // SIGTERM on a stuck read, no detached child.

        if (result.accepted) {
            listResponseAccepted = true;
            loaded = true;
            lastError = "";
            lastRefreshedAt = new Date().toLocaleString();
            doctors = result.records;
        } else {
            listResponseAccepted = false;
            loaded = false;
            doctors = [];
            lastRefreshedAt = "";
            lastError = result.error ||
                "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER";
        }

        // Destroy the retired Process after its signal handler unwinds. Late
        // handlers remain tied to that retired object, never to activeRead.
        Qt.callLater(function() { process.destroy(); });
        doctorsRefreshed();
        return true;
    }

    function advanceDoctorRead(process, generation, next) {
        if (!isCurrentDoctorRead(process, generation) || !next)
            return;
        process.pendingRead = next;
        if (!next.complete)
            return;
        completeDoctorRead(process, generation, next);
    }

    function failDoctorRead(process, generation, reason) {
        if (!isCurrentDoctorRead(process, generation))
            return false;
        return completeDoctorRead(process, generation, {
            accepted: false,
            records: [],
            error: reason || "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER"
        });
    }

    Timer {
        id: doctorReadWatchdog
        interval: root.readTimeoutMs
        repeat: false
        running: false
        onTriggered: root.failDoctorRead(
            root.activeRead, root.readGeneration,
            "HOSPITAL BACKEND NOT READY // DOCTOR READ TIMED OUT"
        )
    }

    // Every new read gets its own Process/StdioCollector objects. Those
    // callbacks pass the source object and original generation explicitly;
    // no old callback is permitted to mutate a current read or the roster.
    Component {
        id: doctorReadFactory
        Process {
            id: requestProcess
            property int requestGeneration: 0
            property var pendingRead: DoctorReadPolicy.begin()

            stdout: StdioCollector {
                onStreamFinished: {
                    if (!root.isCurrentDoctorRead(
                            requestProcess, requestProcess.requestGeneration))
                        return;
                    root.advanceDoctorRead(
                        requestProcess, requestProcess.requestGeneration,
                        DoctorReadPolicy.captureStdout(
                            requestProcess.pendingRead, this.text)
                    );
                }
            }

            stderr: StdioCollector {
                onStreamFinished: {
                    if (!root.isCurrentDoctorRead(
                            requestProcess, requestProcess.requestGeneration))
                        return;
                    root.advanceDoctorRead(
                        requestProcess, requestProcess.requestGeneration,
                        DoctorReadPolicy.captureStderr(
                            requestProcess.pendingRead, this.text)
                    );
                }
            }

            onExited: function(code, exitStatus) {
                if (!root.isCurrentDoctorRead(
                        requestProcess, requestProcess.requestGeneration))
                    return;
                root.advanceDoctorRead(
                    requestProcess, requestProcess.requestGeneration,
                    DoctorReadPolicy.captureExit(
                        requestProcess.pendingRead, code, exitStatus)
                );
            }
        }
    }

    Component.onCompleted: refresh()
}
