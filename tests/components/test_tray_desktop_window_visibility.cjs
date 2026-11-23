#!/usr/bin/env node
"use strict";
// Synthetic Sway GET_TREE fixtures against the real QML-imported policy.
// No compositor, app process, D-Bus registry or desktop is touched.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const policy = fs.readFileSync(
    path.resolve(__dirname, "../../modules/TrayDesktopVisibility.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(policy, context);
const list = snapshot => Array.from(context.visibleWindowKeysFromTree(snapshot));
const visible = (item, keys) => context.hasVisibleDesktopWindow(item, keys);
function root(...nodes) { return JSON.stringify({type:"root", nodes}); }
function output(...nodes) { return {type:"output", name:"DP-5", nodes}; }
function ws(name, ...nodes) {
    return {type:"workspace", name, nodes, floating_nodes:[]};
}
function wayland(app_id, show) {
    return {type:"con", app_id, visible:show, nodes:[], floating_nodes:[]};
}
function xwayland(className, show) {
    return {type:"con", visible:show,
        window_properties:{class:className}, nodes:[], floating_nodes:[]};
}

const tray = {
    vesktop:{id:"dev.vencord.vesktop",title:"Vesktop"},
    lutris:{id:"net_lutris_Lutris",title:"Lutris"},
    unrelated:{id:"another.application",title:"Something else"}
};

const onDesktop = list(root(output(
    ws("1", wayland("vesktop",true), wayland("lutris",false)))));
assert.deepEqual(onDesktop, ["vesktop"]);
assert.equal(visible(tray.vesktop,onDesktop),true,
    "visible Vesktop stays active when pointer leaves");
assert.equal(visible(tray.lutris,onDesktop),false,
    "Lutris running but not visible has no active card");
assert.equal(visible(tray.unrelated,onDesktop),false);

const movedToOtherActiveOutput = list(root(
    output(ws("1", wayland("vesktop",false))),
    {type:"output",name:"HDMI-A-1", nodes:[
        ws("2", wayland("lutris",true))]
    }
));
assert.equal(visible(tray.vesktop,movedToOtherActiveOutput),false);
assert.equal(visible(tray.lutris,movedToOtherActiveOutput),true,
    "visible window on another active output counts as desktop-visible");

const floating = list(root(output({
    type:"workspace",name:"2",visible:true,nodes:[],
    floating_nodes:[xwayland("Lutris",true)]
})));
assert.equal(visible(tray.lutris,floating),true,
    "visible floating Xwayland app counts");

const scratch = list(root(output({
    type:"workspace",name:"__i3_scratch",nodes:[],
    floating_nodes:[xwayland("Lutris",false)]
})));
assert.equal(visible(tray.lutris,scratch),false,
    "hidden scratchpad item does not count");

const tabbed = list(root(output(ws("3",
    {type:"con",layout:"tabbed",visible:true,
      nodes:[wayland("vesktop",false),wayland("lutris",true)]}))));
assert.equal(visible(tray.vesktop,tabbed),false,
    "unselected tab should not light its icon");
assert.equal(visible(tray.lutris,tabbed),true);

const sameName = list(root(output(ws("4", wayland("fake-lutris-app",true)))));
assert.equal(visible(tray.lutris,sameName),false,
    "substring of a different app ID must not match Lutris");
const onlyVesktop = list(root(output(ws("5",wayland("vesktop",true)))));
assert.equal(visible({id:"discord",title:"Discord"},onlyVesktop),false,
    "Discord and Vesktop are separate identities");

assert.deepEqual(list("invalid JSON"),[]);
assert.deepEqual(list(""),[]);
assert.deepEqual(list("{}"),[]);
assert.deepEqual(list(JSON.stringify({type:"workspace",nodes:[]})),[]);
assert.equal(visible(tray.lutris,[]),false);
assert.equal(visible(null,onDesktop),false);
assert.equal(visible(tray.vesktop,["dev.vencord.vesktop"]),true);
assert.equal(visible(tray.lutris,["net.lutris.lutris"]),true);

// Event routing must be read-only and use an event subscription, not
// a continuously polling timer or privileged window action.
const qml = fs.readFileSync(
    path.resolve(__dirname,"../../modules/Tray.qml"),"utf8");
assert.match(qml,/I3IpcListener\s*\{\s*subscriptions:\s*\["window", "workspace", "output"\]/);
assert.match(qml,/command:\s*\["swaymsg", "-t", "get_tree", "-r"\]/);
assert.match(qml,/DesktopVisibility\.visibleWindowKeysFromTree\(/);
assert.match(qml,/DesktopVisibility\.hasVisibleDesktopWindow\(/);
assert.match(qml,/readonly property bool cardEmphasized:\s*trayButton\.appOnDesktop/);
assert.match(qml,/visible:\s*trayButton\.appOnDesktop/);
assert.doesNotMatch(qml,/cardEmphasized:\s*trayButton\.appRegistered/);
assert.doesNotMatch(qml,/command:\s*\["swaymsg", "[^"]+", "focus"/);
assert.doesNotMatch(qml,/\bQuickshell\.execDetached\(/);
console.log("Tray visible Sway windows: hidden, active, tabbed, floating, aliases PASS");
