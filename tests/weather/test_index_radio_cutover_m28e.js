"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root,name),"utf8");
const navSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const previewSource = read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const mediaSource = read("widgets/weather/StationMediaSubjectPanelPolicy.js");
const radio = read("widgets/weather/StationRadio.qml");
const pane = read("widgets/weather/StationMediaSubjectPane.qml");
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const env = vm.createContext({});
const media = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(previewSource.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(mediaSource.replace(/^\.pragma library\s*$/m,""),media);
const plain = x => JSON.parse(JSON.stringify(x));

const radioIds = [
  "radio-directory","radio-search-presets","radio-paging",
  "radio-favorites-recent","radio-select-load-enter","radio-play-pause-stop"
];

test("six original RADIO capability families are explicitly accounted for", () => {
  const actual = Object.keys(env.PANELS).filter(id => id.startsWith("radio-"));
  assert.deepEqual(actual.sort(),radioIds.slice().sort());
  for (const id of radioIds)
    assert.equal(env.WIRED_IN_SUBJECTS[id],"M28-E",id);
  assert.deepEqual(plain(env.sourcePagesForPath("media/radio",env.PANELS).map(x => x.id)),["radio"],
    "historical provenance remains available");
  assert.deepEqual(plain(env.remainingSourcePagesForPath("media/radio",env.PANELS)),[],
    "all six formerly CLASSIC-only RADIO source shortcuts are now subject-routed");
});

test("INDEX links directly to three concrete RADIO subroutes with deduplicated controls", () => {
  const links=plain(env.nativeDestinationsForPath("media/radio",env.PANELS));
  assert.deepEqual(links,[
    {path:"media/radio/directory",panels:3,milestones:["M28-E"]},
    {path:"media/radio/saved",panels:1,milestones:["M28-E"]},
    {path:"media/radio/transport",panels:2,milestones:["M28-E"]}
  ]);
  for(const item of links){
    assert.equal(media.kindForRoute(item.path),"radio");
    assert.equal(env.findRoute(item.path).group,false);
  }
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.match(navigator,/onClicked: browser\.chooseRoute\(modelData\.path\)/);
});

test("native RADIO retains original search, presets, paging, favorites, recents and exact transport", () => {
  assert.match(pane,/sourceComponent: mediaPane\.kind === "overview"/);
  assert.match(pane,/mediaPane\.kind === "radio"/);
  assert.match(pane,/StationRadio\s*\{/);
  assert.match(pane,/subjectRoute: mediaPane\.subjectRoute/);
  for(const name of ["search","searchPreset","nextPage","recallSaved",
                     "toggleHighlightedFavorite","loadSelection","enterHighlighted","playbackAction"])
    assert.ok(radio.includes("function " + name + "("),name);
  for(const call of [
    "stationRadio.searchPreset(index)",
    "stationRadio.nextPage()",
    "stationRadio.recallSaved(modelData)",
    "stationRadio.playbackAction(\"play\")",
    "stationRadio.playbackAction(\"pause\")",
    "stationRadio.playbackAction(\"stop\")"
  ])assert.ok(radio.includes(call),call);
  assert.match(radio,/MediaServices\.HeadlessMediaController\s*\{/);
  assert.match(radio,/radioClient: "weather-radio"/);
  assert.match(radio,/weather-radio-memory\.json/);
  assert.match(radio,/NO AUTOPLAY/);
  assert.equal(media.radioGroupVisible("media/radio/directory","search"),true);
  assert.equal(media.radioGroupVisible("media/radio/saved","saved"),true);
  assert.equal(media.radioGroupVisible("media/radio/transport","transport"),true);
});

test("M28-E RADIO source cutover stays exact even as later MEDIA catalogs are reviewed", () => {
  const ids=Object.keys(env.WIRED_IN_SUBJECTS)
    .filter(id=>env.WIRED_IN_SUBJECTS[id]==="M28-E");
  assert.deepEqual(ids.sort(),radioIds.slice().sort());
  for(const family of ["media/watch","media/creators"])
    assert.ok(env.sourcePagesForPath(family,env.PANELS).length>0,
      "historical source map remains intact for "+family);
  assert.deepEqual(plain(env.remainingSourcePagesForPath("media",null)),[]);
  assert.deepEqual(plain(env.nativeDestinationsForPath("../media",env.PANELS)),[]);
});
