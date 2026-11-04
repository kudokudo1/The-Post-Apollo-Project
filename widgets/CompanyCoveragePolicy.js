.pragma library

// Company Network geography is a public reference directory, not a company
// service-availability feed. Capital coordinates are approximate map markers,
// NOT legal coverage boundaries or service-area centroids.
var states = [
    ["AL","Alabama","Montgomery",-86.300,32.379,"lower48"],
    ["AK","Alaska","Juneau",-134.419,58.301,"alaska"],
    ["AZ","Arizona","Phoenix",-112.074,33.448,"lower48"],
    ["AR","Arkansas","Little Rock",-92.289,34.746,"lower48"],
    ["CA","California","Sacramento",-121.494,38.581,"lower48"],
    ["CO","Colorado","Denver",-104.990,39.739,"lower48"],
    ["CT","Connecticut","Hartford",-72.673,41.765,"lower48"],
    ["DE","Delaware","Dover",-75.524,39.158,"lower48"],
    ["DC","District of Columbia","Washington",-77.037,38.907,"lower48"],
    ["FL","Florida","Tallahassee",-84.280,30.439,"lower48"],
    ["GA","Georgia","Atlanta",-84.388,33.749,"lower48"],
    ["HI","Hawaii","Honolulu",-157.858,21.309,"hawaii"],
    ["ID","Idaho","Boise",-116.202,43.615,"lower48"],
    ["IL","Illinois","Springfield",-89.650,39.781,"lower48"],
    ["IN","Indiana","Indianapolis",-86.158,39.768,"lower48"],
    ["IA","Iowa","Des Moines",-93.625,41.586,"lower48"],
    ["KS","Kansas","Topeka",-95.678,39.047,"lower48"],
    ["KY","Kentucky","Frankfort",-84.873,38.200,"lower48"],
    ["LA","Louisiana","Baton Rouge",-91.140,30.451,"lower48"],
    ["ME","Maine","Augusta",-69.780,44.311,"lower48"],
    ["MD","Maryland","Annapolis",-76.492,38.979,"lower48"],
    ["MA","Massachusetts","Boston",-71.059,42.360,"lower48"],
    ["MI","Michigan","Lansing",-84.556,42.732,"lower48"],
    ["MN","Minnesota","Saint Paul",-93.090,44.953,"lower48"],
    ["MS","Mississippi","Jackson",-90.185,32.299,"lower48"],
    ["MO","Missouri","Jefferson City",-92.174,38.577,"lower48"],
    ["MT","Montana","Helena",-112.040,46.588,"lower48"],
    ["NE","Nebraska","Lincoln",-96.702,40.813,"lower48"],
    ["NV","Nevada","Carson City",-119.767,39.163,"lower48"],
    ["NH","New Hampshire","Concord",-71.537,43.208,"lower48"],
    ["NJ","New Jersey","Trenton",-74.742,40.217,"lower48"],
    ["NM","New Mexico","Santa Fe",-105.937,35.687,"lower48"],
    ["NY","New York","Albany",-73.756,42.652,"lower48"],
    ["NC","North Carolina","Raleigh",-78.638,35.780,"lower48"],
    ["ND","North Dakota","Bismarck",-100.783,46.808,"lower48"],
    ["OH","Ohio","Columbus",-82.999,39.961,"lower48"],
    ["OK","Oklahoma","Oklahoma City",-97.516,35.468,"lower48"],
    ["OR","Oregon","Salem",-123.036,44.942,"lower48"],
    ["PA","Pennsylvania","Harrisburg",-76.886,40.273,"lower48"],
    ["RI","Rhode Island","Providence",-71.412,41.824,"lower48"],
    ["SC","South Carolina","Columbia",-81.034,34.000,"lower48"],
    ["SD","South Dakota","Pierre",-100.351,44.368,"lower48"],
    ["TN","Tennessee","Nashville",-86.781,36.162,"lower48"],
    ["TX","Texas","Austin",-97.743,30.267,"lower48"],
    ["UT","Utah","Salt Lake City",-111.891,40.761,"lower48"],
    ["VT","Vermont","Montpelier",-72.575,44.260,"lower48"],
    ["VA","Virginia","Richmond",-77.437,37.541,"lower48"],
    ["WA","Washington","Olympia",-122.901,47.037,"lower48"],
    ["WV","West Virginia","Charleston",-81.633,38.349,"lower48"],
    ["WI","Wisconsin","Madison",-89.400,43.073,"lower48"],
    ["WY","Wyoming","Cheyenne",-104.820,41.140,"lower48"]
];

var regions = {
    lower48: {label:"LOWER 48 + DC",west:-126,east:-66,south:24,north:50},
    alaska: {label:"ALASKA",west:-171,east:-129,south:51,north:72},
    hawaii: {label:"HAWAII",west:-162,east:-154,south:18,north:23}
};
var serviceFamilies = [
    "ALL SERVICES", "BENEFITS", "HEALTHCARE", "EDUCATION",
    "EMPLOYMENT", "REINTEGRATION", "HOUSING"
];
var statusFilters = ["ALL STATUS", "ACTIVE", "PARTNER", "PLANNED"];

function regionKey(value) {
    return Object.prototype.hasOwnProperty.call(regions, value) ? value : "lower48";
}

function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
}

function defaultView(region) {
    var bounds = regions[regionKey(region)];
    return {zoom:1, centerLon:(bounds.west + bounds.east)/2,
            centerLat:(bounds.south + bounds.north)/2};
}

function view(region, zoom, centerLon, centerLat) {
    var bounds = regions[regionKey(region)];
    var z = Number(zoom);
    z = isFinite(z) ? clamp(z, 1, 6) : 1;
    var base = defaultView(region);
    var lon = Number(centerLon);
    var lat = Number(centerLat);
    lon = isFinite(lon) ? lon : base.centerLon;
    lat = isFinite(lat) ? lat : base.centerLat;
    var halfLon = (bounds.east - bounds.west) / (2 * z);
    var halfLat = (bounds.north - bounds.south) / (2 * z);
    return {
        zoom:z,
        centerLon:clamp(lon, bounds.west + halfLon, bounds.east - halfLon),
        centerLat:clamp(lat, bounds.south + halfLat, bounds.north - halfLat)
    };
}

function project(lon, lat, width, height, region, zoom, centerLon, centerLat) {
    var bounds = regions[regionKey(region)];
    var current = view(region, zoom, centerLon, centerLat);
    var w = Number(width), h = Number(height);
    if (!isFinite(w) || !isFinite(h) || w <= 0 || h <= 0)
        return {valid:false,x:0,y:0,visible:false};
    var x = w * (0.5 + (Number(lon) - current.centerLon)
        / (bounds.east - bounds.west) * current.zoom);
    var y = h * (0.5 - (Number(lat) - current.centerLat)
        / (bounds.north - bounds.south) * current.zoom);
    return {valid:isFinite(x) && isFinite(y),x:x,y:y,
            visible:x >= 0 && x <= w && y >= 0 && y <= h};
}

function unproject(x,y,width,height,region,zoom,centerLon,centerLat) {
    var bounds = regions[regionKey(region)];
    var current = view(region,zoom,centerLon,centerLat);
    var w = Number(width), h = Number(height);
    if (!(w > 0 && h > 0)) return null;
    return {
        lon:current.centerLon + (x/w - 0.5) * (bounds.east-bounds.west)/current.zoom,
        lat:current.centerLat - (y/h - 0.5) * (bounds.north-bounds.south)/current.zoom
    };
}

function pan(region,zoom,centerLon,centerLat,dx,dy,width,height) {
    var bounds = regions[regionKey(region)];
    var current = view(region,zoom,centerLon,centerLat);
    if (!(width > 0 && height > 0)) return current;
    return view(region, current.zoom,
        current.centerLon - Number(dx)/width * (bounds.east-bounds.west)/current.zoom,
        current.centerLat + Number(dy)/height * (bounds.north-bounds.south)/current.zoom);
}

function zoomAt(region,zoom,centerLon,centerLat,x,y,width,height,direction) {
    var current = view(region,zoom,centerLon,centerLat);
    var before = unproject(x,y,width,height,region,current.zoom,
                           current.centerLon,current.centerLat);
    if (!before) return current;
    var factor = direction > 0 ? 1.25 : direction < 0 ? 0.8 : 1;
    var nextZoom = clamp(current.zoom * factor,1,6);
    var bounds = regions[regionKey(region)];
    // Preserve coordinate under cursor, clamped to the selected region.
    var lon = before.lon - (x/width - 0.5) * (bounds.east-bounds.west)/nextZoom;
    var lat = before.lat + (y/height - 0.5) * (bounds.north-bounds.south)/nextZoom;
    return view(region,nextZoom,lon,lat);
}

function stateForCode(code) {
    for (var i=0;i<states.length;i++) {
        if (states[i][0] === code) return states[i];
    }
    return null;
}

function visibleStates(region,query) {
    var key=regionKey(region);
    var term=String(query || "").toLowerCase().trim();
    return states.filter(function(row) {
        return row[5] === key && (!term || row[0].toLowerCase().indexOf(term)>=0
            || row[1].toLowerCase().indexOf(term)>=0
            || row[2].toLowerCase().indexOf(term)>=0);
    });
}

function nearestState(region,x,y,width,height,zoom,centerLon,centerLat,radius) {
    var list=visibleStates(region,""), best=null, smallest=Number(radius)*Number(radius);
    for (var i=0;i<list.length;i++) {
        var p=project(list[i][3],list[i][4],width,height,region,zoom,centerLon,centerLat);
        if (!p.visible) continue;
        var d=(p.x-x)*(p.x-x) + (p.y-y)*(p.y-y);
        if (d<=smallest) {smallest=d;best=list[i];}
    }
    return best;
}
