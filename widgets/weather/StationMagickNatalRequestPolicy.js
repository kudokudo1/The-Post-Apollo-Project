.pragma library

// M8b // Validate a single ephemeral UTC natal request before process launch.
// Explicit coordinates and time ONLY; never infer from the host or browser.
var FORMAT="post-apollo.weather.magick-natal-request.m8b.v1";
function fromDraft(draft) {
    if(!draft||draft.valid!==true||draft.sessionOnly!==true||
       draft.zodiac!=="tropical"||
       ["whole-sign","equal"].indexOf(draft.houseSystem)<0 ||
       typeof draft.eventUtc!=="string"||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$/.test(draft.eventUtc)||
       !isFinite(draft.latitude)||!isFinite(draft.longitude)||
       draft.latitude<-90||draft.latitude>90||
       draft.longitude<-180||draft.longitude>180)return null;
    return {format:FORMAT,epoch_utc:draft.eventUtc,
        latitude_deg:draft.latitude,longitude_deg:draft.longitude,
        zodiac:"tropical",house_system:draft.houseSystem};
}
function matches(result,request) {
    if(!result||!request||result.epoch_utc!==request.epoch_utc||
       result.zodiac!==request.zodiac||
       result.house_system!==request.house_system||
       result.position_model!=="apparent"||
       result.origin!=="topocentric"||
       result.frame!=="true-ecliptic-of-date"||
       !result.observer ||
       result.observer.elevation_m!==0 ||
       result.observer.latitude_deg!==request.latitude_deg||
       result.observer.longitude_deg!==request.longitude_deg||
       !result.provenance ||
       result.provenance.house_method!==
         "true-equinox-horizon-meridian-geometric")return false;
    return true;
}
