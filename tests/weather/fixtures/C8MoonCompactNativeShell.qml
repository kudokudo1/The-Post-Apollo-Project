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
    property real compactMoonDiskWidth: 0
    property real compactMoonHeroWidth: 0
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
        id: testWindow
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
                     moonIllumination:9,sunrise:"6:47 AM",sunset:"5:02 PM"},
                    {date:"2026-11-09",moonPhase:"waxing crescent",
                     moonIllumination:17,sunrise:"6:48 AM",sunset:"5:01 PM"},
                    {date:"2026-11-10",moonPhase:"waxing crescent",
                     moonIllumination:26,sunrise:"6:49 AM",sunset:"5:00 PM"},
                    {date:"2026-11-11",moonPhase:"first quarter",
                     moonIllumination:49,sunrise:"6:50 AM",sunset:"4:59 PM"},
                    {date:"2026-11-12",moonPhase:"waxing gibbous",
                     moonIllumination:63,sunrise:"6:51 AM",sunset:"4:58 PM"}
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
                const disk=find(phase,"cosmos-c21-moon-hero-disk");
                if(!disk || !phase.prominentMoon
                    || disk.width<100 || phase.width<275)
                    return root.fail("C21_ACTUAL_MOON_DISK_NOT_ENLARGED");
                root.compactMoonDiskWidth=disk.width;
                root.compactMoonHeroWidth=phase.width;
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
                const forecastDay=find(moon,"cosmos-c20-forecast-day-row");
                const verticalForecast=find(moon,"cosmos-c20-moon-vertical-forecast");
                const forecastDaylight=find(moon,"cosmos-c20-forecast-selected-daylight");
                const board=find(moon,"cosmos-c9-moon-hero-row");
                const railAt=rail ? rail.mapToItem(moon,0,0) : null;
                const forecastAt=forecastStrip
                    ? forecastStrip.mapToItem(moon,0,0) : null;
                const inset=moon.contentInset;
                if(inset!==6 || !headerAt || !board || !forecastAt
                    || !verticalForecast || !forecastDaylight
                    || headerAt.x<inset || headerAt.y<inset
                    || headerAt.x+header.width>moon.width-inset+1
                    || railAt===null || railAt.x<inset
                    || railAt.x+rail.width>moon.width-inset+1
                    || phaseAt.x<inset
                    || phaseAt.y<railAt.y+rail.height
                    || phaseAt.x+phase.width>moon.width-inset+1
                    || positionAt.x<inset
                    || provenanceAt.x<inset
                    || forecastAt.x<phaseAt.x+phase.width+2
                    || forecastAt.x+forecastStrip.width>moon.width-inset+1
                    || ribbonAt.x<forecastAt.x
                    || ribbonAt.x+ribbon.width>moon.width-inset+1
                    || rack.y+rack.height>moon.height+1)
                    return root.fail("C20_SPLIT_STAGE_GUTTER_OR_BOUNDS_FAILED");

                // Keep exactly the same Moon two-mode controls and source
                // facts. The phase now gets more screen space than C19.
                if(!phaseTab || !yearTab
                    || rail.height!==27
                    || phaseTab.height!==27 || yearTab.height!==27
                    || phaseTab.width<200 || yearTab.width<200
                    || !phaseTab.selected
                    || phase.height<125
                    || phase.height<=position.height
                    || position.height<20 || position.height>30
                    || provenance.height<20 || provenance.height>30
                    || phase.height<155
                    || provenanceAt.y<positionAt.y+position.height-1
                    || provenanceAt.y+provenance.height>moon.height-inset+1
                    || forecastAt.y<railAt.y+rail.height
                    || forecastStrip.height<120
                    || ribbonAt.y<forecastAt.y+forecastStrip.height-1
                    || ribbonAt.y+ribbon.height>moon.height-inset+1)
                    return root.fail("C20_INSTRUMENT_PROPORTION_OR_OVERFLOW");

                yearTab.clicked(null);
                if(root.lastMoonRoute!=="cosmos/moon/year")
                    return root.fail("MOON_YEAR_MODE_ROUTE_BROKEN");

                if(!forecastStrip.verticalMode || !forecastStrip.model.ready
                    || forecastStrip.rows.length!==7
                    || forecastStrip.focusedDay.date!=="2026-11-06"
                    || forecastStrip.focusedDay.illumination!==23
                    || forecastDay.height<13
                    || forecastDay.width<140
                    || verticalForecast.height<90
                    || forecastDaylight.height<10)
                    return root.fail("C20_VERTICAL_FORECAST_NOT_MOUNTED");
                forecastStrip.selectedDate="2026-11-07";

                if(count(phase,"cosmos-c8-moon-fact")!==0
                    || count(moon,"cosmos-c8-moon-fact")!==9
                    || count(position,"cosmos-c8-moon-fact")!==3
                    || count(ribbon,"cosmos-c8-moon-fact")!==3
                    || count(provenance,"cosmos-c8-moon-fact")!==3)
                    return root.fail("C20_SOURCE_FACTS_OR_SEPARATE_LEDGER_LOST");
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
                // Verify manually selected larger chassis can scale the Moon
                // without changing source ownership or right-side contents.
                testWindow.width=700;
                testWindow.height=420;
                root.step=6;
            } else if(root.step===6){
                const phase=find(moon,"cosmos-c8-moon-phase");
                const disk=find(phase,"cosmos-c21-moon-hero-disk");
                const right=find(moon,"cosmos-c19-moon-forecast-strip");
                if(!disk || !right || disk.width<root.compactMoonDiskWidth+20
                    || phase.width<root.compactMoonHeroWidth+100
                    || right.rows.length!==7
                    || count(moon,"cosmos-c8-moon-fact")!==9)
                    return root.fail("C21_LARGE_SIZE_MOON_SCALE_OR_SOURCE_LOSS");
                root.done=true;
                console.log("C8_MOON_PASS // C21_LARGE_DISK COMPACT+LARGE NO_SCROLL NINE_FACTS SOURCE_PRESERVED");
                Qt.quit();
            }
        }
    }
}
