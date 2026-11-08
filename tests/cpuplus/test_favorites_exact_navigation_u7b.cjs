"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
function load(file,env) {
    vm.runInNewContext(read(file).replace(/^\\.pragma library\\s*$/m,"")
        .replace(/^\\.import ".+" as \\w+\\s*$/gm,""),env,{filename:file});
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
    assert.doesNotMatch(code,/FileView\\s*\\{|Process\\s*\\{|execDetached|Qt\\.openUrlExternally/);
    assert.doesNotMatch(code,/favoriteStore\\.|toggleCardFavorite\\(|replacePanelFavorites\\(/);
    assert.doesNotMatch(code,/playStation\\(|runCommand\\(|deleteFile\\(/);
    assert.match(code,/ownerAllows\\(/);
    assert.match(code,/Resource\\.identityKey\\(/);
});
