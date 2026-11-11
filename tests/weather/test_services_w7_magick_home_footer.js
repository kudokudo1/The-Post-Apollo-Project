"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");
const card=read("widgets/weather/StationHomeMetricCard.qml");
const consoleQml=read("widgets/weather/StationServicesConsole.qml");
const magick=read("widgets/weather/StationMagickServicesPane.qml");
const host=read("widgets/weather/StationMagickSubjectPane.qml");
const nav=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const index=read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySrc=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
function policy(src){const target={};vm.runInNewContext(src.replace(/^\.pragma library\s*/m,""),target);return target;}

test("W7 HOME last-success text stays in its own bounded 48px SERVICES card",()=>{
  assert.match(consoleQml,/height: services\.homeCards \? 48 : 31/);
  assert.match(consoleQml,/servicesCompact: services\.homeCards/);
  assert.match(card,/property bool servicesCompact: false/);
  assert.match(card,/clip: true/);
  assert.match(card,/visible: !card\.servicesCompact/);
  assert.match(card,/id: servicesCompactText/);
  assert.match(card,/visible: card\.servicesCompact/);
  for (const label of ["title","valueText","detailText","footerText"])
      assert.ok(card.includes("card."+label),"missing "+label);
  assert.match(card,/id: servicesFooter/);
  assert.match(card,/height: 15/);
  assert.match(card,/height: 11/);
  assert.match(card,/anchors\.margins: 3/);
});

test("W7 MAGICK final SERVICES is registered in existing SUBJECTS and INDEX",()=>{
  const groups=policy(nav),tree=policy(index),routes=policy(policySrc);
  assert.equal(groups.GROUPS.magick.at(-1).label,"SERVICES");
  assert.equal(groups.GROUPS.magick.at(-1).key,"services");
  assert.equal(groups.GROUPS.magick.at(-1).path,"magick/services/health");
  assert.equal(groups.selectedGroup("magick/services/health"),"services");
  assert.equal(tree.findRoute("magick/services/health").subject,"magick");
  assert.equal(routes.kindForRoute("magick/services/health"),"reference");
  assert.equal(routes.sourceFor("magick/services/health"),"");
  assert.equal(routes.isInterpretationImplemented("magick/services/health"),false);
  assert.equal(Object.keys(routes.ROUTES).length,17);
  assert.match(host,/servicesRoute:\s*\n\s*subjectRoute === "magick\/services\/health"/);
  assert.match(host,/StationMagickServicesPane\s*\{/);
  assert.match(host,/active: magickPane\.visible && !magickPane\.servicesRoute/);
});

test("W7 MAGICK service list comes from registered routes plus actual two shared contexts",()=>{
  assert.match(magick,/Object\.keys\(MagickPolicy\.ROUTES\)\.filter/);
  assert.match(magick,/MagickPolicy\.sourceFor\(path\)/);
  assert.match(magick,/MagickPolicy\.secondarySourceFor\(path\)/);
  assert.match(magick,/MagickPolicy\.titleFor\(path\)/);
  assert.match(magick,/path !== "magick\/services\/health"/);
  for(const kind of ["LOCAL CALC // REUSED WEATHER","SESSION LOCAL","LOCAL REFERENCE",
                     "JPL / COSMOS REFERENCE","REUSED OBSERVATION",
                     "SHARED // WEATHER CONTEXT","SHARED // STATION CLOCK"])
    assert.ok(magick.includes(kind),kind);
  assert.match(magick,/forecastSourceReady/);
  assert.match(magick,/jplSourceReady/);
  assert.match(magick,/runtimeNowMs/);
  assert.match(magick,/familyLabel: "MAGICK"/);
  assert.match(magick,/primaryStripLabel: "INSTRUMENTS/);
  assert.match(magick,/runtimeRows: \[\]/);
  assert.match(magick,/directoryRows: magickServices\.directoryRows/);
  assert.doesNotMatch(magick,/Process\s*\{|FileView\s*\{|XMLHttpRequest|Timer\s*\{|WeatherService\s*\{|StationSky\s*\{/);
});
