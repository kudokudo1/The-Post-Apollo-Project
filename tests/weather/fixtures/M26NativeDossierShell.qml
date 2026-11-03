import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather/StationDossierPreviewPolicy.js" as DossierPreview
import "widgets/weather/StationDossierCapturePolicy.js" as DossierCapture

// M26-B isolated native Quickshell test entrypoint. No PanelWindow, no
// live compositor, no provider network, no production shell import.
ShellRoot {
    id: root

    readonly property string phase: Quickshell.env("M26_NATIVE_PHASE")
    readonly property string expectedId: "GDACS-M26-NATIVE"
    property bool requested: false
    property bool complete: false
    property int ticks: 0

    WeatherDossierArchiveStore {
        id: archive
    }

    function quitWithFailure(code) {
        if (complete)
            return;
        complete = true;
        console.error("M26_NATIVE_FAIL // " + code
            + " // storage=" + archive.storageState
            + " // last=" + archive.lastResultCode);
        // The invoking script treats absence of a PASS marker as failure.
        Qt.quit();
    }

    function quitWithSuccess(marker) {
        if (complete)
            return;
        complete = true;
        console.log("M26_NATIVE_PASS // " + marker);
        Qt.quit();
    }

    function explicitCandidate(now) {
        const selected = {
            sourceId:"gdacs", sourceLabel:"GDACS",
            id:expectedId,
            title:"M26 DISPOSABLE NATIVE TEST",
            typeLabel:"FLOOD",
            latitude:38.9, longitude:-77.1,
            timeMs:now - 3600000
        };
        const preview = DossierPreview.preview(
            selected, [], null, null, null, [], [], now - 1000
        );
        return DossierCapture.stage(preview, now, true);
    }

    Connections {
        target: archive

        function onDossierSaved(sourceId, eventId, sequence) {
            if (root.phase !== "create") {
                root.quitWithFailure("UNEXPECTED_WRITE_AFTER_RESTART");
                return;
            }
            if (sourceId !== "gdacs"
                    || eventId !== root.expectedId || sequence !== 1
                    || archive.storageState !== "ready"
                    || archive.eventCount("gdacs", root.expectedId) !== 1) {
                root.quitWithFailure("SAVE_CALLBACK_MISMATCH");
                return;
            }
            root.quitWithSuccess("CREATE_CALLBACK_SAVED");
        }
    }

    Timer {
        interval: 50
        repeat: true
        running: !root.complete

        onTriggered: {
            root.ticks++;
            if (root.ticks > 300) {
                root.quitWithFailure("TIMEOUT");
                return;
            }

            if (root.phase === "create") {
                if (!root.requested
                        && archive.storageState === "empty") {
                    root.requested = true;
                    const now = Date.now();
                    const staged = root.explicitCandidate(now);
                    if (!staged.ok) {
                        root.quitWithFailure("ADMISSION_REJECTED");
                        return;
                    }
                    if (!archive.capture(staged, now)) {
                        root.quitWithFailure("SAVE_NOT_QUEUED");
                        return;
                    }
                    if (archive.storageState !== "saving") {
                        root.quitWithFailure("MISSING_SAVING_TRANSITION");
                        return;
                    }
                } else if (archive.storageState === "error"
                           || archive.storageState === "unsupported") {
                    root.quitWithFailure("CREATE_STORE_ERROR");
                }
            } else if (root.phase === "reload") {
                if (archive.storageState === "ready") {
                    const last = archive.latest("gdacs", root.expectedId);
                    if (!last || last.eventId !== root.expectedId
                            || last.sequence !== 1
                            || archive.eventCount("gdacs", root.expectedId) !== 1)
                        root.quitWithFailure("RELOAD_CONTENT_MISMATCH");
                    else
                        root.quitWithSuccess("RELOAD_READBACK_VALIDATED");
                } else if (archive.storageState === "empty"
                        || archive.storageState === "error"
                        || archive.storageState === "unsupported") {
                    root.quitWithFailure("RELOAD_NOT_READY");
                }
            } else if (root.phase === "corrupt") {
                if (archive.storageState === "error"
                        || archive.storageState === "unsupported") {
                    const now = Date.now();
                    const staged = root.explicitCandidate(now);
                    if (!staged.ok || archive.capture(staged, now)
                            || archive.pendingDocument !== null)
                        root.quitWithFailure("CORRUPT_FILE_WRITE_GATE_BROKEN");
                    else
                        root.quitWithSuccess("CORRUPT_FILE_WRITE_REFUSED");
                } else if (archive.storageState === "ready"
                           || archive.storageState === "empty") {
                    root.quitWithFailure("CORRUPT_FILE_ACCEPTED");
                }
            } else {
                root.quitWithFailure("UNKNOWN_TEST_PHASE");
            }
        }
    }
}
