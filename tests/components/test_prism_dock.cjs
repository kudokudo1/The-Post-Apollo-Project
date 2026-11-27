const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const base=path.resolve(__dirname,"../..");
const dock=fs.readFileSync(path.join(base,"modules/PrismDock.qml"),"utf8");
const shell=fs.readFileSync(path.join(base,"shell.qml"),"utf8");
const trash=fs.readFileSync(path.join(base,"modules/Trash.qml"),"utf8");

test("Prism uses the existing visual button as a standalone dock module",()=>{
    assert.match(dock,/PanelWindow\s*\{/);
    assert.match(dock,/PrismButton\s*\{/);
    assert.match(dock,/objectName: "postApolloPrismButton"/);
    assert.match(dock,/selected: prismDock.previewSelected/);
    assert.match(dock,/onLeftClicked: prismDock.previewSelected = !prismDock.previewSelected/);
    assert.match(shell,/Trash\s*\{[\s\S]*?\}\s*PrismDock\s*\{\}/);
});
test("Prism sits right of Trash without modifying Trash's button",()=>{
    assert.match(trash,/margins\s*\{\s*top: 0\s*bottom: 10\s*left: 10/);
    assert.match(trash,/id: trashButton\s+x: 15\s+y: trashArea.height - 60\s+width: 50\s+height: 50/);
    assert.match(dock,/margins\s*\{\s*top: 0\s*bottom: 10\s*left: 73/);
    assert.match(dock,/implicitWidth: 70\s+implicitHeight: 70/);
    assert.match(dock,/x: 10\s+y: 10\s+width: 50\s+height: 50/);
    const trashX=10+15,prismX=73+10;
    assert.equal(prismX-(trashX+50),8);
    assert.equal(10+(70-(10+50)),20);
});
test("Preview cannot claim a dictionary, keyboard focus or background work",()=>{
    assert.match(dock,/mask: Region\s*\{\s*item: prismButton/);
    assert.match(dock,/WlrLayershell.keyboardFocus: WlrKeyboardFocus.None/);
    assert.doesNotMatch(dock,/\b(?:Timer|Process|Loader|Popup|FileView|Connections)\s*\{/);
    assert.doesNotMatch(dock,/(?:save|remove|delete|trash|burn)\s*\(/);
});
