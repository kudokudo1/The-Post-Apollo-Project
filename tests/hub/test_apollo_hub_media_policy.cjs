#!/usr/bin/env node
"use strict";
// Execute actual Hub media projection code with isolated, synthetic observations.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubMediaPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename:"ApolloHubMediaPolicy.js"});

const now = 1000000;
const mpd = (connected, observation, error="", observed=now-1000, clock=now) =>
    policy.mpdSnapshot(connected, observation, error, observed, clock);
const loaded = {ref:{source:"direct-stream",id:"https://private.example/secret"},
    item:{title:"Loaded cassette",artist:"Radio",live:true}};
const session = {backend:"mpd",state:"playing",observed:true,
    ownedByController:true,current:{title:"Playing track",artist:"Artist X",
    uri:"file:///private/music.mp3",queueId:"private"}};
const payload = {session,loaded,selection:{id:"not loaded"},
    browse:{query:"private search"},generation:4};

let idle=mpd(false,payload);
assert.equal(idle.state,"disconnected");
assert.equal(idle.title,"");
assert.equal(idle.ownedByController,false);
assert.equal(mpd(true,null).state,"unobserved");
assert.equal(mpd(true,payload,"",0).state,"unobserved");

let playing=mpd(true,payload);
assert.equal(playing.state,"playing");
assert.equal(playing.fresh,true);
assert.equal(playing.title,"Playing track");
assert.equal(playing.artist,"Artist X");
assert.equal(playing.lastKnownLoadedTitle,"Loaded cassette");
assert.equal(playing.loaded,true);
assert.equal(playing.ownedByController,true);
assert.equal(playing.audibleOutputVerified,false);
assert.equal(playing.ageSeconds,1);
assert.equal(mpd(true,payload,"",now-15000).state,"playing");
assert.equal(mpd(true,payload,"",now-15001).state,"stale");
assert.equal(mpd(true,payload,"",now+1).state,"unobserved");
let stale=mpd(true,payload,"",now-15001);
assert.equal(stale.title,"");
assert.equal(stale.ownedByController,false);
assert.equal(stale.lastKnownLoadedTitle,"Loaded cassette");
let error=mpd(true,payload,"CONTROLLER FAILED");
assert.equal(error.state,"error");
assert.equal(error.fresh,false);
assert.equal(error.ownedByController,false);
assert.equal(error.title,"");

let paused=mpd(true,{session:{...session,state:"paused"}});
assert.equal(paused.state,"paused");
let externallyOwned=mpd(true,{session:{...session,ownedByController:false}});
assert.equal(externallyOwned.ownedByController,false);
let unloaded=mpd(true,{session:{backend:null,state:"unloaded",observed:true,
                                 ownedByController:false,current:null},loaded:null});
assert.equal(unloaded.state,"unloaded");
assert.equal(unloaded.loaded,false);
assert.equal(unloaded.title,"");
let unobserved=mpd(true,{session:{...session,observed:false}});
assert.equal(unobserved.state,"unavailable");
assert.equal(unobserved.fresh,false);
assert.equal(mpd(true,{session:{...session,state:"buffering"}}).state,"unavailable");

// No copied source object, secret URL, raw session identity, control or action escapes.
const output=JSON.stringify(playing);
for(const forbidden of ["private.example","private search","file:///private",
                        "queueId","media_controller","generation","transport",
                        "selection","commandIssued"]) {
    assert.equal(output.includes(forbidden),false,forbidden);
}

const mpris = value => policy.mprisSnapshot(value);
assert.equal(mpris({playerCount:0}).state,"unavailable");
assert.equal(mpris({playerCount:1}).state,"selection-required");
assert.equal(mpris({playerCount:3}).state,"selection-required");
assert.equal(mpris({selectedBusName:"org.mpris.MediaPlayer2.browser",
                    playerCount:3}).state,"player-missing");
assert.equal(mpris({selectedBusName:"",playerCount:1,
                    player:{identity:"Wrong default"}}).state,"selection-required");
let selected=mpris({selectedBusName:"org.mpris.MediaPlayer2.browser",
    playerCount:2, player:{identity:"Browser",title:"Video name",
    artist:"Channel",album:"Series",playbackState:"playing",
    secret:"SHOULD_NOT_LEAK",play(){throw new Error("not allowed")}}});
assert.equal(selected.state,"playing");
assert.equal(selected.selected,true);
assert.equal(selected.playerName,"Browser");
assert.equal(selected.title,"Video name");
assert.equal(selected.artist,"Channel");
assert.equal(selected.album,"Series");
assert.equal(selected.audibleOutputVerified,false);
assert.equal(JSON.stringify(selected).includes("SHOULD_NOT_LEAK"),false);
assert.equal(JSON.stringify(selected).includes("org.mpris"),false);
assert.equal(mpris({selectedBusName:"named",playerCount:1,
                    player:{playbackState:"paused"}}).state,"paused");
assert.equal(mpris({selectedBusName:"named",playerCount:1,
                    player:{playbackState:"stopped"}}).state,"stopped");
assert.equal(mpris({selectedBusName:"named",playerCount:1,
                    player:{playbackState:"unknown"}}).state,"unknown");
assert.equal(mpris({selectedBusName:"named",playerCount:1,
                    player:{title:123,playbackState:"playing"}}).title,"");
assert.equal(policy.shortText("  Some\nTitle\t",160),"Some Title");
assert.equal(policy.shortText("x".repeat(400),160).length,160);
console.log("ApolloHub B4 MPD/MPRIS media policy behavior tests passed");
