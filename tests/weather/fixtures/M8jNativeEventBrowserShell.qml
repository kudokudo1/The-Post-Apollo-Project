import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather"
import "services/weather"
import "widgets/weather/StationMagickTransitMultiPolicy.js" as Multi

// M8j // Actual offscreen QML components with SYNTHETIC numbers only.
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
        console.error("M8J_NATIVE_FAIL // "+reason);
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
            // Source-shaped fixture only. All 29 mock events have valid
            // JPL contract fields but are not real astronomical predictions.
            const synthetic=root.fakeResponse(req);
            const from=Date.parse(req.start_utc);
            synthetic.events=Array.from({length:29},function(_,i){
                const ms=from+(i*4+1)*3600000+(i%3===0?36000:0);
                const eventUtc=new Date(ms).toISOString().slice(0,19)+"Z";
                if(i%7===2)return {
                    utc:eventUtc,type:"station",natal_body:"sun",
                    transit_body:"mercury",direction:"retrograde",
                    longitude_deg:103.75+i,velocity_deg_day:0.003,
                    uncertainty_seconds:60
                };
                return {
                    utc:eventUtc,type:"aspect",natal_body:"sun",
                    transit_body:i%2===0?"moon":"venus",
                    aspect:i%3===0?"square":"sextile",
                    aspect_target_deg:i%3===0?90:60,
                    direction:i%2===0?"prograde":"retrograde",
                    residual_deg:0.00001
                };
            });
            service.pending=req;
            service.accept(JSON.stringify(synthetic));
            if(!root.check(service.ready,"VERIFIED_EVENTS_REJECTED"))return;
            if(!root.check(multiPane.geometry &&
                multiPane.geometry.lines.length===3,"THREE_TRACKS_NOT_DRAWN"))return;
            if(!root.check(multiPane.visibleEvents.length===29,
                "EVENT_BROWSER_INCOMPLETE"))return;
            if(!root.check(multiPane.pageData.pages===3 &&
                multiPane.pageData.items.length===12,"PAGE_1_WRONG"))return;
            multiPane.goPage(1);
            if(!root.check(multiPane.pageData.index===1 &&
                multiPane.pageData.items.length===12,"PAGE_2_WRONG"))return;
            multiPane.goPage(1);
            if(!root.check(multiPane.pageData.index===2 &&
                multiPane.pageData.items.length===5,"PAGE_3_WRONG"))return;
            multiPane.browserKind="station";
            if(!root.check(multiPane.pageData.index===0 &&
                multiPane.visibleEvents.length===4,"STATION_FILTER_WRONG"))return;
            multiPane.browserKind="ALL";
            multiPane.browserAspect="square";
            if(!root.check(multiPane.visibleEvents.length<29 &&
                multiPane.visibleEvents.some(function(e){return e.type==="station";}),
                "ASPECT_FILTER_DROPPED_STATIONS"))return;
            multiPane.browserMotion="retrograde";
            if(!root.check(multiPane.visibleEvents.every(function(e){
                return e.direction==="retrograde";
            }),"MOTION_FILTER_WRONG"))return;
            multiPane.browserMotion="ALL";
            multiPane.browserAspect="ALL";
            multiPane.inspectEvent(multiPane.model.events[2]);
            if(!root.check(multiPane.inspectedEvent &&
                multiPane.inspectedEvent.type==="station" &&
                multiPane.inspectedEvent.numerical_bracket_seconds===60,
                "STATION_INFO_WRONG"))return;
            if(!root.check(root.chosenExact==="",
                "INFO_SHOULD_NOT_OPEN_WHEEL"))return;
            multiPane.inspectEvent(multiPane.model.events[0]);
            if(!root.check(multiPane.inspectedEvent &&
                multiPane.inspectedEvent.type==="aspect" &&
                multiPane.inspectedEvent.numerical_bracket_seconds===1,
                "ASPECT_INFO_WRONG"))return;
            multiPane.chooseEvent(multiPane.model.events[0]);
            if(!root.check(root.chosenBody==="moon" &&
                root.chosenKind==="aspect","WHEEL_CALLBACK_WRONG"))return;
            if(!root.check(root.chosenMinute===
                new Date(Math.round(Date.parse(root.chosenExact)/60000)*60000)
                   .toISOString().slice(0,16)+":00Z",
                "PRECISE_EVENT_ROUNDING_WRONG"))return;
            multiPane.zoomAt(1.25,200);
            if(!root.check(multiPane.zoom>1,"ZOOM_BROKEN"))return;
            multiPane.fit();
            if(!root.check(multiPane.zoom===1,"FIT_BROKEN"))return;
            root.complete=true;
            console.log("M8J_NATIVE_PASS // PAGING_FILTERS_INSPECTOR_WHEEL_HANDOFF");
            Qt.quit();
        }
    }
    Timer {
        interval:9000;running:true;repeat:false
        onTriggered:root.fail("TIMEOUT")
    }
}
