.pragma library

// MEDIA D1 // one subject, four real existing media components.
// Pure routing and visibility only. No stream/playback, files or fetches.
var FORMAT = "post-apollo.weather.media-panels.d1.v1";
var ROUTES = {
  "media/overview": {page:"overview"},
  "media/news/reports": {page:"news",section:"REPORTS"},
  "media/news/filters": {page:"news",section:"REPORTS"},
  "media/news/trends": {page:"news",section:"REPORTS"},
  "media/news/stories": {page:"news",section:"REPORTS"},
  "media/news/locations": {page:"news",section:"REPORTS"},
  "media/news/viewer": {page:"news",section:"REPORTS"},
  "media/watch/live": {page:"catalog",section:"LIVE"},
  "media/watch/congress": {page:"catalog",section:"CONGRESS"},
  "media/watch/reports": {page:"catalog",section:"REPORTS"},
  "media/watch/compare": {page:"catalog",section:"COMPARE"},
  "media/watch/satire": {page:"catalog",section:"SATIRE"},
  "media/radio/directory": {page:"radio"},
  "media/radio/saved": {page:"radio"},
  "media/radio/transport": {page:"radio"},
  "media/creators/saved": {page:"catalog",section:"CREATORS"},
  "media/creators/uploads": {page:"catalog",section:"CREATORS"}
};

function routeInfo(path) {
  return typeof path === "string"
    && Object.prototype.hasOwnProperty.call(ROUTES,path)
    ? ROUTES[path] : null;
}
function kindForRoute(path) {
  var row=routeInfo(path);
  return row ? row.page : "";
}
function catalogSectionFor(path) {
  var row=routeInfo(path);
  return row && row.section ? row.section : "";
}
function newsGroupVisible(path,group) {
  if (path === "") return true;  // CLASSIC NEWS never filtered.
  if (kindForRoute(path) !== "news") return false;
  if (group === "header" || group === "request" || group === "status")
    return true;
  if (group === "filters") return true; // Filters apply locally to every news submode.
  // Feed-first NEWS is the article workspace. Dedicated analysis routes
  // keep trend and story sections from burying the actual headline list.
  if (group === "list")
    return path === "media/news/reports" || path === "media/news/filters"
        || path === "media/news/locations" || path === "media/news/viewer";
  if (group === "trend")
    return path === "media/news/trends";
  if (group === "stories")
    return path === "media/news/stories";
  if (group === "inspector-hint")
    return path === "media/news/locations" || path === "media/news/viewer";
  return false;
}
function radioGroupVisible(path,group) {
  if (path === "" || path === "media/overview") return true;
  if (kindForRoute(path) !== "radio") return false;
  if (group === "header" || group === "source" || group === "transport"
      || group === "status") return true;
  if (group === "search" || group === "directory")
    return path === "media/radio/directory";
  if (group === "saved")
    return path === "media/radio/saved" || path === "media/radio/transport";
  return false;
}
function hintFor(path) {
  if (path === "media/news/locations")
    return "SELECT A HEADLINE, OPEN ITS INSPECTOR AND REQUEST ARTICLE LOCATIONS. GDELT GKG RETURNS MENTIONS, NOT VERIFIED EVENT SITES.";
  if (path === "media/news/viewer")
    return "SELECT A HEADLINE TO OPEN THE EXISTING IN-STATION ARTICLE INSPECTOR. ARTICLE RENDERING DEPENDS ON THE AVAILABLE HOST.";
  if (path === "media/creators/uploads")
    return "SELECT UPLOADS ON A SAVED CREATOR TO QUERY ITS RECENT VIDEOS. THIS IS AN EXPLICIT REQUEST, NOT A LIVE CHANNEL.";
  if (path === "media/watch/live")
    return "CHANNELS ARE PUBLISHER DESTINATIONS; LIVE VIDEO AND EMBEDDING ARE NOT CERTIFIED.";
  return "";
}
