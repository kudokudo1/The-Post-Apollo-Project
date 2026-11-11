.pragma library

// W1 // AppControl-style workspace routes over the existing six subject trees.
// Only navigation and HOME section focus. No providers, write APIs or actors.
var FORMAT = "post-apollo.weather.workspace-navigation.w1.v1";
var FAMILIES = [
    {id:"home",label:"HOME",landing:"home/overview"},
    {id:"weather",label:"WEATHER",landing:"weather/overview"},
    {id:"cosmos",label:"COSMOS",landing:"cosmos/overview"},
    {id:"earth",label:"EARTH",landing:"earth/overview"},
    {id:"media",label:"MEDIA",landing:"media/overview"},
    {id:"magick",label:"MAGICK",landing:"magick/overview"},
    {id:"tools",label:"TOOLS",landing:"tools/overview"}
];
var GROUPS = {
    home:[
        {label:"OVERVIEW",path:"home/overview",key:"overview"},
        {label:"AUTO",path:"home/auto",key:"auto"},
        {label:"QUICK",path:"home/quick",key:"quick"},
        {label:"SNAPSHOT",path:"home/snapshot",key:"snapshot"},
        {label:"HISTORY",path:"home/history",key:"history"},
        {label:"MAGICK",path:"home/magick",key:"magick"},
        {label:"SERVICES",path:"home/health",key:"sources"}
    ],
    weather:[
        {label:"OVERVIEW",path:"weather/overview",key:"overview"},
        {label:"WEATHER",path:"weather/conditions/current",key:"conditions"},
        {label:"HAZARDS",path:"weather/hazards/alerts",key:"hazards"},
        {label:"HISTORY",path:"weather/history/historical-forecast",key:"history"},
        {label:"SERVICES",path:"weather/services/health",key:"services"}
    ],
    cosmos:[
        {label:"OVERVIEW",path:"cosmos/overview",key:"overview"},
        {label:"SUN",path:"cosmos/sun/position",key:"sun"},
        {label:"MOON",path:"cosmos/moon/ephemeris",key:"moon"},
        // Observatory only: terrestrial weather belongs to WEATHER.
        {label:"ASTRONOMY",path:"cosmos/planets-stars/celestial-fix",key:"sky"},
        {label:"EVENTS",path:"cosmos/events/overview",key:"events"},
        {label:"SERVICES",path:"cosmos/space-weather/overview",key:"space-weather"}
    ],
    earth:[
        {label:"OVERVIEW",path:"earth/overview",key:"overview"},
        {label:"MAP / EVENTS",path:"earth/maps/events",key:"map"},
        {label:"WATER",path:"earth/water/rivers",key:"water"},
        {label:"GROUND",path:"earth/ground/full",key:"ground"},
        {label:"SERVICES",path:"earth/services/health",key:"services"}
    ],
    media:[
        {label:"OVERVIEW",path:"media/overview",key:"overview"},
        {label:"NEWS // ALL",path:"media/news/full",key:"news"},
        {label:"WATCH",path:"media/watch/live",key:"watch"},
        {label:"RADIO // ALL",path:"media/radio/full",key:"radio"},
        {label:"CREATORS",path:"media/creators/saved",key:"creators"},
        {label:"SERVICES",path:"media/services/health",key:"services"}
    ],
    magick:[
        {label:"OVERVIEW",path:"magick/overview",key:"overview"},
        {label:"LUNAR + SOLAR",path:"magick/lunar-solar/moon",key:"lunar-solar"},
        {label:"LENSES",path:"magick/planetary/correspondences",key:"lenses"},
        {label:"ASTROLOGY",path:"magick/astrology/charts",key:"astrology"},
        {label:"DIVINATION",path:"magick/divination/tarot",key:"divination"},
        {label:"GRIMOIRE",path:"magick/grimoire/references",key:"grimoire"},
        {label:"SERVICES",path:"magick/services/health",key:"services"}
    ],
    tools:[
        {label:"OVERVIEW",path:"tools/overview",key:"overview"},
        {label:"SOURCES",path:"tools/sources/health",key:"sources"},
        {label:"STORAGE",path:"tools/storage/cache",key:"storage"},
        {label:"TERMINAL",path:"tools/terminal/star-map",key:"terminal"},
        {label:"SETTINGS",path:"tools/settings/location",key:"settings"}
    ]
};

function familyFor(path) {
    if (typeof path !== "string") return "home";
    var id=path.split("/")[0];
    return Object.prototype.hasOwnProperty.call(GROUPS,id) ? id : "home";
}
function landingFor(family) {
    var key=familyFor(String(family||"")+"/");
    var matches=FAMILIES.filter(function(x){return x.id===key;});
    return matches.length ? matches[0].landing : "home/overview";
}
function tabsFor(path) {
    return GROUPS[familyFor(path)].slice();
}
function homeSectionFor(path) {
    if (familyFor(path)!=="home") return "";
    var key=String(path||"").split("/")[1]||"overview";
    // Old HOME/RUNTIME and HOME/HEALTH bookmarks remain valid, but both
    // now open the same final SOURCES screen. No saved routes are deleted.
    if (key==="runtime" || key==="health") return "sources";
    var allowed=["overview","auto","quick","snapshot","history","magick"];
    return allowed.indexOf(key)>=0?key:"overview";
}
function isHomeRoute(path) {
    return typeof path === "string" && /^home\/(overview|auto|quick|snapshot|history|runtime|health|magick)$/.test(path);
}
function selectedGroup(path) {
    var family=familyFor(path);
    var groups=GROUPS[family];
    var tokens=String(path||"").split("/");
    if (tokens.length<=2) {
        for(var j=0;j<groups.length;j++)
            if(groups[j].path===path) return groups[j].key;
    }
    var group=tokens[1]||"overview";
    if (family==="home" && (group==="runtime" || group==="health"))
        return "sources";
    // W8 // historical forecast deep links highlight the combined WEATHER
    // terminal instead of an obsolete bottom FORECAST button.
    if(family==="weather" && group==="forecasts") return "conditions";
    // All original map / event / geography / investigation deep links
    // belong to the one consolidated MAP / EVENTS tab.
    if(family==="earth" && ["maps","geography","geology",
      "events","fires","investigations"].indexOf(group)>=0) return "map";
    // Keep the PLANETS+STARS deep INDEX subtree associated with the full
    // SKY bottom swap, while its detailed route stays available in INDEX.
    if(family==="cosmos" && group==="planets-stars") return "sky";
    // M30-F: historical PLANETARY INDEX routes still highlight the new
    // LENSES category; the duplicated solar-hours bottom tab was retired.
    if(family==="magick" && group==="planetary") return "lenses";
    for(var k=0;k<groups.length;k++)
        if(groups[k].key===group) return group;
    return "overview";
}
function isDirectLanding(path) {
    if(isHomeRoute(path)) return true;
    for(var i=0;i<FAMILIES.length;i++)
        if(FAMILIES[i].landing===path) return true;
    return false;
}
