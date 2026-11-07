.pragma library
// MAGICK M8c // Read-only, source-bound natal/transit comparison.
// Reuses complete M8b chart objects for BOTH epochs: no second data provider,
// guessed planet positions, exact-contact claims, or birth-record persistence.
var FORMAT="post-apollo.weather.magick-transit-comparison.m8c.v1";
var TARGETS=["sun","moon","mercury","venus","mars_barycenter",
    "jupiter_barycenter","saturn_barycenter","uranus_barycenter",
    "neptune_barycenter","pluto_barycenter"];
var NAIF={sun:10,moon:301,mercury:199,venus:299,mars_barycenter:4,
    jupiter_barycenter:5,saturn_barycenter:6,uranus_barycenter:7,
    neptune_barycenter:8,pluto_barycenter:9};
var ASPECTS=[
    {id:"conjunction",degrees:0},
    {id:"sextile",degrees:60},
    {id:"square",degrees:90},
    {id:"trine",degrees:120},
    {id:"opposition",degrees:180}
];
function fail(reason){return {ready:false,reason:reason||"CALCULATE NATAL AND TRANSIT",
    natal:[],transit:[],aspects:[],deltas:[],source:null};}
function utc(text){
    if(typeof text!=="string" ||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$/.test(text))return "";
    var ms=Date.parse(text);
    if(!isFinite(ms))return "";
    var result=new Date(ms).toISOString();
    var year=new Date(ms).getUTCFullYear();
    return result===text.replace("Z",".000Z")&&year>=1901&&year<=2099?text:"";
}
function degree(a){return typeof a==="number"&&isFinite(a)&&a>=0&&a<360;}
function separation(a,b){var d=Math.abs(a-b)%360;return Math.min(d,360-d);}
function signedDelta(from,to){return ((to-from+540)%360)-180;}
function makeDraft(natal,epoch){
    if(!natal || natal.format!=="post-apollo.weather.magick-natal-chart.m8a.v1"||
       natal.zodiac!=="tropical"||!["whole-sign","equal"].includes(natal.house_system)||
       natal.origin!=="topocentric"||natal.position_model!=="apparent"||
       natal.frame!=="true-ecliptic-of-date"||
       !natal.provenance ||
       !/^[0-9a-f]{64}$/i.test(String(natal.provenance.ephemeris_sha256||""))||
       !natal.observer || natal.observer.elevation_m!==0 ||
       typeof natal.observer.latitude_deg!=="number"||
       !isFinite(natal.observer.latitude_deg)||
       natal.observer.latitude_deg < -90||natal.observer.latitude_deg>90||
       typeof natal.observer.longitude_deg!=="number"||
       !isFinite(natal.observer.longitude_deg)||
       natal.observer.longitude_deg < -180||natal.observer.longitude_deg>180||
       !utc(epoch))return null;
    return {valid:true,sessionOnly:true,eventUtc:epoch,
        latitude:natal.observer.latitude_deg,longitude:natal.observer.longitude_deg,
        zodiac:"tropical",houseSystem:natal.house_system};
}
function verifyRaw(n,t){
    if(!n||!t||n.format!=="post-apollo.weather.magick-natal-chart.m8a.v1"||
       t.format!==n.format || n.origin!=="topocentric"||t.origin!==n.origin||
       n.position_model!=="apparent"||t.position_model!==n.position_model||
       n.frame!=="true-ecliptic-of-date"||t.frame!==n.frame||
       n.zodiac!=="tropical"||t.zodiac!==n.zodiac ||
       n.house_system!==t.house_system ||
       !n.observer||!t.observer||!n.provenance||!t.provenance||
       n.observer.elevation_m!==0||t.observer.elevation_m!==0||
       n.observer.latitude_deg!==t.observer.latitude_deg||
       n.observer.longitude_deg!==t.observer.longitude_deg||
       n.provenance.engine!=="skyfield"||t.provenance.engine!=="skyfield"||
       !/^[0-9a-f]{64}$/i.test(String(n.provenance.ephemeris_sha256||""))||
       n.provenance.ephemeris_sha256.toLowerCase()!==
           String(t.provenance.ephemeris_sha256||"").toLowerCase()||
       n.provenance.house_method!=="true-equinox-horizon-meridian-geometric"||
       t.provenance.house_method!==n.provenance.house_method)return false;
    return true;
}
function build(natalModel,transitModel,natalRaw,transitRaw,expectedUtc,orb){
    if(!natalModel||!transitModel||!natalModel.ready||!transitModel.ready ||
       !utc(expectedUtc)||transitRaw.epoch_utc!==expectedUtc||
       natalRaw.epoch_utc!==natalModel.epoch_utc||
       transitRaw.epoch_utc!==transitModel.epoch_utc||
       !verifyRaw(natalRaw,transitRaw))
        return fail("MATCHED JPL NATAL AND TRANSIT SOURCES REQUIRED");
    if(typeof orb!=="number"||!isFinite(orb)||orb<0.5||orb>6)
        return fail("ASPECT ORB OUTSIDE 0.5..6 DEGREES");
    var a=natalModel.planets,b=transitModel.planets;
    if(a.length!==10||b.length!==10)return fail("INCOMPLETE TARGET LIST");
    for(var i=0;i<10;i++)
        if(a[i].id!==TARGETS[i]||b[i].id!==TARGETS[i]||
           a[i].naif_id!==NAIF[TARGETS[i]]||b[i].naif_id!==NAIF[TARGETS[i]]||
           !degree(a[i].longitude_deg)||!degree(b[i].longitude_deg))
            return fail("TARGET IDENTIFICATION OR LONGITUDE INVALID");
    var aspects=[];
    for(var i=0;i<b.length;i++)for(var j=0;j<a.length;j++){
        var s=separation(b[i].longitude_deg,a[j].longitude_deg);
        for(var k=0;k<ASPECTS.length;k++){
            var d=Math.abs(s-ASPECTS[k].degrees);
            if(d<=orb){
                aspects.push({transit_id:b[i].id,natal_id:a[j].id,
                    name:ASPECTS[k].id,exact_target_deg:ASPECTS[k].degrees,
                    separation_deg:s,orb_deg:d});
                break;
            }
        }
    }
    aspects.sort(function(x,y){
        return x.orb_deg-y.orb_deg||
            x.transit_id.localeCompare(y.transit_id)||
            x.natal_id.localeCompare(y.natal_id);
    });
    var deltas=a.map(function(p,i){
        return {id:p.id,natal_deg:p.longitude_deg,
            transit_deg:b[i].longitude_deg,
            signed_delta_deg:signedDelta(p.longitude_deg,b[i].longitude_deg)};
    });
    return {ready:true,reason:"",format:FORMAT,
        natal_epoch_utc:natalModel.epoch_utc,transit_epoch_utc:expectedUtc,
        frame:"true-ecliptic-of-date",observer:natalRaw.observer,
        source:{engine:"skyfield",ephemeris_sha256:natalRaw.provenance.ephemeris_sha256},
        orb_deg:orb,natal:a,transit:b,aspects:aspects,deltas:deltas,
        limitations:{
            aspects_are_interpretive_angular_tolerances:true,
            exact_aspect_event_time_calculated:false,
            moving_planets_are_topocentric_at_natal_location:true,
            longitudes_use_separate_epochs_of_true_equinox_of_date:true
        }};
}
