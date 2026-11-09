import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// C42 // Real QML layout, synthetic shared SpaceService and no NOAA network.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        const children=item.children || [];
        for(let i=0;i<children.length;i++){
            const result=find(children[i],name);
            if(result)return result;
        }
        return null;
    }
    function fail(why) {
        if(done)return;
        done=true;
        console.error("C42_NATIVE_FAIL // "+why);
        Qt.quit();
    }
    QtObject {
        id: synthetic
        property bool kpReady: true
        property bool kpLoading: false
        property real kp: 3.3
        property string kpLabel: "UNSETTLED"
        property string kpErrorText: ""
        property date kpLastUpdated: new Date(Date.UTC(2026,10,9,8,26))
        property string kpTime: "2026-11-09 08:20:00"
        property bool usingPersistentKpCache: false

        property bool solarWindReady: true
        property bool solarWindLoading: false
        property real solarWindSpeed: 717
        property string solarWindErrorText: ""
        property date solarWindLastUpdated: new Date(Date.UTC(2026,10,9,8,24))
        property string solarWindTime: "2026-11-09 08:20:00"
        property bool usingPersistentSolarWindCache: false

        property bool magneticFieldReady: true
        property bool magneticFieldLoading: false
        property real magneticFieldBt: 5.0
        property real magneticFieldBz: 1.0
        property string magneticFieldErrorText: ""
        property date magneticFieldLastUpdated: new Date(Date.UTC(2026,10,9,8,23))
        property string magneticFieldTime: "2026-11-09 08:20:00"
        property bool usingPersistentMagneticFieldCache: false

        property bool solarFluxReady: true
        property bool solarFluxLoading: false
        property real solarFlux: 128
        property string solarFluxErrorText: ""
        property date solarFluxLastUpdated: new Date(Date.UTC(2026,10,9,8,21))
        property string solarFluxTime: "2026-11-09 08:10:00"
        property bool usingPersistentSolarFluxCache: false
    }
    Window {
        visible: true
        width: 510
        height: 325
        color: "black"
        Weather.StationCosmosSpaceWeatherHubPane {
            id: hub
            anchors.fill: parent
            spaceService: synthetic
            runtimeNowMs: Date.UTC(2026,10,9,8,30)
            activateLiveFeeds: false
        }
    }
    Timer {
        interval: 120
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>42)return root.fail("TIMEOUT");
            const owner=root.find(hub,"cosmos-c42-source-only-space-owner");
            if(!owner)return;
            if(root.phase===0){
                const metrics=root.find(hub,"cosmos-c42-space-metrics");
                const services=root.find(hub,"cosmos-c42-space-services");
                const report=root.find(hub,"cosmos-c42-selected-service-report");
                const rows=root.find(hub,"cosmos-c42-runtime-rows");
                if(!owner.sourceOnly || owner.visible
                   || owner.subjectRoute!=="cosmos/space-weather/full"
                   || hub.runtimeRows.length!==11
                   || hub.runtimeSummary.total!==11
                   || hub.runtimeSummary.ready!==4
                   || !metrics || !metrics.visible
                   || !services || !services.visible
                   || !report || !report.visible || !rows
                   || !(rows.height>0)
                   || !hub.serviceBrief.includes("OBSERVED KP 3.3"))
                    return root.fail("COMBINED_DASHBOARD_NOT_RENDERED");
                hub.selectedServiceId="space-imf";
                if(!hub.serviceBrief.includes("IMF BT 5.0 nT")
                   || !hub.serviceBrief.includes("BZ 1.0 nT"))
                    return root.fail("SOURCE_BRIEF_NOT_LIVE");
                hub.viewMode="services";
                root.phase=1;return;
            }
            if(root.phase===1){
                const metrics=root.find(hub,"cosmos-c42-space-metrics");
                const report=root.find(hub,"cosmos-c42-selected-service-report");
                if(metrics.visible || !report.visible || report.height!==55
                   || !hub.serviceOwnerNote || !hub.runtimeRows[0].label)
                    return root.fail("EXPANDED_SERVICES_NOT_AVAILABLE");
                const reportFor="swpc-alerts";
                hub.selectedServiceId=reportFor;
                if(!hub.serviceBrief.includes("NO CURRENT PROVIDER REPORT"))
                    return root.fail("INACTIVE_PROVIDER_MISLABELED");
                hub.viewMode="directory";
                root.phase=2;return;
            }
            if(root.phase===2){
                const directory=root.find(hub,"cosmos-c42-space-directory");
                const services=root.find(hub,"cosmos-c42-space-services");
                if(!directory || !directory.visible
                   || services.visible || hub.categories.length!==8)
                    return root.fail("ORIGINAL_DIRECTORY_MISSING");
                hub.viewMode="dashboard";
                hub.selectedServiceId="space-wind";
                root.phase=3;return;
            }
            if(root.phase===3){
                if(!hub.serviceBrief.includes("SOLAR WIND 717 KM/S")
                   || hub.runtimeRows.length!==11
                   || !root.find(hub,"cosmos-c42-runtime-rows").visible)
                    return root.fail("RETURN_TO_DASHBOARD_LOST_RUNTIME");
                root.done=true;
                console.log("C42_NATIVE_PASS // FOUR_METRICS_ELEVEN_RUNTIME_ROWS_REPORT_DIRECTORY");
                Qt.quit();
            }
        }
    }
}
