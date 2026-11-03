import QtQuick
import Quickshell
import "services/weather"
import "widgets/weather"

// M26-F: actual EARTH subject pane, one persistent MAP and dossier store.
// This positive test NEVER claims CLASSIC -> EARTH selection continuity.
ShellRoot {
    id: root
    property string route: "earth/maps/overview"
    property string phase: "boot"
    property bool finished: false
    property int ticks: 0
    property var originalMap: null
    property int saveSignals: 0
    readonly property string eventId: "FL:M26D:1"

    WeatherDossierArchiveStore { id: archive }

    FloatingWindow {
        id: window
        title: "M26F-EARTH-TEST"
        visible: true
        implicitWidth: 1280
        implicitHeight: 950
        StationEarthSubjectPane {
            id: earth
            anchors.fill: parent
            subjectRoute: root.route
            dossierArchiveStore: archive
        }
    }

    function find(item, predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        if (!item.children) return null;
        for (let i=0;i<item.children.length;i++) {
            const found=find(item.children[i],predicate);
            if (found) return found;
        }
        return null;
    }
    function mapItem() {
        return find(earth, function(item) {
            return item.selectedContextSourceId !== undefined
                && item.mapGdacsRows !== undefined
                && item.selectedDossierPreview !== undefined;
        });
    }
    function marker() {
        const map = mapItem();
        return find(map,function(item) {
            return item.modelData !== undefined && item.modelData
                && item.modelData.id === root.eventId
                && item.alertRadius !== undefined;
        });
    }
    function card() {
        return find(mapItem(),function(item) {
            return item.eventContext !== undefined
                && item.dossierSaveAvailable !== undefined
                && item.dossierPreview !== undefined;
        });
    }
    function saveButton() {
        return find(card(),function(item) {
            return item.label === "SAVE DOSSIER"
                && item.available !== undefined;
        });
    }
    function scroll() {
        return find(mapItem(),function(item) {
            return item.contentY !== undefined
                && item.contentHeight !== undefined
                && item.height > 500 && item.contentHeight > item.height;
        });
    }
    function place(item,desiredY) {
        const s=scroll(),map=mapItem();
        if (!s || !item || !map) return false;
        const p=item.mapToItem(map,item.width/2,item.height/2);
        s.contentY=Math.max(0,Math.min(s.contentHeight-s.height,
                            s.contentY+p.y-desiredY));
        return true;
    }
    function announce(item,label) {
        if (!item) return false;
        const p=item.mapToItem(window.contentItem,
                               item.width/2,item.height/2);
        if (!isFinite(p.x)||!isFinite(p.y)||
            p.x<0||p.y<0||p.x>=window.width||p.y>=window.height)
            return false;
        console.log("M26F_"+label+"_READY // x="+Math.round(p.x)
                    +" y="+Math.round(p.y));
        return true;
    }
    function selectedValid(count) {
        const map=mapItem();
        if (!map || map!==originalMap) return false;
        if (map.earthMapRoute!==route || map.selectedContextSourceId!=="gdacs")
            return false;
        const s=map.selectedEventContext,p=map.selectedDossierPreview;
        if (!s||s.id!==eventId||!p||!p.ok||!p.dossier
            ||p.dossier.selectedEvent.sourceId!=="gdacs"
            ||p.dossier.selectedEvent.eventId!==eventId
            ||!map.selectedDossierCaptureReview.ready
            ||!map.dossierSaveAvailable
            ||map.mapZoom!==1.5
            ||archive.eventCount("gdacs",eventId)!==count)
            return false;
        return true;
    }
    function fail(reason) {
        if (finished) return;
        finished=true;
        console.error("M26F_FAIL // "+reason+" phase="+phase
                      +" route="+route+" state="+archive.storageState);
    }
    Connections {
        target: archive
        function onDossierSaved(sourceId,eventId,sequence) {
            root.saveSignals++;
            if (root.phase!=="saveClicked"||root.saveSignals!==1
                ||sourceId!=="gdacs"||eventId!==root.eventId
                ||sequence!==1||archive.document.revision!==1)
                root.fail("SAVE_CALLBACK_MISMATCH");
            else {
                root.route="earth/investigations/archive";
                root.phase="archiveAfterSave";
            }
        }
    }
    Component.onCompleted: console.log("M26F_BOOT // EARTH_PANE")
    Timer {
        interval: 60
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            const map=root.mapItem();
            if (root.ticks===1||root.ticks%50===0)
                console.log("M26F_HEARTBEAT // phase="+root.phase
                   +" route="+root.route
                   +" store="+archive.storageState
                   +" map="+!!map);
            if (root.phase==="boot") {
                if (archive.storageState!=="empty"||!map
                    ||map.mapGdacsRows.length!==1)return;
                if (!root.place(root.marker(),350))return;
                root.phase="markerPosition";
            } else if(root.phase==="markerPosition") {
                if(root.announce(root.marker(),"MAP"))
                    root.phase="markerClicked";
            } else if(root.phase==="markerClicked") {
                if(!map||map.selectedContextSourceId!=="gdacs")return;
                root.originalMap=map;
                map.mapZoom=1.5;
                if(!root.selectedValid(0)) {
                    root.fail("INITIAL_SELECTION_INVALID");
                    return;
                }
                root.route="earth/investigations/context";
                root.phase="contextRoute";
            } else if(root.phase==="contextRoute") {
                if(!root.selectedValid(0)) {
                    root.fail("CONTEXT_ROUTE_SELECTION_LOST");
                    return;
                }
                console.log("M26F_PASS // CONTEXT_ROUTE_PRESERVED_SELECTION");
                root.route="earth/investigations/dossiers";
                root.phase="dossiersRoute";
            } else if(root.phase==="dossiersRoute") {
                if(!root.selectedValid(0)) {
                    root.fail("DOSSIERS_ROUTE_SELECTION_LOST");
                    return;
                }
                console.log("M26F_PASS // DOSSIERS_ROUTE_PRESERVED_PREVIEW");
                root.route="earth/maps/overview";
                root.phase="mapRoute";
            } else if(root.phase==="mapRoute") {
                if(!root.selectedValid(0)) {
                    root.fail("RETURN_TO_MAP_SELECTION_LOST");
                    return;
                }
                console.log("M26F_PASS // EARTH_MAP_RETURN_PRESERVED_VIEW");
                root.route="earth/investigations/dossiers";
                root.phase="positionSave";
            } else if(root.phase==="positionSave") {
                if(!root.selectedValid(0)) {
                    root.fail("PRE_SAVE_SELECTION_LOST");
                    return;
                }
                if(!root.place(root.saveButton(),400))return;
                root.phase="savePosition";
            } else if(root.phase==="savePosition") {
                if(root.announce(root.saveButton(),"SAVE"))
                    root.phase="saveClicked";
            } else if(root.phase==="archiveAfterSave") {
                if(!root.selectedValid(1)||root.saveSignals!==1) {
                    root.fail("ARCHIVE_ROUTE_HISTORY_LOST");
                    return;
                }
                root.finished=true;
                console.log("M26F_PASS // EARTH_ROUTE_SELECTION_AND_HISTORY");
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
