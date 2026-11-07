.pragma library

// COSMOS C5 // Shared presentation routing. A subject owns several one-screen
// modes; mode changes never move the user's scroll offset. Pure metadata only.
var MODES = {
    sun: [
        {label:"OBSERVATION", route:"cosmos/sun/observation", kind:"sun-observation"},
        {label:"ACTIVITY", route:"cosmos/sun/activity", kind:"sun-activity"},
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
    "cosmos/events/overview":"cosmos/events/meteors"
};

// Existing deep links remain valid specialist inspectors. They are not
// shown as separate tabs on the new four-mode terminal rail.
var LEGACY_SUN = {
    "cosmos/sun/live":"sun-live",
    "cosmos/sun/position":"sun-position",
    "cosmos/sun/twilight":"light",
    "cosmos/sun/suvi":"solar-section",
    "cosmos/sun/xray":"solar-section",
    "cosmos/sun/flares":"solar-section",
    "cosmos/sun/cycle":"solar-section"
};

function canonical(path) {
    return Object.prototype.hasOwnProperty.call(ALIASES,path)
        ? ALIASES[path] : path;
}

function family(path) {
    var route = canonical(path);
    if (Object.prototype.hasOwnProperty.call(LEGACY_SUN,route))
        return "sun";
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
    if (Object.prototype.hasOwnProperty.call(LEGACY_SUN,route))
        return LEGACY_SUN[route];
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
        || (key === "sun" && (kind(path)==="sun-observation"
            || kind(path)==="sun-position" || kind(path)==="solar-path"
            || kind(path)==="light"));
}

function usesInnerScroll(path) {
    // Only the IAU catalogue uses bounded scrolling by default.
    return kind(path) === "meteors";
}

function fullRoute(path) {
    return family(path) === "sun"
         ? "cosmos/space-weather/full" : "cosmos/sky/full";
}
