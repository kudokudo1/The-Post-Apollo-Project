.pragma library
// MAGICK M8d // UTC date shortcut and read-only Post-Apollo HOME fallback.
// We do NOT infer GPS from an IP, provider's weather coordinates or Explore.
// Manual entries remain authoritative; no merging half-manual coordinate pairs.
function utcClock(date) {
    var raw=date===undefined ? new Date() : date;
    if(!raw||typeof raw.getTime!=="function"||!isFinite(raw.getTime()))
        return null;
    var iso=raw.toISOString();
    var year=Number(iso.slice(0,4));
    if(year<1901||year>2099)return null;
    return {date:iso.slice(0,10),time:iso.slice(11,16)};
}
function utcDay(date) {
    var v=utcClock(date);
    return v?v.date:"";
}
function utcTime(date) {
    var v=utcClock(date);
    return v?v.time:"";
}
function safeHome(place) {
    if(!place||typeof place!=="object"||Array.isArray(place)||
       place.source!=="MANUAL"||typeof place.label!=="string"||
       place.label.trim()===""||
       typeof place.latitude!=="number"||
       typeof place.longitude!=="number"||
       !isFinite(place.latitude)||!isFinite(place.longitude)||
       place.latitude< -90||place.latitude>90||
       place.longitude< -180||place.longitude>180)return null;
    return {latitude:place.latitude,longitude:place.longitude,
        label:place.label.trim()};
}
function coordString(number) {
    return String(Number(number.toFixed(6)));
}
function location(latitudeText,longitudeText,homePlace){
    var a=String(latitudeText===null||latitudeText===undefined
                 ?"":latitudeText).trim();
    var b=String(longitudeText===null||longitudeText===undefined
                 ?"":longitudeText).trim();
    if(a!==""||b!==""){
        if(a===""||b==="")return {ready:false,source:"INCOMPLETE",
            latitude:"",longitude:"",label:"ENTER BOTH COORDINATES"};
        // Preserve typed invalid values for the existing Setup validator.
        // Never replace them with Home, since that could hide a typo.
        return {ready:true,source:"MANUAL",latitude:a,longitude:b,
            label:"MANUAL COORDINATES"};
    }
    var home=safeHome(homePlace);
    if(home)return {ready:true,source:"HOME",latitude:coordString(home.latitude),
        longitude:coordString(home.longitude),
        label:"POST-APOLLO HOME // "+home.label};
    return {ready:false,source:"UNAVAILABLE",latitude:"",longitude:"",
        label:"HOME UNSET // ENTER BOTH COORDINATES"};
}
