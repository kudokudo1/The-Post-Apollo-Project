// Prism's native dock and panel use the existing source of truth for sizing.
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const base=path.resolve(__dirname,"../..");
const dock=fs.readFileSync(path.join(base,"modules/PrismDock.qml"),"utf8");
const panel=fs.readFileSync(path.join(base,"widgets/PrismW.qml"),"utf8");
const shell=fs.readFileSync(path.join(base,"shell.qml"),"utf8");
const trash=fs.readFileSync(path.join(base,"modules/Trash.qml"),"utf8");
const tasks=fs.readFileSync(path.join(base,"widgets/TasksW.qml"),"utf8");
const sizing=fs.readFileSync(path.join(base,"widgets/TasksChassisPolicy.js"),"utf8");
const policy=vm.createContext({});
vm.runInContext(sizing.replace(/^\s*\.pragma library\s*/,""),policy);

test("Prism dock binds its open state to one real widget, not a cosmetic preview",()=>{
    assert.match(dock,/PanelWindow\s*\{/);
    assert.match(dock,/PrismButton\s*\{/);
    assert.match(dock,/objectName: "postApolloPrismButton"/);
    assert.match(dock,/selected: prismDock\.menuOpen/);
    assert.match(dock,/onLeftClicked: prismDock\.toggleRequested\(\)/);
    assert.match(shell,/menuOpen: prismWindow\.menuOpen/);
    assert.match(shell,/onToggleRequested: prismWindow\.toggle\(\)/);
    assert.match(shell,/PrismW\s*\{/);
    assert.ok(shell.indexOf("PrismW {")>shell.indexOf("PrismDock {"));
    assert.match(panel,/function toggle\(\) \{ menuOpen = !menuOpen; \}/);
    assert.match(panel,/onCloseRequested: root\.menuOpen = false/);
    assert.match(panel,/Keys\.onEscapePressed/);
});

test("Prism stays beside the original Trash dock with no new input stealing",()=>{
    assert.match(trash,/margins\s*\{\s*top: 0\s*bottom: 10\s*left: 10/);
    assert.match(trash,/id: trashButton\s+x: 15\s+y: trashArea.height - 60\s+width: 50\s+height: 50/);
    assert.match(dock,/margins\s*\{\s*top: 0\s*bottom: 10\s*left: 73/);
    assert.match(dock,/implicitWidth: 70\s+implicitHeight: 70/);
    assert.match(dock,/x: 10\s+y: 10\s+width: 50\s+height: 50/);
    assert.equal((73+10)-(10+15+50),8);
    assert.equal(10+(70-(10+50)),20);
    assert.match(dock,/mask: Region\s*\{\s*item: prismButton/);
    assert.match(panel,/visible: true/);\n    assert.match(panel,/mask: Region\\s*\\{/);
    assert.match(panel,/width: root\.menuOpen \? root\.frameWidth : 0/);
    assert.match(panel,/height: root\.menuOpen \? root\.frameHeight : 0/);
    assert.match(panel,/focusable: menuOpen/);
    assert.match(panel,/WlrKeyboardFocus\.OnDemand : WlrKeyboardFocus\.None/);
});

test("To-do's exact portrait levels and sizing function own Prism geometry",()=>{
    assert.match(panel,/import "TasksChassisPolicy\.js" as TasksChassisPolicy/);
    assert.match(panel,/TasksChassisPolicy\.frame\(/);
    assert.match(panel,/TasksChassisPolicy\.step\(chassisLevel, 1\)/);
    assert.match(panel,/TasksChassisPolicy\.step\(chassisLevel, -1\)/);
    assert.match(tasks,/TasksChassisPolicy\.frame\(/);
    assert.deepEqual(Array.from(policy.levels),["compact","expanded","large"]);
    for(const [level,w,h] of [
        ["compact",432,790],["expanded",560,1020],["large",760,1345]
    ]) {
        const target=policy.frame(level,2560,2000,12,9,12);
        assert.equal(target.width,w,level+" width");
        assert.equal(target.height,h,level+" height");
    }
    assert.match(panel,/direction: "down"/);
    assert.match(panel,/direction: "up"/);
    assert.match(panel,/available: root\.chassisLevel !== "compact"/);
    assert.match(panel,/available: root\.chassisLevel !== "large"/);
});

test("Prism inherits Trash's actual 165-pixel vertical reserve",()=>{
    assert.match(trash,/readonly property int fullHeightReserve: 70 \+ 10 \+ 85/);
    assert.match(shell,/fullHeightReserve: trashWindow\.fullHeightReserve/);
    assert.match(panel,/Math\.max\(1, usableScreenHeight - fullHeightReserve\)/);
    assert.match(panel,/Math\.min\(tasksChassisFrame\.height, maximumFrameHeight\)/);
    assert.match(panel,/Math\.floor\(frameHeight \* 0\.58\)/);
    for(const screenHeight of [900,1080,1440,2000]) {
        for(const level of Array.from(policy.levels)) {
            const target=policy.frame(level,2560,screenHeight,12,9,12);
            const height=Math.min(target.height,Math.max(1,screenHeight-165));
            const width=Math.min(target.width,Math.floor(height*.58));
            assert.ok(height<=screenHeight-165);
            assert.ok(width<=height*.58);
        }
    }
});

test("Full Prism uses standard window controls but claims no invented dictionary",()=>{
    assert.match(panel,/WindowPanelFrame\s*\{/);
    assert.match(panel,/ResizeButton\s*\{/);
    assert.match(panel,/CloseButton\s*\{/);
    assert.match(panel,/borderWidth: 1/);
    assert.match(panel,/NO DEFINITIONS YET/);
    assert.doesNotMatch(panel,/\b(?:Process|FileView|Popup|Timer)\s*\{/);
    assert.doesNotMatch(dock,/(?:save|remove|delete|trash|burn)\s*\(/);
});
