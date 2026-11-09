import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    function find(item,name) {
        if(!item) return null;
        if(item.objectName===name) return item;
        const children=item.children || [];
        for(let i=0;i<children.length;i++){
            const hit=find(children[i],name);
            if(hit) return hit;
        }
        return null;
    }
    function fail(why) {
        if(done)return;
        done=true;
        console.error("C39_NATIVE_FAIL // "+why);
        Qt.quit();
    }
    QtObject {
        id: weather
        property real latitude: 38.9
        property real longitude: -76.75
        // The source-only SKY still instantiates read-only legacy bindings.
        // Supply explicit benign values so the isolated test doesn't invent
        // undefined weather/AQI observations.
        property var dailyForecast: []
        property var hourlyForecast: []
        property bool forecastReady: false
        property bool aqiReady: false
        property bool aqiLoading: false
        property int airQualityUtcOffsetMinutes: -300
        property bool ready: false
        property bool loading: false
        property string localObservationDateTime: ""
        property real localObservationAnchorMs: 0
    }
    Window {
        visible: true
        width: 520
        height: 340
        color: "black"
        Weather.StationCosmosModesPane {
            id: focused
            anchors.fill: parent
            subjectRoute: "cosmos/planets-stars/celestial-fix"
            weatherService: weather
            runtimeNowMs: Date.UTC(2026,10,8,21,0)
        }
    }
    Timer {
        interval: 120
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>45) return root.fail("TIMEOUT");
            if(root.phase===0) {
                if(!focused.planetSource || !focused.celnav
                    || !focused.planetSource.configured
                    || !focused.celnav.configured
                    || !/^\d{4}-\d{2}-\d{2}$/.test(focused.civilDate))
                    return root.fail("TWO_EXISTING_USNO_SOURCES_NOT_CONFIGURED");
                focused.planetSource.active=false;
                focused.planetSource.loadedKey=focused.planetSource.currentKey;
                focused.planetSource.rows=[
                    {name:"MARS",date:focused.civilDate,status:"NORMAL",
                        rise:"06:14",riseAzimuth:88,
                        transit:"12:43",transitAltitude:45,transitHemisphere:"S",
                        set:"19:21",setAzimuth:274},
                    {name:"JUPITER",date:focused.civilDate,status:"NORMAL",
                        rise:"05:00",riseAzimuth:93,
                        transit:"11:30",transitAltitude:52,transitHemisphere:"N",
                        set:"18:15",setAzimuth:265}
                ];
                focused.planetSource.ready=true;
                focused.celnav.active=false;
                focused.celnav.snapshot={date:focused.civilDate,time:"16:45",
                    planets:[
                        {name:"MARS",altitude:37.5,azimuth:203.4,direction:"SSW"},
                        {name:"JUPITER",altitude:18.2,azimuth:125.2,direction:"SE"}],
                    stars:[],constellations:[]};
                focused.celnav.ready=true;
                root.phase=1;
                return;
            }
            if(root.phase===1) {
                const shell=focused.instrumentItem;
                const strip=root.find(shell,"cosmos-c39-fixed-sky-now");
                const timeline=root.find(shell,"cosmos-c38-planets-day-events");
                if(focused.modeCount!==2 || !strip || !timeline
                    || !timeline.compactInPlanets || !timeline.sourceReady
                    || strip.recordCount!==2
                    || strip.currentRecord.name!=="MARS"
                    || timeline.rows.length!==5 || timeline.events.length!==6)
                    return root.fail("PLANETS_DAY_EVENTS_AND_SKY_STRIP_NOT_RENDERED");
                // ALL has no selected ring planet; C40 right-arrow starts
                // at Mercury. Explicitly choose Mars to verify Mars → Jupiter.
                focused.planetSelection="MARS";
                strip.stepPlanet(1);
                if(focused.planetSelection!=="JUPITER"
                    || strip.currentRecord.name!=="JUPITER"
                    || timeline.selectedPlanet!=="JUPITER")
                    return root.fail("STRIP_PLANET_SELECTION_NOT_SHARED");
                focused.planetSubmode="ring";
                root.phase=2;
                return;
            }
            if(root.phase===2) {
                const ring=root.find(focused.instrumentItem,"cosmos-c39-embedded-day-ring");
                if(!ring || !ring.compactInPlanets || !ring.sourceReady
                    || ring.selectedPlanet!=="JUPITER" || ring.events.length!==3)
                    return root.fail("DAY_RING_NOT_EMBEDDED");
                if(!root.find(ring,"cosmos-c28-clock-dial-canvas"))
                    return root.fail("CIRCULAR_CLOCK_NOT_PRESERVED");

                // C40 // Reproduce the real bug: USNO current sky reports
                // SATURN alone while the five day-ring planets still exist.
                // Both arrows must work in both directions despite missing
                // observations, and a missing planet must not borrow Saturn's
                // altitude or azimuth.
                const strip=root.find(focused.instrumentItem,"cosmos-c39-fixed-sky-now");
                const previousSnapshot=focused.celnav.snapshot;
                focused.celnav.snapshot={
                    date:focused.civilDate,time:"16:46",
                    planets:[{name:"SATURN",altitude:13.5,
                              azimuth:222,direction:"SW"}],
                    stars:[],constellations:[]
                };
                focused.planetSelection="SATURN";
                if(!strip || strip.recordCount!==1
                    || strip.selectedName!=="SATURN"
                    || !strip.currentRecord)
                    return root.fail("C40_SATURN_ONLY_FIXTURE_FAILED");
                const checks=[
                    [1,"MERCURY",false],
                    [1,"VENUS",false],
                    [1,"MARS",false],
                    [1,"JUPITER",false],
                    [1,"SATURN",true],
                    [-1,"JUPITER",false],
                    [-1,"MARS",false],
                    [-1,"VENUS",false],
                    [-1,"MERCURY",false],
                    [-1,"SATURN",true]
                ];
                for(let i=0;i<checks.length;i++) {
                    const entry=checks[i];
                    strip.stepPlanet(entry[0]);
                    if(focused.planetSelection!==entry[1]
                        || ring.selectedPlanet!==entry[1]
                        || strip.selectedName!==entry[1]
                        || !!strip.currentRecord!==entry[2])
                        return root.fail("C40_ARROW_CYCLE_"+i+"_"+entry[1]);
                    if(!entry[2] && strip.sourceNote!=="NOT IN USNO SAMPLE")
                        return root.fail("C40_MISSING_SOURCE_NOT_DISCLOSED");
                }
                // Restore full synthetic sample and previous source selection
                // for the established C39 replay and 12-field detail checks.
                focused.celnav.snapshot=previousSnapshot;
                focused.planetSelection="JUPITER";
                ring.startReplay();
                if(!ring.replayMode || ring.replayPlaying)
                    return root.fail("CIRCULAR_REPLAY_BROKEN");
                ring.seekPreview(720);
                if(ring.displayMinute!==720)
                    return root.fail("DAY_RING_SCRUB_BROKEN");
                ring.returnLive();
                focused.skyDetailsIndex=1;
                focused.skyDetailsExpanded=true;
                root.phase=3;
                return;
            }
            if(root.phase===3) {
                const details=root.find(focused.instrumentItem,"cosmos-c6-record-detail");
                if(!details) return; // asynchronous nested Loader
                if(details.recordCount!==2 || details.selectedIndex!==1
                    || details.selectedName!=="JUPITER"
                    || details.facts.length!==12
                    || details.facts[0].value!=="18.2°") {
                    console.log("C39_DETAILS_DIAG // count="+details.recordCount
                        +" index="+details.selectedIndex
                        +" name="+details.selectedName
                        +" facts="+details.facts.length
                        +" alt="+(details.facts[0]?details.facts[0].value:"NONE"));
                    return root.fail("TWELVE_FACT_DETAILS_NOT_RECOVERABLE");
                }
                focused.skyDetailsExpanded=false;
                focused.planetSubmode="day";
                root.phase=4;
                return;
            }
            if(root.phase===4) {
                const shell=focused.instrumentItem;
                const strip=root.find(shell,"cosmos-c39-fixed-sky-now");
                const timeline=root.find(shell,"cosmos-c38-planets-day-events");
                if(!timeline || !strip || !strip.visible
                    || timeline.selectedPlanet!=="JUPITER")
                    return root.fail("RETURN_TO_PLANETS_LOST_SELECTION");
                root.done=true;
                console.log("C39_NATIVE_PASS // TWO_MODES_EMBEDDED_RING_FIXED_SKY_STRIP_FULL_DETAILS");
                Qt.quit();
            }
        }
    }
}
