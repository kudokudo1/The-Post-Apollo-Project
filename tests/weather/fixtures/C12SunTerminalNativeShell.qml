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
        width: 1840
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
            Weather.StationCosmosSunTerminalPane {
                id: observation
                width: 450
                height: 254
                terminalMode: "observation"
                sourceSpace: noaa
                spaceService: mockSolar
                skyFeed: sky
                weatherService: mockLocation
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
            const obsImage=fixture.locate(observation,"cosmos-c14-suvi-hero");
            const obsArc=fixture.locate(observation,"cosmos-c14-sun-path-hero");
            const obsLive=fixture.locate(observation,"cosmos-c14-live-telemetry");
            const obsSky=fixture.locate(observation,"cosmos-c14-position-live-strip");
            const obsLight=fixture.locate(observation,"cosmos-c14-twilight-ledger");
            const metrics=fixture.locate(activity,"cosmos-c12-activity-metrics");
            const trend=fixture.locate(activity,"cosmos-c12-xray-trend");
            const xray=fixture.locate(activity,"cosmos-c12-xray-facts");
            const flare=fixture.locate(activity,"cosmos-c12-flare-facts");
            const cycle=fixture.locate(activity,"cosmos-c12-cycle-facts");
            const cluster=fixture.locate(activity,"cosmos-c13-simultaneous-instruments");
            const xrayBay=fixture.locate(activity,"cosmos-c13-xray-bay");
            const flareBay=fixture.locate(activity,"cosmos-c13-flare-bay");
            const cycleBay=fixture.locate(activity,"cosmos-c13-cycle-bay");
            if(!hero||!side||!sun||!ledger||!strip||!metrics
                ||!trend||!xray||!flare||!cycle||!cluster
                ||!xrayBay||!flareBay||!cycleBay
                ||!obsImage||!obsArc||!obsLive||!obsSky||!obsLight)return;
            if(fixture.phase===0){
                if(position.positionRows.length!==8||position.positionStrip.length!==5)
                    return fixture.stop("POSITION_DATA_MISSING");
                if(sun.width<220||ledger.width<120||strip.height<25
                    ||hero.width<230||side.width<120
                    ||metrics.height!==52)
                    return fixture.stop("TERMINAL_GEOMETRY_TOO_SMALL");
                if(obsImage.width<200||obsArc.width<200||obsLive.height<20
                    ||obsSky.height<24||obsLight.height<40
                    ||obsLight.y+obsLight.height>observation.height+1
                    ||observation.positionRows.length!==8
                    ||observation.positionStrip.length!==5)
                    return fixture.stop("OBSERVATION_INSTRUMENT_GEOMETRY_INVALID");
                if(hero.height>live.height+1||sun.height>position.height+1
                    ||strip.y+strip.height>position.height+1
                    ||cluster.y+cluster.height>activity.height+1
                    ||cycleBay.y+cycleBay.height>cluster.height+1
                    ||flareBay.y+flareBay.height>cluster.height+1)
                    return fixture.stop("TERMINAL_VIEWPORT_OVERFLOW");
                if(activity.flareCount!==2
                    ||activity.xray.classEquivalent.label!=="C1.2"
                    ||activity.cycle.summary.predictedSsn!==83.2)
                    return fixture.stop("SOURCE_PRESENTATION_NOT_BOUND");
                if(activity.xrayFields.length!==8
                    ||activity.flareFields.length!==8
                    ||activity.cycleFields.length!==12)
                    return fixture.stop("SIMULTANEOUS_FACTS_MISSING");
                if(activity.xrayFields[4].value!=="2026-11-06 12:00 UTC"
                    ||activity.cycleFields[10].value!=="185.0")
                    return fixture.stop("HISTORY_OR_PREDICTION_MISSING");
                activity.selectedFlareIndex=1;
                fixture.phase=1;
            }else if(fixture.phase===1){
                if(activity.selectedFlare.classLabel!=="C2.1"
                    ||activity.flareFields[0].value!=="C2.1"
                    ||activity.flareFields[5].value!=="0.000002100")
                    return fixture.stop("FLARE_EVENT_PAGING_BROKEN");
                if(noaa.solarImageUrl!=="")
                    return fixture.stop("UNEXPECTED_NETWORK_IMAGE");
                fixture.finished=true;
                console.log("C12_SUN_PASS // LIVE POSITION ACTIVITY SOURCES DETAILS ZERO_SCROLL");
                Qt.quit();
            }
        }
    }
}
