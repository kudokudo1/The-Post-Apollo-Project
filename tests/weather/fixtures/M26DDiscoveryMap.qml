import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather"

// Isolated real StationDiscovery MAP and one synthetic GDACS event.
ShellRoot {
    id: root
    property string step: "boot"
    property bool finished: false
    property int ticks: 0
    readonly property string eventId: "FL:M26D:1"
    WeatherDossierArchiveStore { id: archive }
    FloatingWindow {
        id: win
        title: "M26D-MAP-TEST"
        visible: true
        implicitWidth: 1280
        implicitHeight: 950
        StationDiscovery {
            id: map
            anchors.fill: parent
            domain: "map"
            stationOpen: false
            mapShowGdacs: true
            mapShowEarthquakes: false
            mapShowPlaces: false
            mapShowCountryBorders: false
            dossierArchiveStore: archive
        }
    }
    function find(item, predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        if (!item.children) return null;
        for (let i=0; i<item.children.length; i++) {
            const child = find(item.children[i], predicate);
            if (child) return child;
        }
        return null;
    }
    function marker() {
        return find(map, function(i) {
            return i.modelData !== undefined && i.modelData
                && i.modelData.id === root.eventId
                && i.alertRadius !== undefined;
        });
    }
    function card() {
        return find(map, function(i) {
            return i.eventContext !== undefined
                && i.dossierPreview !== undefined
                && i.dossierSaveAvailable !== undefined;
        });
    }
    function saveButton() {
        return find(card(), function(i) {
            return i.label === "SAVE DOSSIER" && i.available !== undefined;
        });
    }
    function scroll() {
        return find(map, function(i) {
            return i.contentY !== undefined && i.contentHeight !== undefined
                && i.height > 500 && i.contentHeight > i.height;
        });
    }
    function show(item, targetY) {
        const s = scroll();
        if (!s || !item) return false;
        const p = item.mapToItem(map, item.width / 2, item.height / 2);
        s.contentY = Math.max(0, Math.min(s.contentHeight - s.height,
                            s.contentY + p.y - targetY));
        return true;
    }
    function announce(item, name) {
        if (!item) return false;
        const p = item.mapToItem(win.contentItem,
                                 item.width / 2, item.height / 2);
        if (!isFinite(p.x) || !isFinite(p.y) ||
             p.x < 0 || p.y < 0 || p.x >= win.width || p.y >= win.height)
            return false;
        console.log("M26D_" + name + "_READY // x=" +
                    Math.round(p.x) + " y=" + Math.round(p.y));
        return true;
    }
    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("M26D_FAIL // " + reason + " // step=" + step +
                      " // selected=" + map.selectedContextSourceId +
                      " // rows=" + map.mapGdacsRows.length);
    }
    Connections {
        target: archive
        function onDossierSaved(sourceId, eventId, sequence) {
            if (root.step !== "saveClick" || sourceId !== "gdacs" ||
                eventId !== root.eventId || sequence !== 1 ||
                archive.eventCount(sourceId, eventId) !== 1) {
                root.fail("SAVED_IDENTITY_MISMATCH");
                return;
            }
            root.finished = true;
            console.log("M26D_PASS // MAP_SELECTED_AND_DOSSIER_SAVED");
        }
    }
    Component.onCompleted: console.log("M26D_BOOT // REAL_MAP")
    Timer {
        interval: 60
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if (root.ticks === 1 || root.ticks % 40 === 0)
                console.log("M26D_HEARTBEAT // step=" + root.step +
                            " store=" + archive.storageState +
                            " rows=" + map.mapGdacsRows.length);
            if (root.step === "boot") {
                if (archive.storageState !== "empty" ||
                    map.mapGdacsRows.length !== 1) return;
                if (!root.show(root.marker(), 350)) return;
                root.step = "mapPosition";
            } else if (root.step === "mapPosition") {
                if (root.announce(root.marker(), "MAP"))
                    root.step = "mapClick";
            } else if (root.step === "mapClick" &&
                       map.selectedContextSourceId === "gdacs") {
                const chosen = map.selectedEventContext;
                const preview = map.selectedDossierPreview;
                if (!chosen || chosen.id !== root.eventId ||
                    !preview || !preview.ok || !preview.dossier ||
                    preview.dossier.selectedEvent.eventId !== root.eventId ||
                    !map.selectedDossierCaptureReview.ready ||
                    !map.dossierSaveAvailable ||
                    archive.eventCount("gdacs",root.eventId) !== 0 ||
                    !root.saveButton()) {
                    root.fail("MAP_DOSSIER_ADMISSION_INVALID");
                    return;
                }
                if (!root.show(root.saveButton(), 400)) return;
                root.step = "savePosition";
            } else if (root.step === "savePosition") {
                if (root.announce(root.saveButton(), "SAVE"))
                    root.step = "saveClick";
            }
        }
    }
    Timer {
        interval: 19000
        running: !root.finished
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 250
        running: root.finished
        repeat: false
        onTriggered: Qt.quit()
    }
}
