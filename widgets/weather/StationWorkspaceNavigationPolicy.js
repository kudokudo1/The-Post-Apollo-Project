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
        {label:"RUNTIME",path:"home/runtime",key:"runtime"},
        {label:"SOURCES",path:"home/health",key:"health"},
        {label:"MAGICK",path:"home/magick",key:"magick"}
    ],
    weather:[
        {label:"OVERVIEW",path:"weather/overview",key:"overview"},
        {label:"NOW + AIR",path:"weather/conditions/current",key:"conditions"},
        {label:"FORECAST",path:"weather/forecasts/hourly",key:"forecasts"},
        {label:"WATER",path:"weather/water/rivers",key:"water"},
        {label:"GROUND",path:"weather/ground/full",key:"ground"},
        {label:"HAZARDS",path:"weather/hazards/alerts",key:"hazards"},
        {label:"MAPS",path:"weather/maps",key:"maps"},
        {label:"HISTORY",path:"weather/history/historical-forecast",key:"history"}
    ],
    cosmos:[
        {label:"OVERVIEW",path:"cosmos/overview",key:"overview"},
        {label:"SUN",path:"cosmos/sun/position",key:"sun"},
        {label:"MOON",path:"cosmos/moon/ephemeris",key:"moon"},
        // Observatory only: terrestrial weather belongs to WEATHER.
        {label:"ASTRONOMY",path:"cosmos/sky/full",key:"sky"},
        {label:"EVENTS",path:"cosmos/events/iss",key:"events"},
        {label:"SPACE // ALL",path:"cosmos/space-weather/full",key:"space-weather"}
    ],
    earth:[
        {label:"OVERVIEW",path:"earth/overview",key:"overview"},
        {label:"GEOGRAPHY",path:"earth/geography/basemap",key:"geography"},
        {label:"GEOLOGY",path:"earth/geology/earthquakes",key:"geology"},
        {label:"EVENTS",path:"earth/events/eonet",key:"events"},
        {label:"FIRES",path:"earth/fires/hotspots",key:"fires"},
        {label:"MAPS",path:"earth/maps/overview",key:"maps"},
        {label:"DOSSIERS",path:"earth/investigations/context",key:"investigations"}
    ],
    media:[
        {label:"OVERVIEW",path:"media/overview",key:"overview"},
        {label:"NEWS",path:"media/news/reports",key:"news"},
        {label:"WATCH",path:"media/watch/live",key:"watch"},
        {label:"RADIO",path:"media/radio/directory",key:"radio"},
        {label:"CREATORS",path:"media/creators/saved",key:"creators"}
    ],
    magick:[
        {label:"OVERVIEW",path:"magick/overview",key:"overview"},
        {label:"LUNAR + SOLAR",path:"magick/lunar-solar/moon",key:"lunar-solar"},
        {label:"PLANETARY",path:"magick/planetary/hours",key:"planetary"},
        {label:"ASTROLOGY",path:"magick/astrology/charts",key:"astrology"},
        {label:"DIVINATION",path:"magick/divination/tarot",key:"divination"},
        {label:"GRIMOIRE",path:"magick/grimoire/references",key:"grimoire"}
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
    var allowed=["overview","auto","quick","snapshot","history","runtime","health","magick"];
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
    // Keep the PLANETS+STARS deep INDEX subtree associated with the full
    // SKY bottom swap, while its detailed route stays available in INDEX.
    if(family==="cosmos" && group==="planets-stars") return "sky";
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
