.pragma library

// M8a // Natal chart renderer contract, NOT a natal calculation engine.
// A selected JPL pair is not a full chart. No synthetic planet placements,
// guessed houses, sidereal offsets or interpretive aspects.
var FORMAT="post-apollo.weather.magick-natal-chart.m8a.v1";
var SIGNS=["ARIES","TAURUS","GEMINI","CANCER","LEO","VIRGO",
           "LIBRA","SCORPIO","SAGITTARIUS","CAPRICORN","AQUARIUS","PISCES"];
var TARGETS=["sun","moon","mercury","venus","mars_barycenter",
             "jupiter_barycenter","saturn_barycenter",
             "uranus_barycenter","neptune_barycenter","pluto_barycenter"];
function fail(reason){return {ready:false,reason:reason||"FULL NATAL SOURCE NOT CONNECTED",
    planets:[],cusps:[],aspects:[],ascendant_deg:null,mc_deg:null};}
function degree(x){return typeof x==="number"&&isFinite(x)&&x>=0&&x<360;}
function canonicalAngle(lon,asc){return Math.PI-2*Math.PI*((lon-asc+360)%360)/360;}
function point(lon,asc,r){var a=canonicalAngle(lon,asc);
    return {x:r*Math.cos(a),y:r*Math.sin(a)};}
function separation(a,b){var d=Math.abs(a-b)%360;return Math.min(d,360-d);}
function derivedAspects(planets,orb){
    if(!Array.isArray(planets)||typeof orb!=="number"||orb<0||orb>8)return [];
    var families=[{name:"conjunction",degrees:0},{name:"sextile",degrees:60},
        {name:"square",degrees:90},{name:"trine",degrees:120},
        {name:"opposition",degrees:180}];
    var out=[];
    for(var i=0;i<planets.length;i++)for(var j=i+1;j<planets.length;j++){
        var d=separation(planets[i].longitude_deg,planets[j].longitude_deg);
        for(var k=0;k<families.length;k++){
            if(Math.abs(d-families[k].degrees)<=orb){
                out.push({a:planets[i].id,b:planets[j].id,name:families[k].name,
                    actual_deg:d,orb_deg:Math.abs(d-families[k].degrees)});
                break;
            }
        }
    }
    return out;
}
function validate(payload){
    if(!payload||payload.format!==FORMAT||payload.epoch_utc===undefined||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(payload.epoch_utc)||
       !payload.provenance||payload.provenance.engine!=="skyfield"||
       !/^[0-9a-f]{64}$/i.test(String(payload.provenance.ephemeris_sha256||""))||
       payload.origin!=="topocentric"||
       payload.frame!=="true-ecliptic-of-date"||
       !["tropical","sidereal"].includes(payload.zodiac)||
       !["whole-sign","equal"].includes(payload.house_system)||
       !Array.isArray(payload.positions)||payload.positions.length!==TARGETS.length||
       !Array.isArray(payload.house_cusps_deg)||payload.house_cusps_deg.length!==12||
       !degree(payload.ascendant_deg)||!degree(payload.mc_deg))
       return fail("COMPLETE VERIFIED TOPoCENTRIC CHART REQUIRED");
    if(payload.zodiac==="sidereal" && (typeof payload.ayanamsa_id!=="string"||
        payload.ayanamsa_id.trim()===""))return fail("SIDEREAL REFERENCE REQUIRED");
    var planetNames={};
    for(var i=0;i<payload.positions.length;i++){
        var p=payload.positions[i];
        if(!p||TARGETS.indexOf(p.id)<0||planetNames[p.id]||
           !degree(p.longitude_deg)||!Number.isInteger(p.naif_id))
           return fail("MISSING/UNVERIFIED PLANETARY PLACEMENTS");
        planetNames[p.id]=true;
    }
    for(var j=0;j<TARGETS.length;j++)if(!planetNames[TARGETS[j]])
        return fail("PLANETARY TARGET MISSING");
    for(var k=0;k<12;k++)if(!degree(payload.house_cusps_deg[k]))
        return fail("UNVERIFIED HOUSE CUSPS");
    var asc=payload.ascendant_deg,cusps=payload.house_cusps_deg;
    // Whole-sign and equal houses follow distinct, checkable definitions.
    if(payload.house_system==="whole-sign"){
        var start=Math.floor(asc/30)*30;
        for(var k=0;k<12;k++)
            if(Math.abs(cusps[k]-(start+30*k)%360)>0.001)
                return fail("WHOLE-SIGN CUSPS INCONSISTENT");
    } else {
        for(var k=0;k<12;k++)
            if(Math.abs(cusps[k]-(asc+30*k)%360)>0.001)
                return fail("EQUAL-HOUSE CUSPS INCONSISTENT");
    }
    var ordered=TARGETS.map(function(id){
        return payload.positions.find(function(p){return p.id===id;});
    });
    return {ready:true,reason:"",format:FORMAT,epoch_utc:payload.epoch_utc,
        origin:payload.origin,zodiac:payload.zodiac,house_system:payload.house_system,
        provenance:payload.provenance,ascendant_deg:asc,mc_deg:payload.mc_deg,
        cusps:cusps.slice(),planets:ordered,aspects:derivedAspects(ordered,6)};
}
