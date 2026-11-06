.pragma library

// COSMOS C5 // Shared presentation routing. A subject owns several one-screen
// modes; mode changes never move the user's scroll offset. Pure metadata only.
var MODES = {
    sun: [
        {label:"PATH", route:"cosmos/sun/position", kind:"solar-path"},
        {label:"LIGHT", route:"cosmos/sun/twilight", kind:"light"},
        {label:"SUVI", route:"cosmos/sun/suvi", kind:"solar-section"},
        {label:"X-RAY", route:"cosmos/sun/xray", kind:"solar-section"},
        {label:"FLARES", route:"cosmos/sun/flares", kind:"solar-section"},
        {label:"CYCLE", route:"cosmos/sun/cycle", kind:"solar-section"},
        {label:"YEAR", route:"cosmos/sun/year", kind:"annual-solar"}
    ],
    astronomy: [
        {label:"CLOCK", route:"cosmos/planets-stars/planet-clock", kind:"planet-clock"},
        {label:"PLANETS", route:"cosmos/planets-stars/celestial-fix", kind:"planets"},
        {label:"STARS", route:"cosmos/planets-stars/constellations", kind:"stars"}
    ],
    events: [
        {label:"METEORS", route:"cosmos/events/meteors", kind:"meteors"},
        {label:"ECLIPSES", route:"cosmos/events/eclipses", kind:"eclipses"},
        {label:"ISS", route:"cosmos/events/iss", kind:"iss"}
    ]
};

var ALIASES = {
    "cosmos/sun/photo-light":"cosmos/sun/twilight",
    "cosmos/sun/activity":"cosmos/sun/suvi",
    "cosmos/events/overview":"cosmos/events/meteors"
};

function canonical(path) {
    return Object.prototype.hasOwnProperty.call(ALIASES,path)
        ? ALIASES[path] : path;
}

function family(path) {
    var route = canonical(path);
    for (var key in MODES) {
        if (!Object.prototype.hasOwnProperty.call(MODES,key))
            continue;
        if (MODES[key].some(function(mode) { return mode.route === route; }))
            return key;
    }
    return "";
}

function modesFor(path) {
    var key = family(path);
    return key !== "" ? MODES[key] : [];
}

function kind(path) {
    var route = canonical(path);
    var modes = modesFor(route);
    for (var i=0;i<modes.length;i++)
        if (modes[i].route === route) return modes[i].kind;
    return "";
}

function dataRoute(path) {
    var route = canonical(path);
    if (route === "cosmos/planets-stars/constellations")
        return route;
    return route;
}

function usesSky(path) {
    var key = family(path);
    return key === "astronomy" || key === "events"
        || (key === "sun" && kind(path) !== "solar-section"
            && kind(path) !== "annual-solar");
}

function usesInnerScroll(path) {
    // Only the IAU catalogue uses bounded scrolling by default.
    return kind(path) === "meteors";
}

function fullRoute(path) {
    return family(path) === "sun"
         ? "cosmos/space-weather/full" : "cosmos/sky/full";
}
