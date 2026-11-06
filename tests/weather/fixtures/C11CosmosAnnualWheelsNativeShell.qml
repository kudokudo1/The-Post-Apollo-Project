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

    Window {
        visible: true
        width: 930
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
            const ml=moon.wheelItem,sl=sun.wheelItem;
            if(!ml || !sl) return;
            const moonCanvas=find(moon,"magick-m7-annual-wheel-canvas");
            const sunCanvas=find(sun,"magick-m7-annual-wheel-canvas");
            const moonModes=find(moon,"magick-m7-annual-subject-tabs");
            const sunModes=find(sun,"magick-m7-annual-subject-tabs");
            if(root.phase===0){
                if(ml.view!=="moon" || ml.lockedView!=="moon"
                    || sl.view!=="solar" || sl.lockedView!=="solar"
                    || !moonCanvas || !sunCanvas || !moonModes || !sunModes
                    || moonModes.visible || sunModes.visible)
                    return root.fail("REUSED_WHEEL_LOCK_OR_CANVAS_MISSING");
                if(moonCanvas.width<400 || moonCanvas.height<220
                    || sunCanvas.width<400 || sunCanvas.height<250)
                    return root.fail("SMALL_OR_CLIPPED_WHEEL_CANVAS");
                if(ml.calendarSource.loading || sl.calendarSource.loading)
                    return root.fail("ANNUAL_JPL_CALCULATED_WITHOUT_CONSENT");
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
                ml.scopeMode="month";
                ml.selectedMonth=2;
                sl.selectedSolar=sl.model.solar_terms[10].id;
                root.phase=2;
            } else if(root.phase===2){
                if(ml.moonMonth.length!==28
                    || !sl.currentTerm || sl.currentTerm.id!=="solar-term-10")
                    return root.fail("MONTH_OR_SOLAR_TERM_SELECTION_BROKEN");
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
                    || ml.calendarSource.loading || sl.calendarSource.loading)
                    return root.fail("RETURN_ROUTE_OR_JPL_LAZY_GATE_BROKEN");
                root.done=true;
                console.log("C11_ANNUAL_PASS // BOTH_WHEELS JPL_ATLAS MONTH SOLAR_TERMS ZOOM_PAN BACK");
                Qt.quit();
            }
        }
    }
}