import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property string route: "cosmos/sun/xray"
    QtObject {
        id: fakeXray
        property bool ready: true
        property bool loading: false
        property bool failed: false
        property bool sampleFresh: true
        property real fluxLong: 0.00000231
        property real fluxShort: 0.00000042
        property string satellite: "GOES-19"
        property string sampleUtc: "2026-11-06 05:15Z"
        property var classEquivalent: ({letter:"C",label:"C2.3"})
        property var trend: [
            {classLetter:"C",level:0.3},{classLetter:"C",level:0.7}
        ]
        function refresh() { return true; }
    }
    QtObject {
        id: fakeFlare
        property bool ready: true
        property bool loading: false
        property int count24h: 2
        property int cPlus24h: 2
        property var latest: ({classLabel:"M1.2",classLetter:"M",peakUtc:"2026-11-06 05:10Z"})
        property var events: [
            {classLabel:"M1.2",classLetter:"M",
             satellite:"GOES-19",beginUtc:"2026-11-06 05:00Z",
             peakUtc:"2026-11-06 05:10Z",endUtc:"2026-11-06 05:25Z",
             ended:true,flux:0.000012},
            {classLabel:"C4.1",classLetter:"C",
             satellite:"GOES-18",beginUtc:"2026-11-06 02:10Z",
             peakUtc:"2026-11-06 02:22Z",endUtc:"2026-11-06 02:40Z",
             ended:true,flux:0.0000041}
        ]
        function refresh() { return true; }
    }
    QtObject {
        id: fakeCycle
        property bool ready: true
        property bool loading: false
        property var summary: ({
           targetMonth:"2026-11",modelMonth:"2026-11",exactMonth:true,
           predictedSsn:82.5,lowSsn:75.0,highSsn:90.0,ssnRangeValid:true,
           predictedFlux:121.1,lowFlux:115.0,highFlux:131.0,fluxRangeValid:true,
           rowCount:108,peakMonth:"2025-03",peakPredictedSsn:163.1,
           nextMonth:"2026-12",nextPredictedSsn:81.7
        })
        function refresh(force) { return true; }
    }
    QtObject {
        id: fakeSpace
        property var xrayObservation: fakeXray
        property var flareObservation: fakeFlare
        property var cycleObservation: fakeCycle
        property string solarImageMode: "195"
        property string solarImageUrl: ""
        property string solarImageError: ""
        property real solarImageLastLoadedMs: 0
        property var solarImageInfo: ({
            title:"SUVI // 195 Å",detail:"NOAA SWPC SUVI SOURCE",shortLabel:"195 Å"
        })
    }
    QtObject {
        id: fakeMainSpace
        property string solarFluxText: "123 SFU"
    }
    Window {
        visible: true
        width: 520
        height: 340
        color: "black"
        Weather.StationCosmosSunInstrumentPane {
            id: instrument
            anchors.fill: parent
            modeRoute: root.route
            sourceSpace: fakeSpace
            spaceService: fakeMainSpace
        }
    }
    function named(item,needle) {
        if(!item) return 0;
        var count=item.objectName===needle?1:0;
        const children=item.children||[];
        for(let i=0;i<children.length;i++)
            count+=named(children[i],needle);
        return count;
    }
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("C6_SOLAR_FAIL // "+reason+" // route "+root.route);
        Qt.quit();
    }
    Timer {
        interval: 120
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>35)return root.fail("TIMEOUT");
            if(root.phase===0) {
                if(instrument.xrayFields[0].value.indexOf("0.000002310")<0)
                    return root.fail("XRAY_LONG_BAND_MISSING");
                instrument.xrayPage=1;
                root.phase=1;
            } else if(root.phase===1) {
                if(instrument.xrayFields[0].value!=="2026-11-06 05:15Z"
                     || instrument.xrayFields[3].value!=="RECEIVED"
                     || named(instrument,"cosmos-c6-xray-detail")!==4)
                    return root.fail("XRAY_DIAGNOSTICS_NOT_VISIBLE");
                root.phase=2;
                root.route="cosmos/sun/flares";
            } else if(root.phase===2) {
                if(instrument.flareCount!==2
                    || instrument.flareFields[2].value!=="2026-11-06 05:00Z"
                    || named(instrument,"cosmos-c6-flare-detail")!==4)
                    return root.fail("FLARE_FULL_EVENT_NOT_VISIBLE");
                instrument.flareIndex=1;
                instrument.flareDataPage=1;
                root.phase=3;
            } else if(root.phase===3) {
                if(instrument.flareFields[0].value!=="2026-11-06 02:40Z"
                   || instrument.flareFields[1].value!=="0.000004100")
                    return root.fail("FLARE_END_AND_FLUX_NOT_INSPECTABLE");
                root.phase=4;
                root.route="cosmos/sun/cycle";
            } else if(root.phase===4) {
                if(instrument.cycleFields[1].value!=="82.5"
                        || named(instrument,"cosmos-c6-cycle-detail")!==4)
                    return root.fail("CYCLE_MODEL_MISSING");
                instrument.cyclePage=1;
                root.phase=5;
            } else if(root.phase===5) {
                if(instrument.cycleFields[0].value!=="75.0 - 90.0"
                    || instrument.cycleFields[1].value!=="115.0 - 131.0")
                    return root.fail("CYCLE_PUBLISHED_RANGES_MISSING");
                instrument.cyclePage=2;
                root.phase=6;
            } else if(root.phase===6) {
                if(instrument.cycleFields[0].value!=="2026-12"
                    || instrument.cycleFields[2].value!=="163.1")
                    return root.fail("CYCLE_OUTLOOK_MISSING");
                done=true;
                console.log("C6_SOLAR_PASS // GOES_XRAY_SOURCE FLARE_EVENTS CYCLE_RANGES_OUTLOOK");
                Qt.quit();
            }
        }
    }
}
