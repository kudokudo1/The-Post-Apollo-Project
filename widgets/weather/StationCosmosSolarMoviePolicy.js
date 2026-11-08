.pragma library

// C36 // NASA SDO AIA 512px latest published 48-hour MOVIES.
// These are compressed sequences of observations, NOT live video or NOAA SUVI.
// URL selection is a fixed NASA allowlist, never arbitrary web/host input.
var FORMAT = "post-apollo.weather.cosmos-sdo-solar-movies.c36.v1";
var BASE = "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/";
var CHANNELS = [
    {id:"171",label:"171 Å",file:"latest_512_0171.mp4",desc:"AIA 171 Å"},
    {id:"193",label:"193 Å",file:"latest_512_0193.mp4",desc:"AIA 193 Å"},
    {id:"304",label:"304 Å",file:"latest_512_0304.mp4",desc:"AIA 304 Å"}
];
function byId(id) {
    if (typeof id !== "string") return null;
    for(var i=0;i<CHANNELS.length;i++)
        if(CHANNELS[i].id===id)return CHANNELS[i];
    return null;
}
function url(id) {
    var row=byId(id);
    return row ? BASE+row.file : "";
}
function positionFraction(position,duration) {
    if(typeof position!=="number" || typeof duration!=="number"
      || !isFinite(position)||!isFinite(duration)||duration<=0)
        return 0;
    return Math.max(0,Math.min(1,position/duration));
}
function seekPosition(fraction,duration) {
    if(typeof fraction!=="number" || typeof duration!=="number"
      || !isFinite(fraction)||!isFinite(duration)||duration<=0)
        return null;
    return Math.round(Math.max(0,Math.min(1,fraction))*duration);
}
