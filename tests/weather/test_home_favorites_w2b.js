"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const policyText = read("services/weather/WeatherHomeFavoritesPolicy.js");
const healthText = read("widgets/weather/StationHomeCardProvenancePolicy.js");
const storeQml = read("services/weather/WeatherHomeFavoritesStore.qml");
const favQml = read("services/favorites/FavoritesStore.qml");
const homeQml = read("widgets/weather/StationHome.qml");
const cardQml = read("widgets/weather/StationHomeMetricCard.qml");
const surface = read("widgets/weather/StationWorkspaceSurface.qml");
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const weatherPane = read("widgets/weather/StationWeatherSubjectPane.qml");
const env = vm.createContext({Math,Number,String,Array,Object,JSON,isFinite});
const health = vm.createContext({Math,Number,String,Array,Object,JSON,isFinite});
vm.runInContext(policyText.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(healthText.replace(/^\.pragma library\s*$/m,""),health);
const copy = v => JSON.parse(JSON.stringify(v));

test("new Weather HOME storage schema is independent from AppControl",()=>{
  const d=copy(env.empty());
  assert.deepEqual(d,{
    schema:"post-apollo.weather-home-favorites.v1",
    version:1,revision:0,panelRoutes:[],cardKeys:[]
  });
  assert.match(storeQml,/Quickshell\.dataDir \+ "\/weather-home-favorites-v1\.json"/);
  assert.match(favQml,/Quickshell\.dataDir \+ "\/appcontrol-favorites\.json"/);
  assert.ok(!storeQml.includes('Quickshell.dataDir + "/appcontrol-favorites.json"'));
  assert.ok(!policyText.includes("favoriteMonitorBoxKeys"));
  assert.ok(!policyText.includes("favoriteTaskMetricKeys"));
  assert.match(storeQml,/atomicWrites: true/);
  assert.match(storeQml,/watchChanges: false/);
  assert.match(storeQml,/onLoadFailed:/);
  assert.match(storeQml,/FileViewError\.FileNotFound/);
  assert.match(storeQml,/onSaved:/);
  assert.match(storeQml,/onSaveFailed:/);
});

test("strict parser round-trips only IDs, refuses malformed/unsupported records",()=>{
  const d=env.empty();
  const good=env.update(d,["home/auto","home/runtime"],
                         ["sky|next-hours","space|geomagnetic"]);
  assert.equal(good.ok,true);
  assert.equal(good.changed,true);
  assert.equal(good.document.revision,1);
  const readback=env.parse(JSON.stringify(good.document));
  assert.equal(readback.ok,true);
  assert.deepEqual(copy(readback.document),copy(good.document));

  const mutated = [
    "{invalid", "null", "[]", "{}",
    JSON.stringify({...d,version:2}),
    JSON.stringify({...d,schema:"appcontrol-favorites"}),
    JSON.stringify({...d,revision:-1}),
    JSON.stringify({...d,revision:"1"}),
    JSON.stringify({...d,panelRoutes:["earth/overview"]}),
    JSON.stringify({...d,panelRoutes:["home/auto","home/auto"]}),
    JSON.stringify({...d,cardKeys:["sky|not-allowed|xx"]}),
    JSON.stringify({...d,cardKeys:["sky|next-hours","sky|next-hours"]}),
    JSON.stringify({...d,cardKeys:["weather|temp", "oops"]}),
  ];
  for(const item of mutated) {
    assert.equal(env.parse(item).ok,false,item);
  }
  const dataLeak={...d,revision:1,cardKeys:["sky|next-hours"]};
  dataLeak.cardKeys[0]={id:"next-hours",value:"77°F",ready:true};
  assert.equal(env.parse(JSON.stringify(dataLeak)).ok,false);
});

test("panel favorites only change on explicit valid requests; failed changes do not mutate",()=>{
  const first=env.empty();
  assert.equal(env.replacePanels(first,["home/auto","home/quick"]).ok,true);
  assert.equal(first.revision,0);
  assert.deepEqual(copy(first.panelRoutes),[]);
  assert.equal(env.replacePanels(first,["home/auto","home/auto"]).ok,false);
  assert.equal(env.replacePanels(first,["home/magick"]).ok,false);
  const next=env.replacePanels(first,["home/auto"]);
  assert.equal(next.document.revision,1);
  assert.equal(env.replacePanels(next.document,["home/auto"]).changed,false);
  assert.deepEqual(copy(env.PANELS),[
    "home/auto","home/quick","home/snapshot",
    "home/history","home/runtime","home/health"
  ]);
});

test("card keys are stable provider+card IDs with a bounded count",()=>{
  let doc=env.empty();
  const add=env.toggleCard(doc,"sky|next-hours");
  assert.equal(add.ok,true);
  assert.equal(add.document.revision,1);
  assert.deepEqual(copy(add.document.cardKeys),["sky|next-hours"]);
  const remove=env.toggleCard(add.document,"sky|next-hours");
  assert.equal(remove.ok,true);
  assert.deepEqual(copy(remove.document.cardKeys),[]);
  assert.equal(remove.document.revision,2);
  for(const bad of ["next-hours","sky|","Sky|next-hours",
                    "sky|foo/bar","appcontrol|next-hours",
                    "weather|value=77","sky|a".repeat(100)]) {
    assert.equal(env.validCardKey(bad),false,bad);
  }
  assert.equal(env.validCardKey("space|geomagnetic"),true);
  let item=env.empty();
  for(let i=0;i<32;i++) {
    const added=env.toggleCard(item,"sky|card-"+i);
    assert.equal(added.ok,true);
    item=added.document;
  }
  assert.equal(env.toggleCard(item,"sky|card-extra").reason,"CARD_LIMIT");
});

test("provenance follows current source health and never grants freshness from a pin",()=>{
  const sky={source:"sky",id:"next-hours",rank:45};
  const kp={source:"space",id:"geomagnetic",rank:88};
  const multi={source:"space",id:"space-stack",rank:99};
  const rows=[
    {id:"weather",provider:"WTTR.IN",state:"STALE",
     sampleAgeMinutes:-1,lastSuccessAgeMinutes:36},
    {id:"kp",provider:"NOAA SWPC",state:"LIVE",
     sampleAgeMinutes:12,lastSuccessAgeMinutes:1}
  ];
  assert.equal(health.cardKey(sky),"sky|next-hours");
  assert.equal(health.cardKey(kp),"space|geomagnetic");
  assert.equal(health.sourceIdFor(sky),"weather");
  assert.equal(health.sourceIdFor(kp),"kp");
  assert.equal(health.sourceIdFor(multi),"");
  assert.match(health.provenance(sky,rows),/STALE/);
  assert.match(health.provenance(sky,rows),/AGE 36m/);
  assert.match(health.provenance(kp,rows),/LIVE/);
  assert.match(health.provenance(kp,rows),/AGE 12m/);
  assert.match(health.provenance(multi,rows),/FRESHNESS UNVERIFIED/);
  assert.match(health.provenance({source:"space",id:"space-feed",rank:72},rows),/FRESHNESS UNVERIFIED/);
  const pins=copy(health.pinnedRows(["sky|next-hours","space|geomagnetic"],
                        [sky]));
  assert.deepEqual(pins.map(p=>p.status),[
    "CURRENT WATCH","NOT CURRENTLY PROMOTED"
  ]);
  assert.ok(!("value" in pins[1]));
  assert.ok(!("ready" in pins[1]));
  assert.ok(!("age" in pins[1]));
});

test("single root writer, native per-card button and after-save panel synchronization",()=>{
  assert.equal((station.match(/WeatherServices\.WeatherHomeFavoritesStore\s*\{/g)||[]).length,1);
  assert.match(station,/homeFavoritesStore: homeFavoritesStore/);
  assert.match(navigator,/property var homeFavoritesStore: null/);
  assert.match(navigator,/function syncHomeDeckFavorites\(\)/);
  assert.match(navigator,/function onFavoritesLoaded\(\)/);
  assert.match(navigator,/function onFavoritesSaved\(revision\)/);
  assert.match(navigator,/replacePanelFavorites\(paths\)/);
  assert.match(surface,/homeFavoritesStore: surface\.homeFavoritesStore/);
  assert.match(weatherPane,/homeFavoritesStore: weatherPane\.homeFavoritesStore/);
  assert.match(homeQml,/property var homeFavoritesStore: null/);
  assert.match(homeQml,/onPinRequested:/);
  assert.match(homeQml,/toggleCardFavorite\(/);
  assert.match(cardQml,/ActionButton\s*\{/);
  assert.match(cardQml,/onClicked: card\.pinRequested\(\)/);
  assert.match(cardQml,/visible: card\.pinEnabled/);
  assert.match(cardQml,/available: card\.pinAvailable/);
  assert.match(homeQml,/PINNED CARD IDS \/\/ CURRENT RANKING IS SEPARATE/);
  for(const source of [homeQml,cardQml,surface,navigator,weatherPane]) {
    assert.ok(!source.includes("FileView {"),"no second writer");
    assert.ok(!source.includes("Process {"),"no extra source process");
  }
  assert.match(storeQml,/function replacePanelFavorites\(routes\)/);
  assert.match(storeQml,/function toggleCardFavorite\(sourceId, cardId\)/);
  assert.match(storeQml,/onSaved:[\s\S]*store\.favoritesSaved\(store\.revision\)/);
});

test.todo("native Fedora Quickshell FileView save, reload and corrupt-file refusal");
test.todo("operator Fedora/Sway visual acceptance");
