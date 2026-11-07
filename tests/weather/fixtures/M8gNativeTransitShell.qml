import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather"
import "services/weather"
import "widgets/weather/StationMagickTransitTimelinePolicy.js" as Timeline

// M8g: Real disposable Quickshell/Qt native component, all inputs synthetic.
// The JPL service's response parser is exercised, never its local Python process.
ShellRoot {
    id:root
    property bool complete:false
    property string selectedExact:""
    property string selectedMinute:""
    property var birthChart:fixtureChart()

    function fixtureChart() {
        const bodies=["sun","moon","mercury","venus","mars_barycenter",
            "jupiter_barycenter","saturn_barycenter","uranus_barycenter",
            "neptune_barycenter","pluto_barycenter"];
        const naif=[10,301,199,299,4,5,6,7,8,9];
        return {
            format:"post-apollo.weather.magick-natal-chart.m8a.v1",
            epoch_utc:"2000-03-21T15:20:00Z",origin:"topocentric",
            frame:"true-ecliptic-of-date",position_model:"apparent",
            zodiac:"tropical",house_system:"whole-sign",
            ascendant_deg:22.25,mc_deg:292.3,
            observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
            provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
                house_method:"true-equinox-horizon-meridian-geometric"},
            house_cusps_deg:Array.from({length:12},(_,i)=>i*30),
            positions:bodies.map(function(body,i){
                return {id:body,naif_id:naif[i],
                    longitude_deg:i===0?10:(14+i*31)%360,
                    latitude_deg:0,distance_au:1.2};
            })
        };
    }
    function fixtureResponse(req) {
        const start=Date.parse(req.start_utc);
        const end=Date.parse(req.end_utc);
        function row(ms,v){
            return {epoch_utc:new Date(ms).toISOString().slice(0,19)+"Z",
                longitude_deg:(10+v)%360,relative_unwrapped_deg:v};
        }
        return {format:Timeline.RESULT_FORMAT,
            source:{engine:"skyfield",
                ephemeris_sha256:"a".repeat(64),
                position_model:"topocentric-apparent",
                coordinate_frame:"true-ecliptic-of-date"},
            observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
            natal_epoch_utc:req.natal_epoch_utc,
            natal_body:"sun",transit_body:"moon",
            natal_longitude_deg:10,
            start_utc:req.start_utc,end_utc:req.end_utc,
            sample_minutes:60,sample_count:169,
            timeline:[row(start,40),row(start+86400000,60),row(end,70)],
            contacts:[{utc:"2026-11-08T03:12:36Z",
                aspect:"sextile",aspect_target_deg:60,
                direction:"prograde",residual_deg:0.00001}],
            limitations:{crossing_search_not_tangency_complete:true,
                contact_time_precision_seconds:1,
                chart_uses_respective_equinoxes_of_date:true,
                medical_or_spiritual_causality_claim:false}
        };
    }
    CelestialTransitTimelineService {
        id:service
        active:true
        natalChart:root.birthChart
    }
    Window {
        visible:true
        width:610;height:470
        StationMagickTransitTimelinePane {
            id:timelinePane
            anchors.fill:parent
            natalData:root.birthChart
            finder:service
            onContactRequested:function(utc){
                root.selectedExact=utc;
                root.selectedMinute=Timeline.nearestMinute(utc);
            }
        }
    }
    function fail(message) {
        if(complete)return;
        complete=true;console.error("M8G_NATIVE_FAIL // "+message);Qt.quit();
    }
    function check(ok,reason) {
        if(!ok)fail(reason);
        return !!ok;
    }
    Timer {
        interval:300;running:true;repeat:false
        onTriggered:{
            if(!root.check(timelinePane.natalReady,"NATAL_QML_MODEL"))return;
            timelinePane.startDate="2026-11-07";
            timelinePane.natalIndex=0;
            timelinePane.transitIndex=1;
            timelinePane.spanDays=7;
            timelinePane.sampleMinutes=60;
            if(!root.check(timelinePane.validSearch,"SOURCE_REQUEST"))return;
            const req=Timeline.request(root.birthChart,"2026-11-07",7,
                                       "sun","moon",60);
            if(!root.check(req!==null,"REQUEST_UNAVAILABLE"))return;
            service.pending=req;
            service.accept(JSON.stringify(root.fixtureResponse(req)));
            if(!root.check(service.ready,"SOURCE_RESPONSE_REJECTED"))return;
            if(!root.check(timelinePane.model &&
                timelinePane.model.contacts.length===1,"CONTACTS_NOT_BOUND"))return;
            if(!root.check(timelinePane.geometry &&
                timelinePane.geometry.points.length===3,"NATIVE_PLOT_NOT_BOUND"))return;
            timelinePane.zoomAt(1.25,200);
            if(!root.check(timelinePane.zoom>1,"ZOOM_CONTROL"))return;
            timelinePane.chooseEvent("2026-11-08T03:12:36Z");
            if(!root.check(root.selectedExact==="2026-11-08T03:12:36Z",
                "PRECISE_EVENT_LOST"))return;
            if(!root.check(root.selectedMinute==="2026-11-08T03:13:00Z",
                "MINUTE_HANDOFF_INCORRECT"))return;
            timelinePane.fit();
            if(!root.check(timelinePane.zoom===1,"FIT_CONTROL"))return;
            root.complete=true;
            console.log("M8G_NATIVE_PASS // JPL_CONTRACT_QML_TIMELINE_EVENT_HANDOFF");
            Qt.quit();
        }
    }
    Timer {
        interval:9000;running:true;repeat:false
        onTriggered:root.fail("TIMEOUT")
    }
}
