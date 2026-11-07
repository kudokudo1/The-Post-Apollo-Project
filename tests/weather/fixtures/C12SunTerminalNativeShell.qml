import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// C12 // Disposable offscreen composite terminal, synthetic memory data only.
// Does not contact NOAA, JPL, user location or the running desktop.
ShellRoot {
    id: fixture
    property int tick: 0
    property int phase: 0
    property bool finished: false

    QtObject {
        id: mockLocation
        property real latitude: 38.9
        property real longitude: -77.0
    }
    QtObject {
        id: mockSolar
        property string solarFluxText: "111 SFU"
    }
    QtObject {
        id: sky
        property var astronomySummary: ({
            available:true,sunrise:"06:45",sunset:"17:02",
            daylightLabel:"10H 17M",date:"2026-11-06"
        })
        property var twilightSummary: ({
            available:true,astronomicalDawn:"05:16",civilDawn:"06:19",
            solarNoon:"11:53",civilDusk:"17:28",
            blueMorningStart:"06:02",blueMorningEnd:"06:21",
            goldenMorningStart:"06:21",goldenMorningEnd:"07:10",
            goldenEveningStart:"16:24",goldenEveningEnd:"17:10",
            blueEveningStart:"17:10",blueEveningEnd:"17:38"
        })
        property var currentSolarPosition: ({
            available:true,altitudeDegrees:22.1,azimuthDegrees:190.4
        })
        property int focusedLocalMinute: 720
        property string focusedCivilDate: "2026-11-06"
        property int moonCivilOffsetMinutes: -300
        property string moonCivilOffsetSource: "OPEN-METEO"
    }

    QtObject {
        id: noaa
        property var xrayObservation: ({
            ready:true, loading:false, sampleFresh:true,
            classEquivalent:{label:"C1.2"},fluxLong:0.0000012,
            fluxShort:0.0000000023,satellite:"GOES-18",sampleUtc:"2026-11-06 12:00 UTC",
            trend:[
                {level:0.20,classLetter:"B"},{level:0.26,classLetter:"B"},
                {level:0.38,classLetter:"C"},{level:0.33,classLetter:"C"},
                {level:0.52,classLetter:"C"},{level:0.46,classLetter:"C"},
                {level:0.44,classLetter:"C"},{level:0.61,classLetter:"C"},
                {level:0.43,classLetter:"C"},{level:0.51,classLetter:"C"},
                {level:0.47,classLetter:"C"},{level:0.38,classLetter:"C"}
            ],
            refresh:function(){}
        })
        property var flareObservation: ({
            ready:true,loading:false,count24h:2,cPlus24h:2,
            latest:{classLabel:"C4.6"},
            events:[
                {classLabel:"C4.6",satellite:"GOES-18",
                 beginUtc:"11:00 UTC",peakUtc:"11:05 UTC",endUtc:"11:12 UTC",
                 flux:0.0000046,ended:true},
                {classLabel:"C2.1",satellite:"GOES-18",
                 beginUtc:"10:00 UTC",peakUtc:"10:02 UTC",endUtc:"10:06 UTC",
                 flux:0.0000021,ended:true}
            ],
            refresh:function(){}
        })
        property var cycleObservation: ({
            ready:true,loading:false,summary:{
                modelMonth:"2026-11",targetMonth:"2026-12",
                predictedSsn:83.2,predictedFlux:123.0,
                lowSsn:67.9,highSsn:92.7,
                lowFlux:112.0,highFlux:138.0,
                ssnRangeValid:true,fluxRangeValid:true,
                exactMonth:true,rowCount:50,nextMonth:"2026-12",
                nextPredictedSsn:80.2,peakPredictedSsn:185.0,
                peakMonth:"2024-11"
            },
            refresh:function(){}
        })
        property string solarImageMode: "195"
        property string solarImageUrl: ""
        property string solarImageError: ""
        property real solarImageLastLoadedMs: 0
        property var solarImageInfo: ({
            title:"SUVI // 195 Å", detail:"NOAA IMAGE FIXTURE // NOT FETCHED",
            shortLabel:"195 Å"
        })
        function selectSolarImageMode(next) { solarImageMode=next; }
        function refreshSolarImage() {}
    }

    Window {
        visible: true
        width: 1380
        height: 286
        color: "black"
        Row {
            anchors.fill: parent
            spacing: 6
            Weather.StationCosmosSunTerminalPane {
                id: live
                width: 450
                height: 254
                terminalMode: "live"
                sourceSpace: noaa
                spaceService: mockSolar
            }
            Weather.StationCosmosSunTerminalPane {
                id: position
                width: 450
                height: 254
                terminalMode: "position"
                skyFeed: sky
                weatherService: mockLocation
            }
            Weather.StationCosmosSunTerminalPane {
                id: activity
                width: 450
                height: 254
                terminalMode: "activity"
                sourceSpace: noaa
                spaceService: mockSolar
            }
        }
    }

    function locate(item,name) {
        if(!item) return null;
        if(item.objectName===name) return item;
        const children=item.children||[];
        for(let i=0;i<children.length;i++){
            const match=locate(children[i],name);
            if(match) return match;
        }
        return null;
    }
    function stop(error){
        if(finished) return;
        finished=true;
        console.error("C12_SUN_FAIL // "+error);
        Qt.quit();
    }
    Timer {
        interval: 130
        repeat: true
        running: !fixture.finished
        onTriggered: {
            fixture.tick++;
            if(fixture.tick>38) return fixture.stop("TIMEOUT");
            const hero=fixture.locate(live,"cosmos-c12-suvi-hero");
            const side=fixture.locate(live,"cosmos-c12-live-telemetry");
            const sun=fixture.locate(position,"cosmos-c12-sun-path-hero");
            const ledger=fixture.locate(position,"cosmos-c12-light-ledger");
            const strip=fixture.locate(position,"cosmos-c12-position-live-strip");
            const metrics=fixture.locate(activity,"cosmos-c12-activity-metrics");
            const tabs=fixture.locate(activity,"cosmos-c12-activity-inner-modes");
            if(!hero||!side||!sun||!ledger||!strip||!metrics||!tabs)return;
            if(fixture.phase===0){
                if(position.positionRows.length!==8||position.positionStrip.length!==5)
                    return fixture.stop("POSITION_DATA_MISSING");
                if(sun.width<220 || ledger.width<120 || strip.height<25
                    || hero.width<230 || side.width<120
                    || metrics.height!==61 || tabs.height!==24)
                    return fixture.stop("TERMINAL_GEOMETRY_TOO_SMALL");
                if(hero.height>live.height+1||sun.height>position.height+1
                    || strip.y+strip.height>position.height+1)
                    return fixture.stop("TERMINAL_VIEWPORT_OVERFLOW");
                if(activity.flareCount!==2
                    || activity.xray.classEquivalent.label!=="C1.2"
                    || activity.cycle.summary.predictedSsn!==83.2)
                    return fixture.stop("SOURCE_PRESENTATION_NOT_BOUND");
                const x=fixture.locate(activity,"cosmos-c12-xray-trend");
                if(!x) return fixture.stop("X_RAY_HISTORY_NOT_PRESENT");
                activity.xraySourcePage=true;
                fixture.phase=1;
            }else if(fixture.phase===1){
                const x=fixture.locate(activity,"cosmos-c12-xray-facts");
                if(!x||!activity.xraySourcePage
                    ||activity.xrayFields.length!==4)
                    return fixture.stop("X_RAY_SOURCE_INSPECTOR_MISSING");
                activity.activityFocus=1;
                fixture.phase=2;
            }else if(fixture.phase===2){
                const f=fixture.locate(activity,"cosmos-c12-flare-facts");
                if(!f) return;
                if(activity.flareFields.length!==4)
                    return fixture.stop("FLARE_EVENT_FIELDS_MISSING");
                activity.selectedFlareIndex=1;
                activity.flareDetailPage=1;
                fixture.phase=3;
            }else if(fixture.phase===3){
                if(activity.selectedFlare.classLabel!=="C2.1"
                    ||activity.flareFields.length!==4)
                    return fixture.stop("FLARE_NAVIGATION_BROKEN");
                activity.activityFocus=2;
                activity.cycleDetailPage=2;
                fixture.phase=4;
            }else if(fixture.phase===4){
                const c=fixture.locate(activity,"cosmos-c12-cycle-facts");
                if(!c) return;
                if(activity.cycleFields.length!==4
                    ||activity.cycleFields[2].value!=="185.0")
                    return fixture.stop("CYCLE_OUTLOOK_FIELDS_MISSING");
                activity.cycleDetailPage=1;
                fixture.phase=5;
            }else if(fixture.phase===5){
                if(activity.cycleFields.length!==4
                    ||activity.cycleFields[0].value!=="67.9 - 92.7")
                    return fixture.stop("CYCLE_RANGES_FIELDS_MISSING");
                if(noaa.solarImageUrl!=="")
                    return fixture.stop("UNEXPECTED_NETWORK_IMAGE");
                fixture.finished=true;
                console.log("C12_SUN_PASS // LIVE POSITION ACTIVITY SOURCES DETAILS ZERO_SCROLL");
                Qt.quit();
            }
        }
    }
}
