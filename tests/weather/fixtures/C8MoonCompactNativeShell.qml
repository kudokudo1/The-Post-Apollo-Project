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
    property string lastMoonRoute: ""
    QtObject {
        id: fakeWeather
        // Start without coordinates so no network fetcher starts before
        // the fixture deactivates the real USNO source actors.
        property var latitude: ""
        property var longitude: ""
        property var dailyForecast: []
        property bool forecastReady: false
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
            onRouteRequested: function(path) { root.lastMoonRoute=path; }
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
                fakeWeather.localObservationDateTime="2026-11-06T12:00:00";
                fakeWeather.dailyForecast=[
                    {date:"2026-11-06",moonPhase:"waning crescent",
                     moonIllumination:23,sunrise:"6:45 AM",sunset:"5:04 PM"},
                    {date:"2026-11-07",moonPhase:"new moon",
                     moonIllumination:3,sunrise:"6:46 AM",sunset:"5:03 PM"},
                    {date:"2026-11-08",moonPhase:"waxing crescent",
                     moonIllumination:9,sunrise:"6:47 AM",sunset:"5:02 PM"}
                ];
                fakeWeather.forecastReady=true;
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
                const position=find(moon,"cosmos-c9-moon-tall-position");
                const ribbon=find(moon,"cosmos-c9-moon-event-ribbon");
                const provenance=find(moon,"cosmos-c9-moon-free-provenance");
                if(!phase||!rack||!position||!ribbon||!provenance
                    || !phase.compactMode || !phase.showMoon || phase.showSun)
                    return root.fail("MAGICK_PHASE_OR_NEW_HIERARCHY_MISSING");
                const phaseAt=phase.mapToItem(moon,0,0);
                const positionAt=position.mapToItem(moon,0,0);
                const ribbonAt=ribbon.mapToItem(moon,0,0);
                const provenanceAt=provenance.mapToItem(moon,0,0);
                const header=find(moon,"cosmos-c9-moon-free-header");
                const headerAt=header ? header.mapToItem(moon,0,0) : null;
                const rail=find(moon,"cosmos-c18-moon-fullwidth-mode-rail");
                const phaseTab=find(moon,"cosmos-c18-moon-observation-tab");
                const yearTab=find(moon,"cosmos-c11-open-moon-year");
                const forecastStrip=find(moon,"cosmos-c19-moon-forecast-strip");
                const forecastDay=find(moon,"cosmos-c19-forecast-day");
                const railAt=rail ? rail.mapToItem(moon,0,0) : null;
                const inset=moon.contentInset;
                if(inset!==6 || !headerAt
                   || headerAt.x<inset || headerAt.y<inset
                   || headerAt.x+header.width>moon.width-inset+1
                   || phaseAt.x<inset || positionAt.x+position.width>moon.width-inset+1
                   || ribbonAt.x<inset || ribbonAt.x+ribbon.width>moon.width-inset+1
                   || provenanceAt.x<inset
                   || provenanceAt.x+provenance.width>moon.width-inset+1
                   || rack.x<inset || rack.x+rack.width>moon.width-inset+1
                   || rack.y+rack.height>moon.height-inset+1)
                    return root.fail("MOON_C10_STAGE_GUTTER_NOT_PRESERVED");
                // All three MOON modes occupy a single full-width top rail.
                if(!railAt || !phaseTab || !yearTab || !forecastStrip || !forecastDay
                    || railAt.x<inset || railAt.y<headerAt.y+header.height
                    || railAt.x+rail.width>moon.width-inset+1
                    || rail.height!==27
                    || phaseTab.height!==27 || yearTab.height!==27
                    || phaseTab.width<200 || yearTab.width<200
                    || !phaseTab.selected
                    || phaseAt.y<railAt.y+rail.height)
                    return root.fail("MOON_SUN_STYLE_MODE_RAIL_FAILED");
                yearTab.clicked(null);
                if(root.lastMoonRoute!=="cosmos/moon/year")
                    return root.fail("MOON_YEAR_MODE_ROUTE_BROKEN");
                if(!forecastStrip.model.ready
                    || forecastStrip.rows.length!==3
                    || forecastStrip.focusedDay.date!=="2026-11-06"
                    || forecastStrip.focusedDay.illumination!==23
                    || forecastStrip.height<43
                    || forecastStrip.y<phaseAt.y+phase.height
                    || forecastStrip.y+forecastStrip.height>ribbonAt.y)
                    return root.fail("C19_MOON_FORECAST_STRIP_MISSING");
                forecastStrip.selectedDate="2026-11-07";
                if(positionAt.x < phaseAt.x+phase.width-1
                    || Math.abs(positionAt.y-phaseAt.y)>1
                    || ribbonAt.y<phaseAt.y+phase.height-1
                    || ribbon.width<position.width*2
                    || provenanceAt.y<ribbonAt.y+ribbon.height-1
                    || rack.y+rack.height>moon.height+1
                    || rack.height<50)
                    return root.fail("C9_ASYMMETRIC_VIEWPORT_OVERFLOW");
                if(count(position,"cosmos-c8-moon-fact")!==3
                   || count(ribbon,"cosmos-c8-moon-fact")!==3
                   || count(provenance,"cosmos-c8-moon-fact")!==3)
                    return root.fail("C9_FACT_GROUPING_LOST");
                root.step=3;
            } else if(root.step===3) {
                const forecast=find(moon,"cosmos-c19-moon-forecast-strip");
                if(!forecast || !forecast.focusedDay
                    || forecast.focusedDay.date!=="2026-11-07"
                    || forecast.focusedDay.phase!=="NEW"
                    || forecast.focusedDay.illumination!==3)
                    return root.fail("C19_FORECAST_DAY_SELECTION_FAILED");
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
                console.log("C8_MOON_PASS // NINE_FACTS COMPACT_PHASE NO_SCROLL PROVIDER_LIMITS C9_VISUAL_HIERARCHY C10_6PX_STAGE_GUTTER");
                Qt.quit();
            }
        }
    }
}
