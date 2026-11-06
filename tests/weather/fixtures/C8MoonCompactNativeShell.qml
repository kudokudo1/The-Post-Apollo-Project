import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// Synthetic samples only in isolated native CI, never in the production UI.
ShellRoot {
    id: root
    property bool done: false
    property int step: 0
    property int ticks: 0
    QtObject {
        id: fakeWeather
        // Start without coordinates so no network fetcher starts before
        // the fixture deactivates the real USNO source actors.
        property var latitude: ""
        property var longitude: ""
        property var dailyForecast: []
        property int airQualityUtcOffsetMinutes: -300
        property bool ready: false
        property bool loading: false
        property string localObservationDateTime: ""
        property real localObservationAnchorMs: 0
    }
    Window {
        visible: true
        width: 450
        height: 276
        color: "black"
        Weather.StationCosmosMoonCompactPane {
            id: moon
            anchors.fill: parent
            weatherService: fakeWeather
            runtimeNowMs: Date.UTC(2026,10,6,7,55)
        }
    }
    function find(item, name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        const kids=item.children||[];
        for(let i=0;i<kids.length;i++){
            const hit=find(kids[i],name);
            if(hit)return hit;
        }
        return null;
    }
    function count(item,name){
        if(!item)return 0;
        const kids=item.children||[];
        let n=item.objectName===name?1:0;
        for(let i=0;i<kids.length;i++)n+=count(kids[i],name);
        return n;
    }
    function fail(message){
        if(done)return;
        done=true;
        console.error("C8_MOON_FAIL // "+message);
        Qt.quit();
    }
    Timer {
        interval: 150
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>40)return root.fail("TIMEOUT");
            const sky=moon.sourceSkyHost;
            if(root.step===0) {
                if(!sky || !sky.moonObservation || !sky.celestialObservation)
                    return root.fail("ORIGINAL_USNO_SERVICES_NOT_MOUNTED");
                sky.moonObservation.active=false;
                sky.celestialObservation.active=false;
                fakeWeather.latitude=38.9;
                fakeWeather.longitude=-76.7;
                root.step=1;
            } else if(root.step===1) {
                sky.moonObservation.ephemeris={
                    available:true, rise:"03:59 AM",transit:"09:45 AM",
                    set:"03:22 PM",phase:"WANING CRESCENT",
                    illumination:7.0,noRiseSet:false,
                    sourceDate:"2026-11-06"
                };
                sky.moonObservation.ready=true;
                sky.celestialObservation.snapshot={
                    date:"2026-11-06",time:"07:55",
                    moon:{altitude:12.3,azimuth:204.1,direction:"SSW"}
                };
                sky.celestialObservation.ready=true;
                root.step=2;
            } else if(root.step===2) {
                if(!moon.moonReady || moon.renderedFactCount!==9
                    || count(moon,"cosmos-c8-moon-fact")!==9)
                    return root.fail("FIXED_NINE_FACTS_NOT_RENDERED");
                if(moon.facts[0].value!=="03:59 AM"
                    || moon.facts[1].value!=="09:45 AM"
                    || moon.facts[2].value!=="03:22 PM"
                    || moon.facts[3].value!=="ABOVE DISPLAY LIMIT"
                    || moon.facts[4].value!=="12.3°"
                    || moon.facts[5].value!=="204.1° // SSW"
                    || moon.facts[6].value!=="2026-11-06"
                    || moon.facts[7].value!=="-300 M"
                    || moon.facts[8].value!=="OPEN-METEO TIMEZONE")
                    return root.fail("MOON_EVENT_POSITION_PROVENANCE_DATA_LOST");
                const phase=find(moon,"cosmos-c8-moon-phase");
                const rack=find(moon,"cosmos-c8-moon-readings");
                if(!phase||!rack||!phase.compactMode
                    || !phase.showMoon || phase.showSun)
                    return root.fail("MAGICK_COMPACT_PHASE_NOT_REUSED");
                if(rack.y+rack.height>moon.height+1
                   || rack.y<phase.y+phase.height-1
                   || rack.height<70)
                    return root.fail("COMPACT_VIEWPORT_GEOMETRY_OVERFLOW");
                root.step=3;
            } else if(root.step===3) {
                const eph=sky.moonObservation.ephemeris;
                sky.moonObservation.ephemeris={
                    available:true,rise:"--",transit:eph.transit,set:"--",
                    phase:eph.phase,illumination:eph.illumination,
                    noRiseSet:true,sourceDate:eph.sourceDate
                };
                root.step=4;
            } else if(root.step===4) {
                const note=find(moon,"cosmos-c8-moon-source-note");
                if(!note || !note.text.includes("NO RISE OR SET")
                    || moon.facts[0].value!=="--"
                    || moon.facts[2].value!=="--")
                    return root.fail("NO_RISE_SET_CAVEAT_LOST");
                sky.celestialObservation.snapshot={
                    date:"2026-11-06",time:"08:00",moon:null
                };
                root.step=5;
            } else if(root.step===5){
                if(moon.facts[3].value!=="NOT IN USNO LIST"
                   || moon.facts[4].value!=="--"
                   || moon.facts[5].value!=="--")
                    return root.fail("BELOW_DISPLAY_LIMIT_MISREPRESENTED");
                root.done=true;
                console.log("C8_MOON_PASS // NINE_FACTS COMPACT_PHASE NO_SCROLL PROVIDER_LIMITS");
                Qt.quit();
            }
        }
    }
}
