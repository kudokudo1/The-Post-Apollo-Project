import QtQuick
import Quickshell
import QtTest
import "services/weather"
import "widgets/weather"
import "widgets/weather/StationDossierPreviewPolicy.js" as DossierPreview
import "widgets/weather/StationDossierCapturePolicy.js" as DossierCapture

// M26-C: actual production EVENT CONTEXT card + ActionButton pointer path
// in an isolated offscreen Qt window; no production shell or provider fetch.
ShellRoot {
    id: root

    property var preview: null
    property bool armed: false
    property int requestCount: 0
    property int savedCount: 0
    property bool complete: false

    WeatherDossierArchiveStore {
        id: archive
    }

    Window {
        id: testWindow
        visible: true
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
                    || sequence !== 1)
                root.failure("NATIVE_CALLBACK_IDENTITY_MISMATCH");
            else
                root.savedCount++;
        }
    }

    function findAction(item, text) {
        if (!item)
            return null;
        if (item.label !== undefined && item.label === text)
            return item;
        if (!item.children)
            return null;
        for (let i = 0; i < item.children.length; ++i) {
            const match = findAction(item.children[i], text);
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
        // Quitting synchronously in a QtTest/TestSchedule signal handler
        // destroys the runner in-flight. A separate timer owns shutdown.
    }

    function success() {
        if (complete)
            return;
        complete = true;
        console.log("M26C_UI_PASS // DISABLED_POINTER_IGNORED");
        console.log("M26C_UI_PASS // ENABLED_POINTER_SAVED");
        console.log("M26C_UI_PASS // SOURCE_ARCHIVE_SEPARATE");
        // A timer quits after QtTest's assertion stack has unwound.
    }

    Timer {
        interval: 250
        repeat: false
        running: root.complete
        onTriggered: Qt.quit()
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
        interval: 18000
        repeat: false
        running: !root.complete
        onTriggered: root.failure("TEST_TIMEOUT")
    }

    TestCase {
        name: "M26CFedoraDossierCard"
        when: !!root.preview
            && archive.storageState === "empty"
            && testWindow.visible

        function test_real_card_pointer_and_save() {
            const save = root.findAction(card, "SAVE DOSSIER");
            const provider = root.findAction(card, "ARCHIVE");
            verify(save !== null, "SAVE DOSSIER ActionButton not found");
            verify(provider !== null, "source-native ARCHIVE button not found");
            compare(provider.available, false,
                "source-native archive action must remain separate");
            compare(save.available, false,
                "unarmed user action must initially be disabled");

            mouseClick(save, save.width / 2, save.height / 2,
                       Qt.LeftButton);
            compare(root.requestCount, 0,
                "disabled pointer must never request a write");

            root.armed = true;
            tryCompare(save, "available", true, 2000);
            mouseClick(save, save.width / 2, save.height / 2,
                       Qt.LeftButton);
            compare(root.requestCount, 1,
                "one native mouse click must request one dossier");
            tryCompare(archive, "storageState", "ready", 6000);
            compare(root.savedCount, 1,
                "native FileView callback must report one save");
            compare(archive.eventCount("gdacs", "GDACS-M26C-CLICK"), 1);
            compare(provider.available, false,
                "dossier capture must not enable source-native archive");
            root.success();
        }
    }
}
