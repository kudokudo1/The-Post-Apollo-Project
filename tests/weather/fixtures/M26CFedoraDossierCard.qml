import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather"
import "widgets/weather/StationDossierPreviewPolicy.js" as DossierPreview
import "widgets/weather/StationDossierCapturePolicy.js" as DossierCapture

// M26-C: production Event Context card and real ActionButton MouseArea.
// A disposable Xvfb runner sends actual native X11 pointer events.
ShellRoot {
    id: root

    property var preview: null
    property bool armed: false
    property bool readyLogged: false
    property int requestCount: 0
    property int savedCount: 0
    property bool complete: false

    WeatherDossierArchiveStore {
        id: archive
    }

    Window {
        id: testWindow
        title: "M26C-DOSSIER-TEST"
        flags: Qt.FramelessWindowHint
        visible: true
        x: 0
        y: 0
        width: 720
        height: 900
        color: "#16051F"

        StationEventContextCard {
            id: card
            x: 10
            y: 10
            width: testWindow.width - 20
            eventContext: ({
                sourceId: "gdacs",
                sourceLabel: "GDACS",
                id: "GDACS-M26C-CLICK",
                title: "M26-C DISPOSABLE UI EVENT",
                typeLabel: "FLOOD",
                coordinates: "38.900, -77.100",
                timeLabel: "SYNTHETIC"
            })
            dossierPreview: root.preview
            dossierCaptureReview: DossierCapture.review(
                root.preview, Date.now()
            )
            dossierSaveAvailable: root.armed
                && dossierCaptureReview
                && dossierCaptureReview.ready === true
                && (archive.storageState === "ready"
                    || archive.storageState === "empty")
            dossierSaveStatus: root.savedCount > 0
                ? "SAVED // 1 DOSSIER"
                : archive.storageState === "saving"
                ? "DOSSIER SAVING" : "NOT SAVED"
            dossierSavedCount: root.savedCount
            archiveAvailable: false
            archiveStatusText: "SOURCE ARCHIVE UNCHANGED"
            onDossierSaveRequested: {
                root.requestCount++;
                console.log("M26C_UI_REQUEST // count=" + root.requestCount);
                const now = Date.now();
                const staged = DossierCapture.stage(
                    card.dossierPreview, now, true
                );
                if (!staged.ok || !archive.capture(staged, now))
                    root.failure("CARD_CAPTURE_REJECTED");
            }
        }
    }

    Connections {
        target: archive
        function onDossierSaved(sourceId, eventId, sequence) {
            if (sourceId !== "gdacs"
                    || eventId !== "GDACS-M26C-CLICK"
                    || sequence !== 1
                    || root.requestCount !== 1
                    || archive.eventCount("gdacs", eventId) !== 1) {
                root.failure("NATIVE_CALLBACK_IDENTITY_MISMATCH");
                return;
            }
            root.savedCount++;
            const sourceButton = root.findAction(card, "ARCHIVE");
            if (!sourceButton || sourceButton.available)
                root.failure("SOURCE_ARCHIVE_ACTIVATED");
            else
                root.success();
        }
    }

    function findAction(item, wanted) {
        if (!item)
            return null;
        if (item.label !== undefined && item.label === wanted)
            return item;
        if (!item.children)
            return null;
        for (let i = 0; i < item.children.length; ++i) {
            const match = findAction(item.children[i], wanted);
            if (match)
                return match;
        }
        return null;
    }

    function failure(reason) {
        if (complete)
            return;
        complete = true;
        console.error("M26C_UI_FAIL // " + reason
            + " // requests=" + requestCount
            + " // saved=" + savedCount
            + " // state=" + archive.storageState);
    }

    function success() {
        if (complete)
            return;
        complete = true;
        console.log("M26C_UI_PASS // ENABLED_POINTER_SAVED");
        console.log("M26C_UI_PASS // SOURCE_ARCHIVE_SEPARATE");
    }

    Component.onCompleted: {
        const now = Date.now();
        preview = DossierPreview.preview({
            sourceId:"gdacs", sourceLabel:"GDACS",
            id:"GDACS-M26C-CLICK", title:"M26-C DISPOSABLE UI EVENT",
            typeLabel:"FLOOD", latitude:38.9,
            longitude:-77.1, timeMs:now - 3600000
        }, [], null, null, null, [], [], now - 1000);
        if (!preview.ok)
            failure("PREVIEW_FAILED");
    }

    Timer {
        interval: 50
        repeat: true
        running: !root.complete
        onTriggered: {
            if (root.readyLogged || archive.storageState !== "empty"
                    || !root.preview || !testWindow.visible)
                return;
            const save = root.findAction(card, "SAVE DOSSIER");
            const source = root.findAction(card, "ARCHIVE");
            if (!save || !source || source.available || save.available
                    || !card.dossierPreviewReady
                    || root.requestCount !== 0) {
                root.failure("INITIAL_DISABLED_CARD_STATE_INVALID");
                return;
            }
            const p = save.mapToItem(null, save.width / 2, save.height / 2);
            root.readyLogged = true;
            console.log("M26C_UI_READY // SAVE x=" + Math.round(p.x)
                + " y=" + Math.round(p.y));
        }
    }

    // Window for an actual disabled pointer click, then separately arm.
    Timer {
        interval: 1600
        repeat: false
        running: root.readyLogged && !root.armed && !root.complete
        onTriggered: {
            if (root.requestCount !== 0) {
                root.failure("DISABLED_BUTTON_REQUESTED_WRITE");
                return;
            }
            root.armed = true;
            const save = root.findAction(card, "SAVE DOSSIER");
            if (!save || !save.available)
                root.failure("ENABLED_BUTTON_NOT_READY");
            else
                console.log("M26C_UI_ARMED // POINTER_CLICK_NOW");
        }
    }

    Timer {
        interval: 20000
        repeat: false
        running: !root.complete
        onTriggered: root.failure("TEST_TIMEOUT")
    }

    Timer {
        interval: 250
        repeat: false
        running: root.complete
        onTriggered: Qt.quit()
    }
}
