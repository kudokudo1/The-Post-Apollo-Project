import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather"

// Test-only real MAP and dossier writer, four provider cases in distinct
// Quickshell processes sharing one disposable data directory.
ShellRoot {
    id: root
    readonly property string sourceId: Quickshell.env("M26E_SOURCE")
    readonly property int ordinal: Number(Quickshell.env("M26E_ORDINAL"))
    readonly property string eventId: "M26E-SHARED"
    property string step: "boot"
    property bool done: false
    property int ticks: 0

    QtObject {
        id: seismic
        property bool active: false
        property bool ready: root.sourceId === "usgs"
        property bool loading: false
        property bool failed: false
        property bool usingPersistentCache: false
        property string errorText: ""
        property date lastUpdated: new Date()
        property var events: ready ? [{
            id: "M26E-SHARED",
            magnitude: 4.2,
            depthKm: 11,
            place: "SYNTHETIC USGS EVENT",
            latitude: 0,
            longitude: 0,
            time: Date.now() - 60000
        }] : []
    }

    WeatherDossierArchiveStore { id: archive }

    FloatingWindow {
        id: win
        title: "M26E-MAP-TEST"
        visible: true
        implicitWidth: 1280
        implicitHeight: 950

        StationDiscovery {
            id: map
            anchors.fill: parent
            domain: "map"
            stationOpen: false
            seismicSource: seismic
            mapShowGdacs: root.sourceId === "gdacs"
            mapShowEarthquakes: root.sourceId === "usgs"
            mapShowPlaces: false
            mapShowCountryBorders: false
            mapShowAdmin1: false
            dossierArchiveStore: archive
            eventArchiveStore: null
        }
    }

    function find(item, predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        if (!item.children) return null;
        for (let i = 0; i < item.children.length; i++) {
            const result = find(item.children[i], predicate);
            if (result) return result;
        }
        return null;
    }
    function marker() {
        return find(map, function(item) {
            return item.modelData !== undefined && item.modelData
                && item.modelData.id === root.eventId
                && item.projected !== undefined;
        });
    }
    function card() {
        return find(map, function(item) {
            return item.eventContext !== undefined
                && item.dossierPreview !== undefined
                && item.dossierSaveAvailable !== undefined;
        });
    }
    function saveButton() {
        return find(card(), function(item) {
            return item.label === "SAVE DOSSIER"
                && item.available !== undefined;
        });
    }
    function scroll() {
        return find(map, function(item) {
            return item.contentY !== undefined
                && item.contentHeight !== undefined
                && item.height > 500
                && item.contentHeight > item.height;
        });
    }
    function show(item, targetY) {
        const s = scroll();
        if (!s || !item) return false;
        const point = item.mapToItem(map, item.width/2, item.height/2);
        s.contentY = Math.max(0, Math.min(s.contentHeight-s.height,
                            s.contentY+point.y-targetY));
        return true;
    }
    function announce(item, action) {
        if (!item) return false;
        const p = item.mapToItem(win.contentItem,
                                 item.width/2, item.height/2);
        if (!isFinite(p.x) || !isFinite(p.y) || p.x < 0 || p.y < 0
            || p.x >= win.width || p.y >= win.height) return false;
        console.log("M26E_" + action + "_READY // source=" + sourceId
                    + " x=" + Math.round(p.x) + " y=" + Math.round(p.y));
        return true;
    }
    function fail(code) {
        if (done) return;
        done = true;
        console.error("M26E_FAIL // " + code + " source=" + sourceId
            + " step=" + step + " store=" + archive.storageState
            + " selected=" + map.selectedContextSourceId);
    }
    Connections {
        target: archive
        function onDossierSaved(sourceId, eventId, sequence) {
            if (root.step !== "saveClick"
                || sourceId !== root.sourceId || eventId !== root.eventId
                || sequence !== root.ordinal
                || archive.document.revision !== root.ordinal
                || archive.document.entries.length !== root.ordinal
                || archive.eventCount(sourceId,eventId) !== 1
                || map.selectedDossierCount !== 1) {
                root.fail("SAVED_PROVENANCE_OR_REVISION_MISMATCH");
                return;
            }
            root.done = true;
            console.log("M26E_PASS // SOURCE=" + root.sourceId
                + " REVISION=" + root.ordinal
                + " EXACT_PROVIDER_EVENT_KEY_PERSISTED");
        }
    }
    Component.onCompleted: {
        if (["gdacs","usgs","eonet","firms"].indexOf(sourceId) < 0
                || ordinal < 1 || ordinal > 4) {
            fail("UNKNOWN_PROVIDER_OR_ORDINAL");
        } else {
            console.log("M26E_BOOT // source=" + sourceId
                + " ordinal=" + ordinal);
        }
    }
    Timer {
        interval: 60
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks === 1 || root.ticks % 45 === 0)
                console.log("M26E_HEARTBEAT // " + root.sourceId
                    + " step=" + root.step
                    + " ready=" + archive.storageState
                    + " rev=" + archive.document.revision);
            if (root.step === "boot") {
                const correctState = ordinal === 1 ? "empty" : "ready";
                if (archive.storageState !== correctState
                    || archive.document.revision !== ordinal-1
                    || !root.marker()) return;
                if (!root.show(root.marker(),350)) return;
                root.step = "positionMarker";
            } else if (root.step === "positionMarker") {
                if (root.announce(root.marker(),"MAP"))
                    root.step = "mapClick";
            } else if (root.step === "mapClick"
                       && map.selectedContextSourceId === root.sourceId) {
                const selected = map.selectedEventContext;
                const candidate = map.selectedDossierPreview;
                if (!selected || selected.id !== root.eventId
                    || !candidate || !candidate.ok || !candidate.dossier
                    || candidate.dossier.selectedEvent.sourceId !== root.sourceId
                    || candidate.dossier.selectedEvent.eventId !== root.eventId
                    || !map.selectedDossierCaptureReview.ready
                    || !map.dossierSaveAvailable
                    || archive.eventCount(root.sourceId,root.eventId) !== 0
                    || archive.document.revision !== root.ordinal-1
                    || !root.saveButton()) {
                    root.fail("MARKER_DOSSIER_ADMISSION_MISMATCH");
                    return;
                }
                if (!root.show(root.saveButton(),400)) return;
                root.step = "positionSave";
            } else if (root.step === "positionSave") {
                if (root.announce(root.saveButton(),"SAVE"))
                    root.step = "saveClick";
            }
        }
    }
    Timer {
        interval: 19000
        running: !root.done
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 250
        running: root.done
        repeat: false
        onTriggered: Qt.quit()
    }
}
