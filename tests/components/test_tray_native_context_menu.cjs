#!/usr/bin/env node
"use strict";
// Execute the exact onClicked QML JavaScript against isolated StatusNotifier
// doubles. This never creates a menu, clicks the desktop or changes app data.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(
    path.resolve(__dirname, "../../modules/Tray.qml"), "utf8"
);
const start = "onClicked: function (mouse) {";
const end = "\n                    }\n\n                    onWheel:";
assert.equal(source.split(start).length - 1, 1);
const body = source.split(start, 2)[1].split(end, 1)[0];
assert.ok(body.includes("trayNativeMenu.open();"));
const context = {
    Qt: { LeftButton: 1, RightButton: 2 },
    trayButton: { modelData: {} },
    trayDock: { isDiscordTrayItem: () => false, openDiscordFromTray: () => {} },
    trayNativeMenu: { open: () => {} },
};
const clicked = vm.runInNewContext("(function(mouse) {" + body + "\n})", context);
function click(button, settings) {
    let opens = 0, activates = 0, discord = 0;
    context.trayButton.modelData = {
        hasMenu: !!settings.hasMenu,
        onlyMenu: !!settings.onlyMenu,
        menu: settings.menu ?? null,
        activate: () => activates++
    };
    context.trayDock.isDiscordTrayItem = () => !!settings.discord;
    context.trayDock.openDiscordFromTray = () => discord++;
    context.trayNativeMenu.open = () => opens++;
    clicked({button});
    return {opens, activates, discord};
}
assert.deepEqual(click(2, {hasMenu:true,menu:{}}),
    {opens:1,activates:0,discord:0}, "right-click opens app-supplied menu");
assert.deepEqual(click(2, {hasMenu:false,menu:null}),
    {opens:0,activates:0,discord:0}, "no fabricated context action");
assert.deepEqual(click(2, {hasMenu:true,menu:null}),
    {opens:0,activates:0,discord:0}, "null menu is not opened");
assert.deepEqual(click(1, {hasMenu:true,menu:{},onlyMenu:true}),
    {opens:1,activates:0,discord:0}, "menu-only left click");
assert.deepEqual(click(1, {hasMenu:false,menu:null,onlyMenu:false}),
    {opens:0,activates:1,discord:0}, "normal app left activation");
assert.deepEqual(click(1, {hasMenu:true,menu:{},discord:true}),
    {opens:0,activates:0,discord:1}, "existing Vesktop bridge retained");
assert.deepEqual(click(2, {hasMenu:true,menu:{},discord:true}),
    {opens:1,activates:0,discord:0}, "right-click Discord remains native");

// The whole tray shares one computed accent regardless of what icon is under
// the mouse. This is the actual QML expression, not a reimplementation.
const colorStart = "readonly property color accentColor:";
assert.equal(source.split(colorStart).length - 1, 1);
const expression = source.split(colorStart,2)[1].split("\n\n",1)[0];
const Colors = {cyan:"#00ffff",magenta:"#ff00ff",orange:"#ff9900"};
function accent(pressed, hovered) {
    return vm.runInNewContext("(" + expression + ")", {
        trayButtonPressed:pressed, trayButtonHovered:hovered, Colors
    });
}
assert.equal(accent(false,false),Colors.cyan);
assert.equal(accent(false,true),Colors.magenta);
assert.equal(accent(true,true),Colors.orange);
assert.equal(accent(true,false),Colors.orange);
assert.match(source,/border\.color:\s*accentColor/);
assert.equal((source.match(/color: trayDock\.accentColor/g)||[]).length,4);
assert.match(source,/QsMenuAnchor\s*\{[\s\S]*?menu:\s*trayButton\.modelData\.menu/);
assert.match(source,/anchor\.item:\s*trayButton/);
assert.match(source,/anchor\.edges:\s*Edges\.Top/);
assert.match(source,/anchor\.gravity:\s*Edges\.Top/);
console.log("Tray native menu click dispatch and unified glow accent: PASS");
