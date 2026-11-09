import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// Disposable offscreen JPL fixture. Populates only synthetic in-memory atlases;
// no user kernel, calendar file, provider credentials or network connection.
ShellRoot {
    id: root
    property bool done: false
    property int phase: 0
    property int ticks: 0
    property string lastMoonRoute: ""

    // Forecast model is provider-local and synthetic; it is NOT JPL data.
    QtObject {
        id: mockWeather
        property bool forecastReady: true
        property string localObservationDateTime: "2026-11-06T12:00:00"
        property var dailyForecast: [
            {date:"2026-11-06",moonPhase:"waning crescent",
             moonIllumination:23,sunrise:"6:45 AM",sunset:"5:04 PM"},
            {date:"2026-11-07",moonPhase:"new moon",
             moonIllumination:3,sunrise:"6:46 AM",sunset:"5:03 PM"},
            {date:"2026-11-08",moonPhase:"waxing crescent",
             moonIllumination:9,sunrise:"6:47 AM",sunset:"5:02 PM"}
        ]
    }

    Window {
        visible: true
        width: 1390
        height: 288
        color: "black"
        Row {
            anchors.fill: parent
            spacing: 6
            Weather.StationCosmosAnnualWheelPane {
                id: moon
                width: 450
                height: 276
                subject: "moon"
                runtimeNowMs: Date.UTC(2026,10,6,20,0)
                onRouteRequested: function(path) {
                    root.lastMoonRoute=path;
                }
            }
            Weather.StationCosmosAnnualWheelPane {
                id: sun
                width: 450
                height: 276
                subject: "sun"
                runtimeNowMs: Date.UTC(2026,10,6,20,0)
            }
            Weather.StationCosmosAnnualWheelPane {
                id: forecast
                width: 450
                height: 276
                subject: "moon"
                moonView: "forecast"
                weatherService: mockWeather
                runtimeNowMs: Date.UTC(2026,10,6,20,0)
                onRouteRequested: function(path) {
                    root.lastMoonRoute=path;
                }
            }
        }
    }

    function find(item,name) {
        if (!item) return null;
        if (item.objectName===name) return item;
        const c=item.children||[];
        for (let i=0;i<c.length;i++){
            const child=find(c[i],name);
            if(child) return child;
        }
        return null;
    }
    function fail(message){
        if(done) return;
        done=true;
        console.error("C11_ANNUAL_FAIL // "+message);
        Qt.quit();
    }
    function sampleAtlas(){
        const year=2026, start=Date.UTC(year,0,1),days=[];
        for(let i=0;i<365;i++){
            const d=new Date(start+i*86400000);
            days.push({
                date:d.toISOString().slice(0,10),
                day_index:i,month:d.getUTCMonth()+1,
                phase_angle_deg:(i*12.2)%360,
                phase_id:"new",illumination:i%101
            });
        }
        const terms=[];
        for(let i=0;i<24;i++){
            terms.push({
                kind:"solar",id:"solar-term-"+i,
                date:days[i*15].date,
                time_utc:"12:00:00Z",longitude_deg:i*15,
                major:i%6===0
            });
        }
        return {
            ready:true,year:2026,timezone:"UTC",days:days,
            lunar_events:[
                {kind:"moon",id:"new",date:days[0].date,time_utc:"2026-01-01T00:00:00Z"},
                {kind:"moon",id:"full",date:days[14].date,time_utc:"2026-01-15T00:00:00Z"}
            ],
            solar_terms:terms
        };
    }

    Timer {
        interval: 110
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if(root.ticks>35) return root.fail("TIMEOUT");
            const ml=moon.wheelItem,sl=sun.wheelItem,fl=forecast.wheelItem;
            if(!ml || !sl || !fl) return;
            const moonCanvas=find(moon,"magick-m7-annual-wheel-canvas");
            const sunCanvas=find(sun,"magick-m7-annual-wheel-canvas");
            const moonModes=find(moon,"magick-m7-annual-subject-tabs");
            const sunModes=find(sun,"magick-m7-annual-subject-tabs");
            const forecastModes=find(forecast,"magick-m7-annual-subject-tabs");
            const forecastOutlook=find(forecast,"magick-m7-forecast-outlook");
            const forecastCanvas=find(forecast,"magick-m7-annual-wheel-canvas");
            const moonTitle=find(moon,"cosmos-c44-moon-year-header");
            const forecastTitle=find(forecast,"cosmos-c44-moon-year-header");
            const yearRail=find(moon,"cosmos-c11-moon-year-mode-rail");
            const forecastRail=find(forecast,"cosmos-c11-moon-year-mode-rail");
            const yearDivider=find(moon,"cosmos-c23-moon-year-divider");
            const forecastDivider=find(forecast,"cosmos-c23-moon-year-divider");
            const sunDivider=find(sun,"cosmos-c23-moon-year-divider");
            const phaseTab=find(moon,"cosmos-c11-back-to-moon");
            const yearTab=find(moon,"cosmos-c17-moon-wheel-tab");
            const forecastOverview=find(forecast,"cosmos-c11-back-to-moon");
            if(root.phase===0){
                if(ml.view!=="moon" || ml.lockedView!=="moon"
                    || sl.view!=="solar" || sl.lockedView!=="solar"
                    || fl.view!=="forecast" || fl.lockedView!=="forecast"
                    || !moonCanvas || !sunCanvas || !moonModes || !sunModes
                    || !forecastModes || !forecastOutlook || !forecastCanvas
                    || moonModes.visible || sunModes.visible || forecastModes.visible
                    || forecastCanvas.visible)
                    return root.fail("REUSED_WHEEL_LOCK_OR_FORECAST_MISSING");
                if(!yearRail || !forecastRail || !phaseTab
                    || !yearTab || !forecastOverview
                    || yearRail.height!==27 || forecastRail.height!==27
                    || phaseTab.width<200 || yearTab.width<200
                    || forecastOverview.width<200 || phaseTab.height!==27
                    || yearTab.height!==27 || forecastOverview.height!==27
                    || !yearTab.selected || forecastOverview.selected)
                    return root.fail("MOON_C18_FULL_WIDTH_MODE_RAIL_FAILED");
                const yearRailAt=yearRail.mapToItem(moon,0,0);
                const moonTitleAt=moonTitle ? moonTitle.mapToItem(moon,0,0) : null;
                const forecastTitleAt=forecastTitle
                    ? forecastTitle.mapToItem(forecast,0,0) : null;
                if(!moonTitleAt || !forecastTitleAt
                    || moonTitleAt.y!==6 || forecastTitleAt.y!==6
                    || moonTitle.height!==18 || forecastTitle.height!==18
                    || moonTitle.width!==438 || forecastTitle.width!==438
                    || yearRailAt.y!==28)
                    return root.fail("C44_MOON_YEAR_HEADER_NOT_ALIGNED");
                const yearDividerAt=yearDivider
                    ? yearDivider.mapToItem(moon,0,0) : null;
                const forecastDividerAt=forecastDivider
                    ? forecastDivider.mapToItem(forecast,0,0) : null;
                const yearStageAt=ml.mapToItem(moon,0,0);
                const forecastStageAt=fl.mapToItem(forecast,0,0);
                if(!yearDivider || !forecastDivider || !sunDivider
                    || !yearDivider.visible || !forecastDivider.visible
                    || sunDivider.visible || sunDivider.height!==0
                    || yearDivider.height!==2 || forecastDivider.height!==2
                    || yearDividerAt.y!==yearRailAt.y+yearRail.height+5
                    || yearStageAt.y!==yearDividerAt.y+2+3
                    || forecastStageAt.y!==forecastDividerAt.y+2+3
                    || yearDividerAt.x!==6 || forecastDividerAt.x!==6)
                    return root.fail("C23_MOON_YEAR_HEADER_DIVIDER_BROKEN");
                // C44 adds a real 18px title to MOON (not SUN), so the
                // original 276px fixture retains a useful ~205px wheel.
                if(moonCanvas.width<400 || moonCanvas.height<190
                    || sunCanvas.width<400 || sunCanvas.height<250
                    || forecastOutlook.width<400 || forecastOutlook.height<190)
                    return root.fail("SMALL_OR_CLIPPED_MOON_INSTRUMENT");
                if(ml.calendarSource.loading || sl.calendarSource.loading
                    || fl.calendarSource.active || fl.calendarSource.loading)
                    return root.fail("FORECAST_MUST_NOT_START_JPL_SERVICE");
                if(!forecastOutlook.compactLayout
                    || !forecastOutlook.model.ready
                    || forecastOutlook.model.rows.length!==3
                    || forecastOutlook.focusedDay.date!=="2026-11-06")
                    return root.fail("FORECAST_DAILY_WEATHER_BINDING_MISSING");
                const atlas=root.sampleAtlas();
                ml.calendarSource.atlas=atlas;
                sl.calendarSource.atlas=atlas;
                ml.calendarSource.ready=true;
                sl.calendarSource.ready=true;
                root.phase=1;
            } else if(root.phase===1){
                if(!ml.model.ready || !sl.model.ready
                    || ml.model.days.length!==365 || sl.model.solar_terms.length!==24
                    || ml.model.lunar_events.length!==2
                    || ml.selectedYear!==2026 || sl.selectedYear!==2026)
                    return root.fail("ANNUAL_LUNAR_SOLAR_DATA_LOST");
                forecastOutlook.selectedDate="2026-11-07";
                ml.scopeMode="month";
                ml.selectedMonth=2;
                sl.selectedSolar=sl.model.solar_terms[10].id;
                root.phase=2;
            } else if(root.phase===2){
                if(ml.moonMonth.length!==28
                    || !sl.currentTerm || sl.currentTerm.id!=="solar-term-10"
                    || !forecastOutlook.focusedDay
                    || forecastOutlook.focusedDay.date!=="2026-11-07"
                    || forecastOutlook.focusedDay.illumination!==3)
                    return root.fail("MONTH_SOLAR_TERM_OR_FORECAST_SELECTION_BROKEN");
                ml.fitWheel();
                sl.fitWheel();
                ml.zoomAt(1.25,200,120);
                root.phase=3;
            } else if(root.phase===3){
                console.log("C11_ZOOM_DIAG // moon="+ml.wheelZoom+" sun="+sl.wheelZoom+" days="+ml.moonMonth.length);
                if(ml.wheelZoom!==1.25 || sl.wheelZoom!==1
                    || ml.moonMonth.length!==28)
                    return root.fail("ANNUAL_ZOOM_OR_MONTH_VIEW_BROKEN");
                ml.panBy(15,-10);
                ml.resetView();
                const back=find(moon,"cosmos-c11-back-to-moon");
                if(!back) return root.fail("PHASE_BACK_BUTTON_MISSING");
                back.clicked(null);
                root.phase=4;
            } else if(root.phase===4){
                if(root.lastMoonRoute!=="cosmos/moon/ephemeris"
                    || ml.wheelZoom!==1.6
                    || ml.calendarSource.loading || sl.calendarSource.loading
                    || fl.calendarSource.active)
                    return root.fail("RETURN_ROUTE_OR_JPL_LAZY_GATE_BROKEN");
                const backward=find(forecast,"cosmos-c17-moon-wheel-tab");
                if(!backward || fl.view!=="forecast")
                    return root.fail("INDEX_FORECAST_INSPECTOR_LOST");
                backward.clicked(null);
                if(root.lastMoonRoute!=="cosmos/moon/year")
                    return root.fail("INDEX_FORECAST_TO_YEAR_ROUTE_BROKEN");
                root.done=true;
                console.log("C11_ANNUAL_PASS // BOTH_WHEELS JPL_ATLAS MONTH SOLAR_TERMS ZOOM_PAN BACK + C17_MOON_FORECAST");
                Qt.quit();
            }
        }
    }
}