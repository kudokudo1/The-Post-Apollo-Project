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
// Execute the real QML Lutris identity predicate as JavaScript. An exact
// registered app identity may use a Desktop ID or AppIndicator service ID.
const lutrisStart = "function isLutrisTrayItem(item) {";
assert.equal(source.split(lutrisStart).length - 1, 1);
const lutrisBody = source.split(lutrisStart, 2)[1].split(
    "\n    }\n\n    function openDiscordFromTray()", 1
)[0];
const isLutrisTrayItem = vm.runInNewContext(
    "(function(item) {" + lutrisBody + "\n})"
);
for (const id of ["lutris", "net.lutris.Lutris",
                  "net_lutris_Lutris", "net.lutris.Lutris.desktop"])
    assert.equal(isLutrisTrayItem({id}), true, id);
assert.equal(isLutrisTrayItem({title:"Lutris"}), true);
for (const id of ["vesktop", "org.kde.LutrisHelper", "fake-lutris-app"])
    assert.equal(isLutrisTrayItem({id}), false, id);

const context = {
    Qt: { LeftButton: 1, RightButton: 2 },
    trayButton: { modelData: {} },
    trayDock: {
        isDiscordTrayItem: () => false, isLutrisTrayItem,
        openDiscordFromTray: () => {}
    },
    trayNativeMenu: { open: () => {} },
};
const clicked = vm.runInNewContext("(function(mouse) {" + body + "\n})", context);
function click(button, settings) {
    let opens = 0, activates = 0, discord = 0;
    context.trayButton.modelData = {
        id: settings.id ?? "", title: settings.title ?? "",
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
assert.deepEqual(click(1, {id:"net.lutris.Lutris",hasMenu:true,menu:{}}),
    {opens:1,activates:0,discord:0},
    "Lutris left-click opens its own advertised menu when Activate may do nothing");
assert.deepEqual(click(1, {id:"lutris",hasMenu:false,menu:null}),
    {opens:0,activates:1,discord:0},
    "Lutris without a native menu retains normal activation fallback");
assert.deepEqual(click(1, {id:"another-app",hasMenu:true,menu:{}}),
    {opens:0,activates:1,discord:0},
    "another application's left-click activation is not replaced");
assert.deepEqual(click(2, {hasMenu:true,menu:{},discord:true}),
    {opens:1,activates:0,discord:0}, "right-click Discord remains native");

// The whole tray shares one computed accent regardless of what icon is under
// the mouse. This is the actual QML expression, not a reimplementation.
const colorStart = "readonly property color accentColor:";
assert.equal(source.split(colorStart).length - 1, 1);
const expression = source.split(colorStart,2)[1].split("\n\n",1)[0];
const Colors = {cyan:"#00ffff",magenta:"#ff00ff",orange:"#ff9900"};
function accent(pressed, hovered, menuOpen) {
    return vm.runInNewContext("(" + expression + ")", {
        trayButtonPressed:pressed, trayButtonHovered:hovered,
        trayMenuOpen:menuOpen, Colors
    });
}
assert.equal(accent(false,false,false),Colors.cyan,"idle tray cyan");
assert.equal(accent(false,true,false),Colors.orange,"hovered tray orange");
assert.equal(accent(true,false,false),Colors.orange,"pressed tray orange");
assert.equal(accent(false,false,true),Colors.magenta,"native menu open magenta");
assert.equal(accent(true,true,true),Colors.magenta,"open beats hovering and press");

const iconColorStart = "readonly property color iconAccentColor:";
assert.equal(source.split(iconColorStart).length - 1,1);
const iconExpression = source.split(iconColorStart,2)[1].split("\n\n",1)[0];
function iconAccent(registered, hovered, pressed) {
    return vm.runInNewContext("(" + iconExpression + ")", {
        trayButton:{appRegistered:registered},
        trayButtonMouse:{containsMouse:hovered,pressed:pressed},
        Colors
    });
}
// The app icon is born as a registered SNI delegate and remains open-colored
// after moving the pointer away or closing the native menu.
assert.equal(iconAccent(true,false,false),Colors.magenta,
    "registered application idle is open-magenta");
assert.equal(iconAccent(true,true,false),Colors.magenta,
    "hover must not clear the registered application's magenta identity");
assert.equal(iconAccent(true,false,true),Colors.magenta,
    "click must not clear the registered application's magenta identity");
assert.equal(iconAccent(false,false,false),Colors.cyan,
    "only an unregistered/fallback app icon can be idle cyan");
assert.equal(iconAccent(false,true,false),Colors.orange,
    "unregistered/fallback hover still orange");

// Exercise the QML registration predicate, not a synthetic local click flag.
const registeredStart = "readonly property bool appRegistered:";
assert.equal(source.split(registeredStart).length - 1, 1);
const registeredExpr = source.split(registeredStart,2)[1].split("\n\n",1)[0];
function registered(modelData) {
    return vm.runInNewContext("(" + registeredExpr + ")", {
        trayButton:{modelData}
    });
}
assert.equal(registered({id:"vesktop"}),true);
assert.equal(registered({id:"net.lutris.Lutris"}),true);
assert.equal(registered(null),false);
assert.equal(registered(undefined),false);
assert.match(source,/readonly property bool cardEmphasized:\s*trayButton\.appRegistered/);
assert.match(source,/visible:\s*trayButton\.appRegistered/);
assert.doesNotMatch(source,/readonly property bool cardEmphasized:\s*trayNativeMenu\.visible/);
assert.match(source,/trayMenuOpen \? 0\.72/);
assert.match(source,/trayMenuOpen \? 0\.18/);
assert.match(source,/onOpened: trayDock\.openMenuAnchor = trayNativeMenu/);
assert.match(source,/onClosed:\s*\{\s*if \(trayDock\.openMenuAnchor === trayNativeMenu\)/);
assert.match(source,/Component\.onDestruction:\s*\{\s*if \(trayDock\.openMenuAnchor === trayNativeMenu\)/);
assert.match(source,/border\.color:\s*accentColor/);
assert.equal((source.match(/color: trayDock\.accentColor/g)||[]).length,4);
assert.match(source,/HoverHandler\s*\{\s*id:\s*trayHoverHandler\s*blocking:\s*false/);
assert.match(source,/readonly property bool trayButtonHovered:\s*trayHoverHandler\.hovered/);
assert.doesNotMatch(source,/trayDock\.trayButtonHovered\s*=/);
assert.match(source,/text:\s*"TRAY"[\s\S]*?color:\s*trayDock\.accentColor/);
assert.match(source,/QsMenuAnchor\s*\{[\s\S]*?menu:\s*trayButton\.modelData\.menu/);
assert.match(source,/anchor\.item:\s*trayButton/);
assert.match(source,/anchor\.edges:\s*Edges\.Top/);
assert.match(source,/anchor\.gravity:\s*Edges\.Top/);
console.log("Tray native clicks, outer accent and persistent registered-app magenta/card: PASS");
