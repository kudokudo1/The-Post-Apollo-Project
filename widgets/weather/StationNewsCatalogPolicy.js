.pragma library

// Curated *destinations*, not live program availability or embedded-playback
// certification. Explicit access/format labels prevent confusion between
// free pages, pay-TV channels, recorded clips and official floor broadcasts.
// A real video source is opened only after a user-initiated in-pane action.
var channels = [
    {id:"aje", section:"LIVE", title:"AL JAZEERA ENGLISH", source:"Al Jazeera", detail:"International reporting // official live page", access:"FREE PAGE // EMBED UNVERIFIED", kind:"channel", url:"https://www.aljazeera.com/video/live"},
    {id:"livenow", section:"LIVE", title:"LIVENOW FROM FOX", source:"FOX Television Stations", detail:"Free rolling US news // not pay-TV FOX News Channel", access:"FREE PAGE // EMBED UNVERIFIED", kind:"channel", url:"https://www.livenowfox.com/live"},
    {id:"nbcnow", section:"LIVE", title:"NBC NEWS NOW", source:"NBC News", detail:"Free 24-hour streaming news", access:"FREE PAGE // EMBED UNVERIFIED", kind:"channel", url:"https://www.nbcnews.com/now"},
    {id:"abcnews", section:"LIVE", title:"ABC NEWS LIVE", source:"ABC News", detail:"Free continuous news and reporting", access:"FREE PAGE // EMBED UNVERIFIED", kind:"channel", url:"https://abc.com/watch-live"},
    {id:"cnn", section:"LIVE", title:"CNN", source:"CNN", detail:"Full live channel requires All Access or eligible TV provider", access:"SUBSCRIPTION / TV LOGIN", kind:"channel", url:"https://www.cnn.com/"},
    {id:"foxnews", section:"LIVE", title:"FOX NEWS CHANNEL", source:"Fox News", detail:"Full live channel requires FOX One or TV provider", access:"SUBSCRIPTION / TV LOGIN", kind:"channel", url:"https://www.fox.com/stream/fox-news"},
    {id:"house", section:"CONGRESS", title:"U.S. HOUSE FLOOR", source:"Office of the House Clerk", detail:"Official floor webcast // only when proceedings occur", access:"FREE OFFICIAL WEBCAST", kind:"channel", url:"https://live.house.gov/"},
    {id:"senate", section:"CONGRESS", title:"U.S. SENATE FLOOR", source:"U.S. Senate", detail:"Official Senate floor webcast", access:"FREE OFFICIAL WEBCAST", kind:"channel", url:"https://www.senate.gov/floor/"},
    {id:"hearings", section:"CONGRESS", title:"COMMITTEE HEARINGS", source:"Congress.gov", detail:"Public hearings, committee meetings and archived video when provided", access:"PUBLIC RECORDS // VIDEO VARIES", kind:"channel", url:"https://www.congress.gov/committees"},
    {id:"cspan", section:"CONGRESS", title:"C-SPAN", source:"C-SPAN", detail:"Public affairs coverage and archives; full linear channels may require TV login", access:"ARCHIVE FREE / LIVE TV LOGIN", kind:"channel", url:"https://www.c-span.org/"},
    {id:"bbc", section:"REPORTS", title:"BBC NEWS", source:"BBC", detail:"International reporting and news video", access:"PUBLISHER PAGE", kind:"channel", url:"https://www.bbc.com/news"},
    {id:"npr", section:"REPORTS", title:"NPR NEWS", source:"NPR", detail:"Public radio journalism, audio and reports", access:"PUBLISHER PAGE", kind:"channel", url:"https://www.npr.org/sections/news/"},
    {id:"nasa", section:"REPORTS", title:"NASA NEWS", source:"NASA", detail:"Space, Earth science and research", access:"OFFICIAL REPORTS", kind:"channel", url:"https://www.nasa.gov/news/"},
    {id:"nws", section:"REPORTS", title:"NATIONAL WEATHER SERVICE", source:"NWS", detail:"Official weather forecasts and warnings // not a TV station", access:"OFFICIAL DATA", kind:"channel", url:"https://www.weather.gov/"},
    {id:"groundnews", section:"COMPARE", title:"GROUND NEWS", source:"Ground News", detail:"Publisher comparison and blindspot analysis; ratings belong to provider", access:"FREE / SUBSCRIPTION FEATURES", kind:"channel", url:"https://ground.news/"},
    {id:"allsides", section:"COMPARE", title:"ALLSIDES", source:"AllSides", detail:"Compare headlines and editorial framing across outlets", access:"PROVIDER WEBSITE", kind:"channel", url:"https://www.allsides.com/unbiased-balanced-news"},
    {id:"jubilee", section:"CREATORS", title:"JUBILEE MEDIA", source:"Jubilee", detail:"Middle Ground, Odd One Out and social debate // not straight news", access:"CREATOR / DISCUSSION", kind:"channel", url:"https://www.jubileemedia.com/"},
    {id:"theonion", section:"SATIRE", title:"THE ONION", source:"The Onion", detail:"Fictional satirical news // never mark as verified reporting", access:"SATIRE / PARODY", kind:"channel", url:"https://theonion.com/"}
];
var sections = ["LIVE", "CONGRESS", "REPORTS", "COMPARE", "CREATORS", "SATIRE"];
function itemsFor(section) {
    return channels.filter(function(x) { return x.section === section; });
}
function find(id) {
    for (let i = 0; i < channels.length; ++i)
        if (channels[i].id === id) return channels[i];
    return null;
}
function safeChannelId(input) {
    const raw = String(input || "").trim();
    const match = /^(?:https:\/\/(?:www\.|m\.)?youtube\.com\/channel\/)?(UC[A-Za-z0-9_-]{22})\/?$/.exec(raw);
    return match ? match[1] : "";
}
function normalizeCreator(label, channelId) {
    const id = safeChannelId(channelId);
    const title = String(label || "").replace(/[\u0000-\u001f<>|]/g, " ").trim().slice(0, 70);
    if (!id || !title) return null;
    return {id:id, title:title};
}
function creatorRecord(label, channelId) {
    const c = normalizeCreator(label, channelId);
    if (!c) return null;
    return {id:"user-"+c.id, section:"CREATORS", title:c.title,
        source:"SAVED CREATOR", detail:"Selected YouTube channel // recent uploads available on demand",
        access:"YOUTUBE // USER ADDED", kind:"channel",
        channelId:c.id, url:"https://www.youtube.com/channel/"+c.id};
}
function toViewerRecord(item) {
    if (!item || !item.title || !/^https:\/\/[^ ]+$/.test(item.url)) return null;
    return {kind:"channel", title:item.title, source:item.source || "SOURCE",
        time:item.access || "ACCESS NOT VERIFIED", detail:item.detail || "",
        url:item.url, channelId:item.channelId || ""};
}
