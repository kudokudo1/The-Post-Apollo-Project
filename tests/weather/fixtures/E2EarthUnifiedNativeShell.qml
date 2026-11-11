import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// E2 // An isolated layout-only witness. Providers never activate because
// stationOpen is false, and synthetic status rows never claim live observations.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property real pinnedY: -1
    property real controlsY: -1
    property int initialMapCount: -1
    // Start on the original scrolling map route, as the real EARTH overview does.
    property bool pinned: false
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        const children=item.children||[];
        for(let i=0;i<children.length;i++){
            const found=find(children[i],name);
            if(found)return found;
        }
        return null;
    }
    function count(item,name) {
        if(!item)return 0;
        let result=item.objectName===name ? 1 : 0;
        const children=item.children||[];
        for(let i=0;i<children.length;i++) result+=count(children[i],name);
        return result;
    }
    function fail(why) {
        if(done)return;
        done=true;
        console.error("E2_NATIVE_FAIL // "+why);
        Qt.quit();
    }
    Window {
        id: win
        visible: true
        width: 520
        height: 365
        color: "black"
        Loader {
            id: panel
            anchors.fill: parent
            sourceComponent: root.phase < 3 ? mapCase : servicesCase
        }
    }
    Component {
        id: mapCase
        Weather.StationDiscovery {
            id: earthMap
            domain: "map"
            stationOpen: false
            earthMapOnly: true
            earthMapRoute: root.pinned
                ? "earth/maps/events" : "earth/overview"
            earthPinnedMap: root.pinned
        }
    }
    Component {
        id: servicesCase
        Weather.StationEarthServicesPane {
            runtimeRows: [
                {id:"discovery",label:"NASA EONET",mode:"poll",
                 availability:"LIVE",transport:"READY",receivedAgeMinutes:4,
                 observationAgeMinutes:9,cadenceMs:900000,ready:true},
                {id:"gdacs",label:"GDACS",mode:"poll",
                 availability:"OFFLINE",transport:"ERROR",receivedAgeMinutes:-1,
                 observationAgeMinutes:-1,cadenceMs:900000,ready:false}
            ]
            sourceRows: [
                {name:"NASA EONET",state:"RECEIVED"},
                {name:"GDACS",state:"SOURCE WAITING"}
            ]
        }
    }
    Timer {
        interval:120
        repeat:true
        running:!root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>70)return root.fail("TIMEOUT");
            if(!panel.item || panel.status!==Loader.Ready)return;
            if(root.phase===0) {
                const map=panel.item;
                const host=find(map,"earth-e2-pinned-map-host");
                const canvas=find(map,"earth-e2-single-map-plot");
                const scroll=find(map,"earth-e2-event-scroll");
                const filters=find(map,"earth-e2-pinned-filters");
                if(!host || !canvas || !scroll || !filters)return;
                if(!root.pinned) {
                    // The original map gets a Column-assigned y-offset before
                    // selecting the pinned MAP tab. This transition was absent
                    // from E2's original native witness.
                    if(canvas.parent===host || canvas.y<=0)return;
                    root.pinned=true;
                    return;
                }
                if(!canvas.visible
                    || Math.abs(canvas.mapToItem(host,0,0).x)>0.15
                    || Math.abs(canvas.mapToItem(host,0,0).y)>0.15)
                    return root.fail("PINNED_MAP_RETAINED_OLD_SCROLL_OFFSET");
                const controls=find(map,"earth-e3-pinned-map-controls");
                const appearance=find(map,"earth-e3-pinned-appearance");
                const manual=find(map,"earth-e3-pinned-manual");
                const rack=find(map,"earth-e3-legacy-runtime-rack");
                const sources=find(map,"earth-e3-legacy-source-rack");
                const legacyFilter=find(map,"earth-e3-legacy-eonet-filter");
                if(!controls || !appearance || !manual || !rack || !sources
                        || !legacyFilter)
                    return root.fail("E3_CONTROL_DECK_MISSING");
                if(!host.visible || !filters.visible
                    || canvas.parent!==host
                    || !scroll.visible || canvas.height<=100
                    || host.width!==480 || canvas.width!==480
                    || count(map,"earth-e2-single-map-plot")!==1
                    || controls.width!==host.width
                    || !controls.visible || !appearance.visible || !manual.visible
                    || controls.y < host.y+host.height
                    || scroll.y < controls.y+controls.height
                    || rack.visible || sources.visible || legacyFilter.visible)
                    return root.fail("NOT_ONE_PINNED_MAP_WITH_E3_CONTROLS");
                for(const key of ["borders","states","places","quakes","gdacs","reset"])
                    if(!find(map,"earth-e3-map-"+key))
                        return root.fail("E3_MAP_TOOL_MISSING_"+key);
                for(const key of ["mrms","rainviewer","smoke","firms"])
                    if(!find(map,"earth-e3-source-"+key))
                        return root.fail("E3_MANUAL_SOURCE_MISSING_"+key);
                for(const key of ["radar-history","manual-load","manual-clear"])
                    if(!find(map,"earth-e3-"+key))
                        return root.fail("E3_MANUAL_ACTION_MISSING_"+key);
                root.controlsY=controls.mapToItem(map,0,0).y;
                const keys=["all","quakes","eonet","gdacs","firms"];
                const tabWidth=(480-16)/5;
                for(let i=0;i<keys.length;i++) {
                    const tab=find(map,"earth-e2-filter-"+keys[i]);
                    if(!tab || Math.abs(tab.width-tabWidth)>1
                        || !tab.visible)
                        return root.fail("FILTER_NOT_VISIBLE_"+keys[i]);
                }
                root.pinnedY=canvas.mapToItem(map,0,0).y;
                root.initialMapCount=count(map,"earth-e2-single-map-plot");
                scroll.contentY=250;
                map.earthFocusedLayer="quakes";
                root.phase=1;return;
            }
            if(root.phase===1) {
                const map=panel.item;
                const canvas=find(map,"earth-e2-single-map-plot");
                const scroll=find(map,"earth-e2-event-scroll");
                if(!canvas || !scroll)return root.fail("MAP_LOST_AFTER_SCROLL");
                const y=canvas.mapToItem(map,0,0).y;
                const controls=find(map,"earth-e3-pinned-map-controls");
                if(Math.abs(y-root.pinnedY)>0.15
                    || !controls
                    || Math.abs(controls.mapToItem(map,0,0).y-root.controlsY)>0.15
                    || map.earthFocusedLayer!=="quakes"
                    || !scroll.visible
                    || count(map,"earth-e2-single-map-plot")!==1)
                    return root.fail("MAP_OR_E3_TOOLS_SCROLLED_OR_DUPLICATED");
                // The deck switches manual sources while keeping the same map.
                map.pinnedSourceMode="firms";
                if(map.pinnedSourceMode!=="firms"
                    || find(map,"earth-e3-manual-clear").available)
                    return root.fail("E3_FIRMS_MANUAL_GATE_BROKEN");
                map.pinnedSourceMode="mrms";
                map.earthFocusedLayer="firms";
                if(map.earthFocusedLayer!=="firms")
                    return root.fail("FIRE_FILTER_NOT_SELECTABLE");
                map.earthServicesOnly=true;
                root.phase=2;return;
            }
            if(root.phase===2) {
                const map=panel.item;
                const host=find(map,"earth-e2-pinned-map-host");
                const scroll=find(map,"earth-e2-event-scroll");
                const controls=find(map,"earth-e3-pinned-map-controls");
                if(host.visible || scroll.visible || !controls || controls.visible)
                    return root.fail("SERVICE_VIEW_DOES_NOT_HIDE_MAP");
                root.phase=3;return;
            }
            if(root.phase===3) {
                const p=panel.item;
                if(!p || p.objectName!=="earth-e2-services-pane"
                    || p.runtimeRows.length!==2
                    || p.sourceRows.length!==2
                    || p.readyCount!==1
                    || !p.dashboard || !p.dashboard.detailItem)
                    return root.fail("RUNTIME_SOURCE_ROWS_MISSING");
                p.viewMode="sources";
                root.phase=4;return;
            }
            if(root.phase===4) {
                const p=panel.item;
                if(p.viewMode!=="sources"
                    || !p.dashboard || !p.dashboard.headerItem)
                    return root.fail("SOURCE_DIRECTORY_NOT_AVAILABLE");
                p.viewMode="runtime";
                p.selectedSourceId="gdacs";
                root.phase=5;return;
            }
            if(root.phase===5) {
                const p=panel.item;
                if(!p.selectedSource || p.selectedSource.id!=="gdacs")
                    return root.fail("SOURCE_SELECTION_LOST");
                root.done=true;
                console.log("E2_NATIVE_PASS // PINNED_SINGLE_MAP_SCROLL_FILTERS_SERVICES // E3_FIXED_CONTROLS");
                Qt.quit();
            }
        }
    }
}
