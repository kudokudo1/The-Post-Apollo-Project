import QtQuick
import Quickshell
import "./service" as Hospital

// Exact production HospitalDoctorService.qml copied to ./service with only
// its installed reader path replaced by a disposable fake. No Hospital DB.
// A REAL Quickshell instance, not the existing Node method mock, runs this.
ShellRoot {
    id: witness
    property int phase: 0
    property bool failed: false
    property var oldTimer: null
    property var oldProcess: null
    property int oldGeneration: 0

    function check(condition, explanation) {
        if (condition)
            return true;
        failed = true;
        console.error("H1_QS_LIFECYCLE_FAIL // " + explanation);
        Qt.quit();
        return false;
    }

    Hospital.HospitalDoctorService {
        id: directory
        onDoctorsRefreshed: {
            if (witness.failed)
                return;
            if (witness.phase === 0) {
                if (!witness.check(!directory.loaded && directory.doctors.length === 0,
                        "hung reader published unverified Doctor data"))
                    return;
                if (!witness.check(directory.lastError.indexOf("TIMED OUT") >= 0,
                        "first reader did not terminate via watchdog: " + directory.lastError))
                    return;
                if (!witness.check(witness.oldTimer && witness.oldProcess,
                        "failed to capture original Timer and Process identities"))
                    return;
                if (!witness.check(directory.activeRead === null
                        && directory.activeWatchdog === null,
                        "timeout did not retire original identities"))
                    return;
                console.log("H1_QS_LIFECYCLE_TIMEOUT_PASS");
                witness.phase = 1;
                if (!witness.check(directory.refresh(),
                        "immediate retry after watchdog did not start"))
                    return;
                const nextProcess = directory.activeRead;
                const nextTimer = directory.activeWatchdog;
                if (!witness.check(nextProcess && nextTimer
                        && nextProcess !== witness.oldProcess
                        && nextTimer !== witness.oldTimer
                        && directory.readGeneration !== witness.oldGeneration,
                        "new request reused old timer or Process"))
                    return;

                // Emulate a queued Qt timeout by invoking the *real* old
                // Timer's triggered() signal before Qt.callLater destroys it.
                // Its onTriggered handler must reject the stale owner even
                // though a new Process is already active.
                witness.oldTimer.triggered();
                if (!witness.check(directory.activeRead === nextProcess
                        && directory.activeWatchdog === nextTimer
                        && directory.refreshing && !directory.loaded
                        && directory.doctors.length === 0,
                        "old Timer signal cancelled or published new read"))
                    return;
                if (!witness.check(!directory.timeoutDoctorRead(
                        witness.oldTimer, nextProcess, directory.readGeneration),
                        "old Timer borrowed the new request's identity"))
                    return;
                console.log("H1_QS_LIFECYCLE_OLD_TIMER_REFUSED");
            } else if (witness.phase === 1) {
                if (!witness.check(directory.loaded
                        && !directory.refreshing
                        && directory.lastError === ""
                        && directory.doctors.length === 1
                        && directory.doctors[0].id === "fixture-doctor",
                        "retry failed to publish only the new accepted Doctor"))
                    return;
                console.log("H1_QS_LIFECYCLE_RETRY_PASS");
                witness.phase = 2;
                Qt.quit();
            } else {
                witness.check(false, "unexpected additional Doctor refresh event");
            }
        }
    }

    Timer {
        id: captureOriginalIdentity
        interval: 80
        repeat: true
        running: true
        onTriggered: {
            if (witness.phase === 0 && directory.activeRead
                    && directory.activeWatchdog) {
                witness.oldTimer = directory.activeWatchdog;
                witness.oldProcess = directory.activeRead;
                witness.oldGeneration = directory.readGeneration;
                stop();
            }
        }
    }

    Timer {
        id: earlyPublicationCheck
        interval: 500
        repeat: false
        running: true
        onTriggered: {
            if (witness.phase === 0)
                witness.check(!directory.loaded && directory.doctors.length === 0,
                    "stdout closed before process exit yet roster became visible");
        }
    }

    Timer {
        id: boundedTestTimeout
        interval: 28000
        repeat: false
        running: true
        onTriggered: {
            if (witness.phase !== 2)
                witness.check(false, "real Quickshell fixture did not finish in 28 seconds");
        }
    }
}
