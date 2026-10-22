#!/usr/bin/env node
"use strict";

// Behavioral tests run the actual production pure-JS policy in a VM.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const file = path.join(__dirname, "../../services/hub/ApolloHubNetworkPolicy.js");
const source = fs.readFileSync(file, "utf8").replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename: "ApolloHubNetworkPolicy.js"});

function observe(values) { return policy.snapshot(values); }
function connectedWifi(extra={}) {
    return {devicesKnown:true, wifiPresent:true, wifiConnected:true,
            wifiInterface:"wlp3s0", wifiName:"Example SSID", wifiSignal:0.734,
            ...extra};
}

assert.equal(observe(null).state, "unavailable");
assert.equal(observe({devicesKnown:false}).connected, false);
assert.equal(observe({devicesKnown:true}).state, "unavailable");
let offline = observe({devicesKnown:true,wifiPresent:true,
                       wifiConnected:false,ethernetPresent:true});
assert.equal(offline.state, "disconnected");
assert.equal(offline.internetState, "unverified");
assert.equal(offline.wifi.signalPercent, -1);
assert.equal(offline.transport, "none");

let wifi = observe(connectedWifi());
assert.equal(wifi.state, "connected");
assert.equal(wifi.connected, true);
assert.equal(wifi.transport, "wifi");
assert.equal(wifi.wifi.interfaceName, "wlp3s0");
assert.equal(wifi.wifi.networkName, "Example SSID");
assert.equal(wifi.wifi.signalPercent, 73);
assert.equal(wifi.ethernet.connected, false);
assert.equal(wifi.internetState, "unverified");
assert.equal(wifi.linkSpeedMbps, -1);
assert.equal(wifi.linkSpeedApproximate, false);

// The dock supplies one existing Wi-Fi bitrate; no duplicate probe.
// Its number represents approximate link rate, NOT Internet throughput.
const fastWifi = observe(connectedWifi({wifiLinkSpeedMbps:229.2}));
assert.equal(fastWifi.linkSpeedMbps, 229);
assert.equal(fastWifi.linkSpeedApproximate, true);
assert.equal(fastWifi.internetState, "unverified");
assert.equal(observe(connectedWifi({wifiLinkSpeedMbps:0})).linkSpeedMbps, -1);
assert.equal(observe(connectedWifi({wifiLinkSpeedMbps:100.5})).linkSpeedMbps, 101);
for (const badSpeed of [null, undefined, "", "229", -2, 0, NaN, Infinity,
                        {}, []]) {
    assert.equal(observe(connectedWifi({wifiLinkSpeedMbps:badSpeed})).linkSpeedMbps, -1);
}
assert.equal(observe(connectedWifi({wifiConnected:false, wifiLinkSpeedMbps:229})).linkSpeedMbps, -1);

let wired = observe({devicesKnown:true, wifiPresent:true, wifiConnected:false,
                     ethernetPresent:true, ethernetConnected:true,
                     ethernetInterface:"enp2s0", wifiName:"should-hide"});
assert.equal(wired.transport, "ethernet");
assert.equal(wired.linkSpeedMbps, -1);
assert.equal(wired.linkSpeedApproximate, false);
assert.equal(wired.ethernet.interfaceName, "enp2s0");
assert.equal(wired.wifi.networkName, "");
assert.equal(wired.wifi.signalPercent, -1);

let both = observe({...connectedWifi(),ethernetPresent:true,
                    ethernetConnected:true,ethernetInterface:"enp2s0"});
assert.equal(both.transport, "ethernet");
assert.equal(both.wifi.connected, true);
assert.equal(both.ethernet.connected, true);
assert.equal(both.internetState, "unverified");
assert.equal(observe({...connectedWifi({wifiLinkSpeedMbps:229}),
                      ethernetPresent:true, ethernetConnected:true}).linkSpeedMbps, -1);

// Malformed strength and absent connected SSID are unknown, never 0%.
// Don't confuse values from a *different* network with this connected link.
for (const bad of [undefined, null, "", "abc", -0.01, 1.01,
                    Infinity, NaN, {}, []]) {
    assert.equal(observe(connectedWifi({wifiSignal:bad})).wifi.signalPercent, -1);
}
assert.equal(observe(connectedWifi({wifiSignal:0})).wifi.signalPercent, 0);
assert.equal(observe(connectedWifi({wifiSignal:1})).wifi.signalPercent, 100);
assert.equal(observe(connectedWifi({wifiSignal:0.499})).wifi.signalPercent, 50);
assert.equal(observe(connectedWifi({wifiName:null})).wifi.networkName, "");
assert.equal(observe(connectedWifi({wifiName:123})).wifi.networkName, "");
assert.equal(observe(connectedWifi({wifiInterface:null})).wifi.interfaceName, "");

// No credential, control function, raw object or private address can leak.
const secret = observe({...connectedWifi(),password:"VERY SECRET",
    token:"ACCESS TOKEN", mac:"00:11:22:33:44:55", command:"disconnect"});
const encoded = JSON.stringify(secret);
for (const forbidden of ["VERY SECRET", "ACCESS TOKEN",
                         "00:11:22:33:44:55", "disconnect"])
    assert.equal(encoded.includes(forbidden), false);

console.log("ApolloHub Network policy behavior tests passed");
