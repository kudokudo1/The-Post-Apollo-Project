.pragma library

// M28-B. Compact EARTH map companion from EXISTING EONET event records.
// The entire EONET list remains under EARTH → EVENTS → EONET.
// No news fetch, no event merge, no writer, and no invented coordinates.
var FORMAT = "post-apollo.weather.earth-map-companion.m28b.v1";

function validPoint(row) {
    if (!row || typeof row !== "object") return false;
    var lat=Number(row.latitude), lon=Number(row.longitude);
    return row.latitude !== null && row.longitude !== null
      && isFinite(lat) && isFinite(lon)
      && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}
function within(row, bounds) {
    if (!bounds || !bounds.valid) return true;
    var lat=Number(row.latitude), lon=Number(row.longitude);
    return lat >= bounds.south && lat <= bounds.north
        && lon >= bounds.west && lon <= bounds.east;
}
function previewEonet(rows, selected, bounds, maxCount) {
    var pool=Array.isArray(rows) ? rows.filter(validPoint) : [];
    var count=Number(maxCount);
    count=isFinite(count) ? Math.max(1,Math.min(8,Math.floor(count))) : 4;
    var current=pool.filter(function(row){return within(row,bounds);});
    var wanted=selected && typeof selected.id === "string" ? selected.id : "";
    var preview=[], seen={};
    if(wanted) {
        for(var i=0;i<pool.length;i++) {
            if(pool[i].id === wanted) {
                preview.push(pool[i]); seen[wanted]=true; break;
            }
        }
    }
    for(var j=0;j<current.length && preview.length<count;j++) {
        var row=current[j],key=String(row.id || "");
        if(key && seen[key]) continue;
        preview.push(row);
        if(key)seen[key]=true;
    }
    return preview;
}
