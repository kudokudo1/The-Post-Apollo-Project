import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather"
import "services/weather"
import "widgets/weather/StationMagickTransitMultiPolicy.js" as Multi

// M8h // Actual offscreen QML components with SYNTHETIC numbers only.
// No real birth data, network, JPL process launch or host desktop mutation.
ShellRoot {
    id:root
    property bool complete:false
    property string chosenExact:""
    property string chosenBody:""
    property string chosenKind:""
    property string chosenMinute:""
    property var natal:fakeNatal()
    function fakeNatal(){
        const names=Multi.TARGETS;
        return {
            format:"post-apollo.weather.magick-natal-chart.m8a.v1",
            epoch_utc:"2000-03-21T15:20:00Z",
            origin:"topocentric",frame:"true-ecliptic-of-date",
            position_model:"apparent",zodiac:"tropical",house_system:"whole-sign",
            observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
            provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
                house_method:"true-equinox-horizon-meridian-geometric"},
            ascendant_deg:22.25,mc_deg:292.3,
            house_cusps_deg:Array.from({length:12},(_,i)=>i*30),
            positions:names.map(function(id,i){return {
                id:id,naif_id:Multi.NAIF[id],
                longitude_deg:i===0?10:(14+i*31)%360,
                latitude_deg:0,distance_au:1.2
            };})
        };
    }
    function fakeResponse(req){
        const a=Date.parse(req.start_utc),z=Date.parse(req.end_utc);
        const points=(index)=>[0,1,7].map(function(day){
            const ms=day===7?z:a+day*86400000;
            const relative=40+index*3+day*2;
            return {epoch_utc:new Date(ms).toISOString().slice(0,19)+"Z",
                longitude_deg:(10+relative)%360,
                relative_unwrapped_deg:relative};
        });
        return {format:Multi.RESULT_FORMAT,
            source:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
                position_model:"topocentric-apparent",
                coordinate_frame:"true-ecliptic-of-date"},
            observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
            natal_epoch_utc:req.natal_epoch_utc,natal_body:req.natal_body,
            natal_longitude_deg:10,
            start_utc:req.start_utc,end_utc:req.end_utc,
            transit_bodies:req.transit_bodies.slice(),
            sample_minutes:60,aspects_deg:req.aspects_deg.slice(),
            include_stations:true,
            series:req.transit_bodies.map(function(id,i){return {
                id:id,sample_count:169,timeline:points(i)};
            }),
            events:[
                {utc:"2026-11-08T03:12:36Z",
                    type:"aspect",natal_body:"sun",transit_body:"moon",
                    aspect:"sextile",aspect_target_deg:60,
                    direction:"prograde",residual_deg:0.00001},
                {utc:"2026-11-09T06:00:00Z",
                    type:"station",natal_body:"sun",transit_body:"mercury",
                    direction:"retrograde",longitude_deg:103.75,
                    velocity_deg_day:0.003,uncertainty_seconds:60}
            ],
            limitations:{
                crossing_search_not_tangency_complete:true,
                station_search_not_all_turns_guaranteed:true,
                station_velocity_central_difference_minutes:20,
                station_time_bracket_seconds:60,
                contact_time_precision_seconds:1,
                chart_uses_respective_equinoxes_of_date:true,
                medical_or_spiritual_causality_claim:false
            }
        };
    }
    CelestialTransitMultiService {
        id: service
        active:true
        natalChart:root.natal
    }
    Window {
        visible:true
        width:650;height:500
        StationMagickTransitMultiPane {
            id:multiPane
            anchors.fill:parent
            natalData:root.natal
            finder:service
            onEventRequested:function(exactUtc,body,kind){
                root.chosenExact=exactUtc;
                root.chosenBody=body;
                root.chosenKind=kind;
                root.chosenMinute=Multi.nearestMinute(exactUtc);
            }
        }
    }
    function fail(reason){
        if(complete)return;
        complete=true;
        console.error("M8H_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    function check(ok,reason){
        if(!ok)fail(reason);
        return !!ok;
    }
    Timer {
        interval:320;running:true;repeat:false
        onTriggered:{
            multiPane.startDate="2026-11-07";
            multiPane.spanDays=7;
            multiPane.sampleMinutes=60;
            multiPane.natalIndex=0;
            multiPane.selectedBodies=["moon","mercury","venus"];
            multiPane.selectedAspects=[60,90];
            if(!root.check(multiPane.canSearch,"SOURCE_REQUEST_INVALID"))return;
            const req=Multi.request(root.natal,"2026-11-07",7,
                "sun",["moon","mercury","venus"],[60,90],60);
            if(!root.check(req!==null,"MISSING_REQUEST"))return;
            service.pending=req;
            service.accept(JSON.stringify(root.fakeResponse(req)));
            if(!root.check(service.ready,"SOURCE_NOT_VALIDATED"))return;
            if(!root.check(multiPane.model && multiPane.model.ready,
                "MODEL_NOT_BOUND"))return;
            if(!root.check(multiPane.geometry &&
                multiPane.geometry.lines.length===3,"THREE_LINES_NOT_DRAWN"))return;
            if(!root.check(multiPane.visibleEvents.length===2,
                "EVENT_BROWSER_MISSING"))return;
            multiPane.browserKind="station";
            if(!root.check(multiPane.visibleEvents.length===1 &&
                multiPane.visibleEvents[0].type==="station",
                "STATION_FILTER_FAILED"))return;
            multiPane.browserKind="ALL";
            multiPane.browserPlanet="moon";
            if(!root.check(multiPane.visibleEvents.length===1,
                "PLANET_FILTER_FAILED"))return;
            multiPane.browserPlanet="";
            multiPane.descending=true;
            if(!root.check(multiPane.visibleEvents[0].type==="station",
                "SORT_ORDER_FAILED"))return;
            multiPane.zoomAt(1.25,200);
            if(!root.check(multiPane.zoom>1,"ZOOM_FAILED"))return;
            multiPane.fit();
            if(!root.check(multiPane.zoom===1,"FIT_FAILED"))return;
            multiPane.chooseEvent(multiPane.model.events[1]);
            if(!root.check(root.chosenKind==="station" &&
                root.chosenBody==="mercury","STATION_CALLBACK_FAILED"))return;
            if(!root.check(root.chosenExact==="2026-11-09T06:00:00Z" &&
                root.chosenMinute==="2026-11-09T06:00:00Z",
                "EVENT_HANDOFF_FAILED"))return;
            multiPane.chooseEvent(multiPane.model.events[0]);
            if(!root.check(root.chosenExact==="2026-11-08T03:12:36Z" &&
                root.chosenMinute==="2026-11-08T03:13:00Z",
                "PRECISE_ASPECT_HANDOFF_FAILED"))return;
            root.complete=true;
            console.log("M8H_NATIVE_PASS // THREE_PLANETS_STATIONS_FILTERS_EVENTS");
            Qt.quit();
        }
    }
    Timer {
        interval:9000;running:true;repeat:false
        onTriggered:root.fail("TIMEOUT")
    }
}
