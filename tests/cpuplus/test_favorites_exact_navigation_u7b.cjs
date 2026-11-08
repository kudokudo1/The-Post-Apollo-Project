"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
function load(file,env) {
    vm.runInNewContext(read(file).replace(/^\.pragma library\s*$/m,"")
        .replace(/^\.import ".+" as \w+\s*$/gm,""),env,{filename:file});
}
const Resource={};
load("services/favorites/FavoritesResourcePolicy.js",Resource);
const WeatherHome={};
load("services/weather/WeatherHomeFavoritesPolicy.js",WeatherHome);
const Exact={Resource,WeatherHome};
load("services/favorites/FavoritesExactNavigationPolicy.js",Exact);
const plain=x=>JSON.parse(JSON.stringify(x));
const known=Array.from(WeatherHome.PANELS);
function rowFor(route) {
    return {
        key:Resource.identityKey("weather-home","panel",route),
        owner:"weather-home",provider:"weather-home",kind:"panel",
        category:"WEATHER",menu:"HOME",readOnly:true,resolved:true,
        isFavorite:true,available:"unresolved",capabilities:[]
    };
}
function snapshot(routes,state="ready") {
    return {storageState:state,panelRoutes:routes.slice(),cardKeys:[]};
}

test("U7b fixed HOME panel routes produce only owner and safe route",()=>{
    assert.deepEqual(known,["home/auto","home/quick","home/snapshot",
        "home/history","home/runtime","home/health"]);
    for(const route of known) {
        const original=rowFor(route);
        const copy=plain(original);
        assert.deepEqual(plain(Exact.plan(original)),{
            ok:true,owner:"weather",route,reason:""
        });
        assert.deepEqual(plain(original),copy);
    }
});

test("U7b rejects forged records, non-panel favorites and strings with private content",()=>{
    const base=rowFor("home/quick");
    const variations=[
        null,[],{}, {...base,readOnly:false}, {...base,resolved:false},
        {...base,owner:"appcontrol"}, {...base,provider:"radio"},
        {...base,kind:"card"}, {...base,category:"APP CTRL"},
        {...base,menu:"RUN"}, {...base,isFavorite:false},
        {...base,key:Resource.identityKey("weather-home","card","weather|foo")},
        {...base,key:Resource.identityKey("weather-home","panel","home/private")},
        {...base,key:base.key+"&command=rm%20-rf"},
        {...base,key:"home/quick"},
        {...base,key:undefined},
        {...base,key:"fav1:local:weather-home:panel:home%2Fquick%2F.."}
    ];
    for(const candidate of variations) {
        const result=Exact.plan(candidate);
        assert.equal(result.ok,false,JSON.stringify(candidate));
        assert.equal(result.route,"");
        assert.equal(result.owner,"");
    }
    assert.equal(JSON.stringify(Exact.plan(base)).includes("fav1:"),false);
    assert.equal(JSON.stringify(Exact.plan(base)).includes("resourceId"),false);
});

test("Weather owner revalidates membership and store freshness before choosing route",()=>{
    for(const route of known) {
        assert.equal(Exact.ownerAllows(route,snapshot([route])),true);
        assert.equal(Exact.ownerAllows(route,snapshot([])),false);
    }
    for(const state of ["loading","saving","error","unsupported","disconnected"]) {
        assert.equal(Exact.ownerAllows("home/quick",snapshot(["home/quick"],state)),false);
    }
    assert.equal(Exact.ownerAllows("home/quick",null),false);
    assert.equal(Exact.ownerAllows("home/quick",{...snapshot(["home/quick"]),cardKeys:["bad"]}),false);
    assert.equal(Exact.ownerAllows("home/quick",{...snapshot(["home/quick"]),panelRoutes:["home/quick","home/quick"]}),false);
    assert.equal(Exact.ownerAllows("home/private",snapshot(["home/private"])),false);
    assert.equal(Exact.ownerAllows("media/radio/full",snapshot(["home/quick"])),false);
    assert.equal(Exact.ownerAllows("home/quick",snapshot(["home/quick"],"empty")),true);
});

test("U7b policy remains a pure navigation contract without filesystem or player APIs",()=>{
    const code=read("services/favorites/FavoritesExactNavigationPolicy.js");
    assert.doesNotMatch(code,/FileView\s*\{|Process\s*\{|execDetached|Qt\.openUrlExternally/);
    assert.doesNotMatch(code,/favoriteStore\.|toggleCardFavorite\(|replacePanelFavorites\(/);
    assert.doesNotMatch(code,/playStation\(|runCommand\(|deleteFile\(/);
    assert.match(code,/ownerAllows\(/);
    assert.match(code,/Resource\.identityKey\(/);
});

test("U7b shell, CPU++ and Weather owner form an allowlisted exact-item chain",()=>{
    const pane=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
    const cpu=read("widgets/CpuPlusW.qml");
    const shell=read("shell.qml");
    const weather=read("widgets/weather/WeatherStationW.qml");
    assert.match(pane,/import ".+FavoritesExactNavigationPolicy.js" as ExactNavigation/);
    assert.match(pane,/exactNavigationRequested\(target\.owner,target\.route\)/);
    assert.match(pane,/label: pane\.selectedResource && pane\.selectedResource\.readOnly[\s\S]*?"OPEN ITEM"/);
    assert.match(pane,/if\(pane\.selectedResource\.readOnly\)/);
    assert.match(pane,/id: openItem/);
    assert.match(pane,/property alias exactNavigationControl: openItem/);
    assert.match(cpu,/signal favoriteExactNavigationRequested\(string owner,string route\)/);
    assert.match(cpu,/onExactNavigationRequested: function\(owner,route\)/);
    assert.match(cpu,/cpuPlusWindow\.favoriteExactNavigationRequested\(owner,route\)/);
    assert.match(shell,/onFavoriteExactNavigationRequested: function\(owner,route\)/);
    assert.match(shell,/if\(shellRoot\.openApolloFavoriteItem\(owner,route\)\)\s*cpuPlusWindow\.close\(\)/);
    const routing=shell.split("function openApolloFavoriteItem(owner,route) {")[1]
        .split("function openApolloFavoriteOwner(owner,view) {")[0];
    assert.ok(routing);
    assert.match(routing,/owner!=="weather"/);
    assert.match(routing,/Object\.prototype\.hasOwnProperty\.call\(homeRoutes,route\)/);
    assert.match(routing,/weatherStationWindow\.openSavedHomePanel\(route\)/);
    assert.match(routing,/requestControlKeyboard\("weather","favorites-exact-item"\)/);
    assert.doesNotMatch(routing,/runCommand|execDetached|openUrl|launch|kill|playStation|favoriteKey/);
    const allow=[...routing.matchAll(/"(home\/[a-z-]+)":true/g)].map(x=>x[1]).sort();
    assert.deepEqual(allow,known.slice().sort());
    assert.match(weather,/function openSavedHomePanel\(route\)/);
    const ownerPath=weather.split("function openSavedHomePanel(route) {")[1]
        .split("function openNotificationView(view) {")[0];
    assert.ok(ownerPath);
    assert.equal((ownerPath.match(/ExactNavigation\.ownerAllows\(/g)||[]).length,2);
    assert.match(ownerPath,/subjectNavigator\.chooseRoute\(route\)/);
    assert.match(ownerPath,/!menuOpen \|\| !subjectNavigationOpen \|\| contextTerminalRequested/);
    assert.doesNotMatch(ownerPath,/toggleCardFavorite|replacePanelFavorites|FileView|playStation|launchSubjectTerminal/);
});

test("U7b native fixture explicitly clicks OPEN ITEM after OPEN OWNER",()=>{
    const fixture=read("tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml");
    const runner=read("scripts/favorites/verify_cpuplus_hub_fedora_u4.sh");
    assert.match(fixture,/onExactNavigationRequested: function\(owner,route\)/);
    assert.match(fixture,/route!=="home\/auto"/);
    assert.match(fixture,/detail\.exactNavigationControl/);
    assert.match(fixture,/U7B_PASS \/\/ EXACT_HOME_PANEL_ONLY_NO_PROVIDER_ACTIONS/);
    assert.match(runner,/U7B_ITEM_READY/);
    assert.match(runner,/U7B_PASS \/\/ EXACT_HOME_PANEL_ONLY_NO_PROVIDER_ACTIONS/);
    assert.match(runner,/xdotool mousemove --window "\$window" "\$ex" "\$ey" click 1/);
});
