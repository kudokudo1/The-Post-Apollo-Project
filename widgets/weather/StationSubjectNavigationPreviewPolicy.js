.pragma library

// Passive routes-to-legacy-page discovery for the M1 subject browser.
// No data fetching, writes, or reparenting. The old pages remain explicitly CLASSIC.
var ORDER = ["home","ground","sky","space","map","news","radio","terminal"];
var LABELS = {
  home:"HOME", ground:"GROUND", sky:"SKY", space:"SPACE",
  map:"MAP", news:"NEWS", radio:"RADIO", terminal:"TERMINAL"
};

function legacyPageForPanel(panelId) {
  if (typeof panelId !== "string") return "";
  var prefix = panelId.split("-")[0];
  return ORDER.indexOf(prefix) >= 0 ? prefix : "";
}

function sourcePagesForPath(path, panelRoutes) {
  if (typeof path !== "string"
      || !/^[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)
      || !panelRoutes || typeof panelRoutes !== "object")
    return [];
  var counts = {};
  for (var i = 0; i < ORDER.length; i++) counts[ORDER[i]] = 0;
  var keys = Object.keys(panelRoutes);
  for (var j = 0; j < keys.length; j++) {
    var panel = keys[j];
    var target = panelRoutes[panel];
    if (typeof target !== "string"
        || (target !== path && target.indexOf(path + "/") !== 0))
      continue;
    var oldPage = legacyPageForPanel(panel);
    if (oldPage) counts[oldPage]++;
  }
  return ORDER.filter(function(key) {return counts[key] > 0;})
    .map(function(key) {
      return {id:key, label:LABELS[key], panels:counts[key], status:"CLASSIC_SOURCE"};
    });
}
