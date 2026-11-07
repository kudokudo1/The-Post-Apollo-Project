import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather"
import "services/weather"
import "widgets/weather/StationMagickTransitMatrixPolicy.js" as Matrix

// M8l: real disposable offscreen Qt/Quickshell, source-shaped SYNTHETIC data.
// Does not execute Skyfield, read real birth dates or access live config.
ShellRoot {
    id:root
    property bool complete:false
    property string chosenUtc:""
    property string chosenNatal:""
    property string chosenMoving:""
    property string chosenKind:""
    property var natal:fakeNatal()
    function fakeNatal(){
        return {
            format:"post-apollo.weather.magick-natal-chart.m8a.v1",
            epoch_utc:"2000-03-21T15:20:00Z",
            origin:"topocentric",frame:"true-ecliptic-of-date",
            position_model:"apparent",zodiac:"tropical",house_system:"whole-sign",
            observer:{latitude_deg:38.9,longitude_deg:-76.8,elevation_m:0},
            provenance:{engine:"skyfield",ephemeris_sha256:"a".repeat(64),
                house_method:"true-equinox-horizon-meridian-geometric"},
            ascendant_deg:22.25,mc_deg:292.3,
            house_cusps_deg:Array.from({length:12},(_,i)=>30*i),
            positions:Matrix.TARGETS.map(function(id,i){return {
                id:id,naif_id:Matrix.NAIF[id],
                longitude_deg:i===0?10:i===3?25:(14+i*31)%360,
                latitude_deg:0,distance_au:1.2
            };})
        };
    }
    function fakeResult(q){
        const from=Date.parse(q.start_utc),to=Date.parse(q.end_utc);
        const points=function(index){
            return [from,from+(to-from)/2,to].map(function(t,i){
                return {epoch_utc:new Date(t).toISOString().slice(0,19)+"Z",
                    longitude_deg:40+index*12+i*3};
            });
        };
        const cells=[];
        q.transit_bodies.forEach(function(t){
            q.natal_bodies.forEach(function(n){
                cells.push({natal_body:n,transit_body:t,
                    aspect_count:n==="sun"&&t==="moon"?1:0});
            });
        });
        return {
            format:Matrix.RESULT_FORMAT,
            source:{engine:"skyfield",ephemeris_sha256:q.expected_ephemeris_sha256,
                position_model:"topocentric-apparent",
                coordinate_frame:"true-ecliptic-of-date"},
            observer:{latitude_deg:q.latitude_deg,longitude_deg:q.longitude_deg,
                elevation_m:0},
            natal_epoch_utc:q.natal_epoch_utc,
            natal_bodies:q.natal_bodies.slice(),
            natal_longitudes:q.natal_bodies.map(function(id){
                return {id:id,longitude_deg:root.natal.positions.find(
                    function(p){return p.id===id;}).longitude_deg};
            }),
            transit_bodies:q.transit_bodies.slice(),
            start_utc:q.start_utc,end_utc:q.end_utc,
            sample_minutes:q.sample_minutes,sample_count:Math.ceil((to-from)/(q.sample_minutes*60000))+1,
            aspects_deg:q.aspects_deg.slice(),
            include_stations:true,
            series:q.transit_bodies.map(function(id,i){
                return {id:id,sample_count:Math.ceil((to-from)/(q.sample_minutes*60000))+1,timeline:points(i)};
            }),
            matrix:cells,
            events:[
                {utc:"2026-11-07T03:12:36Z",type:"aspect",natal_body:"sun",
                    transit_body:"moon",aspect:"sextile",aspect_target_deg:60,
                    direction:"prograde",residual_deg:.00001},
                {utc:"2026-11-07T06:00:00Z",type:"station",natal_body:null,
                    transit_body:"mercury",direction:"retrograde",
                    longitude_deg:105.6,velocity_deg_day:.0003,
                    uncertainty_seconds:60}
            ],
            limitations:{
                crossing_search_not_tangency_complete:true,
                station_search_not_all_turns_guaranteed:true,
                station_rate_scan_interval_minutes_max:15,
                station_velocity_central_difference_minutes:20,
                station_time_bracket_seconds:60,
                contact_time_precision_seconds:1,
                stations_not_natal_pairs:true,
                chart_uses_respective_equinoxes_of_date:true,
                medical_or_spiritual_causality_claim:false
            }
        };
    }
    CelestialTransitMatrixService {
        id:service
        active:true
        natalChart:root.natal
    }
    Window {
        visible:true
        width:640;height:525
        StationMagickTransitMatrixPane {
            id:matrixPane
            anchors.fill:parent
            natalData:root.natal
            finder:service
            onEventRequested:function(exactUtc,natalBody,transitBody,kind){
                root.chosenUtc=exactUtc;
                root.chosenNatal=natalBody;
                root.chosenMoving=transitBody;
                root.chosenKind=kind;
            }
        }
    }
    function fail(reason){
        if(complete)return;
        complete=true;
        console.error("M8L_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    function check(ok,reason){
        if(!ok)fail(reason);
        return !!ok;
    }
    Timer {
        interval:370;running:true;repeat:false
        onTriggered:{
            matrixPane.startDate="2026-11-07";
            matrixPane.natalBodies=["sun","moon","mercury","venus"];
            matrixPane.transitBodies=["moon","mercury","venus","mars_barycenter"];
            matrixPane.spanDays=7;matrixPane.sampleMinutes=60;
            matrixPane.aspectAngles=[60,90];
            if(!root.check(matrixPane.workload.pairs===16 &&
                matrixPane.workload.pairSamples===2704 &&
                !matrixPane.workload.valid,"FOUR_BY_FOUR_BUDGET_NOT_ENFORCED"))return;
            if(!root.check(!matrixPane.canSearch &&
                matrixPane.suggestedSpan===1,"FIT_RANGE_NOT_AVAILABLE"))return;
            matrixPane.spanDays=matrixPane.suggestedSpan;
            if(!root.check(matrixPane.canSearch &&
                matrixPane.workload.pairSamples===400 &&
                matrixPane.workload.stationSamples===388,
                "FIT_RANGE_NOT_SAFE"))return;
            matrixPane.toggleBody(true,"jupiter_barycenter");
            if(!root.check(matrixPane.natalBodies.length===4,
                "FIFTH_NATAL_BODY_ACCEPTED"))return;
            matrixPane.toggleBody(false,"pluto_barycenter");
            if(!root.check(matrixPane.transitBodies.length===4,
                "FIFTH_MOVING_BODY_ACCEPTED"))return;
            const req=Matrix.request(root.natal,"2026-11-07",1,
                ["sun","moon","mercury","venus"],
                ["moon","mercury","venus","mars_barycenter"],[60,90],60);
            if(!root.check(req!==null,"SOURCE_4X4_REQUEST_MISSING"))return;
            service.pending=req;
            service.accept(JSON.stringify(root.fakeResult(req)));
            if(!root.check(service.ready,"JPL_SOURCE_GATE_REJECTED"))return;
            if(!root.check(matrixPane.model&&matrixPane.model.ready,
                "QML_MODEL_NOT_BOUND"))return;
            if(!root.check(matrixPane.model.matrix.length===16,
                "MISSING_4x4_CELLS"))return;
            if(!root.check(matrixPane.countFor("sun","moon")==="1"&&
                matrixPane.countFor("venus","mercury")==="0",
                "SOURCE_CELL_COUNTS_INVALID"))return;
            if(!root.check(matrixPane.eventPage.total===2,
                "EVENTS_MISSING"))return;
            matrixPane.selectPair("sun","moon");
            if(!root.check(matrixPane.eventPage.total===1 &&
                matrixPane.eventPage.items[0].natal_body==="sun",
                "CELL_FILTER_NOT_BOUND"))return;
            matrixPane.selectPair("sun","moon");
            if(!root.check(matrixPane.eventPage.total===2,
                "CELL_FILTER_TOGGLE_FAILED"))return;
            matrixPane.filterKind="station";
            if(!root.check(matrixPane.eventPage.total===1 &&
                matrixPane.eventPage.items[0].natal_body===null,
                "STATION_DUPLICATED_OR_MISATTRIBUTED"))return;
            matrixPane.chooseEvent(matrixPane.model.events[1]);
            if(!root.check(root.chosenKind==="station" &&
                root.chosenNatal==="sun"&&root.chosenMoving==="mercury",
                "STATION_WHEEL_REFERENCE_WRONG"))return;
            matrixPane.filterKind="ALL";
            matrixPane.chooseEvent(matrixPane.model.events[0]);
            if(!root.check(root.chosenKind==="aspect"&&
                root.chosenNatal==="sun"&&root.chosenMoving==="moon"&&
                root.chosenUtc==="2026-11-07T03:12:36Z",
                "EXACT_PAIR_WHEEL_EVENT_WRONG"))return;
            if(!root.check(Matrix.nearestMinute(root.chosenUtc)===
                "2026-11-07T03:13:00Z","MINUTE_ROUNDING_FAILED"))return;
            root.complete=true;
            console.log("M8L_NATIVE_PASS // FOUR_BY_FOUR_FIT_RANGE_AND_WHEEL");
            Qt.quit();
        }
    }
    Timer {
        interval:9000;running:true;repeat:false
        onTriggered:root.fail("TIMEOUT")
    }
}
