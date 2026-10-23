#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubLayout.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const layout=vm.createContext({});
vm.runInContext(source,layout,{filename:"ApolloHubLayout.js"});

const toPlain=value=>JSON.parse(JSON.stringify(value));
const allTiles=value=>value.modes.flatMap(mode=>
    mode.subModes.flatMap(group=>group.tiles));
const validateIds=value=>{
    const ids=allTiles(value).map(t=>t.id);
    assert.equal(new Set(ids).size,ids.length);
    assert.ok(ids.every(id=>/^tile-[1-9][0-9]*$/.test(id)));
};
const original=layout.defaultLayout();
assert.equal(original.version,2);
assert.equal(original.nextTileId,12);
assert.equal(original.modes.length,3);
assert.equal(allTiles(original).length,11);
validateIds(original);
assert.equal(original.modes[0].subModes[0].tiles[0].module,"time");
assert.equal(original.modes[0].subModes[0].tiles[0].size,"half");
assert.equal(original.modes[1].subModes[0].tiles[0].size,"wide");
assert.equal(allTiles(original).every(t=>t.rowSpan===1),true);

// Faithful v1 migration: modes, groups, positions, icons, half/wide widths,
// module IDs and names retain their order and meaning.
const v1=toPlain(original);
v1.version=1;
delete v1.nextTileId;
v1.modes.forEach(mode=>mode.subModes.forEach(group=>
    group.tiles.forEach(tile=>{delete tile.id;delete tile.rowSpan;})));
const fromV1=layout.parse(JSON.stringify(v1));
assert.equal(fromV1.version,2);
assert.deepEqual(toPlain(fromV1),toPlain(original));
assert.equal(JSON.stringify(v1).includes('"rowSpan"'),false);
assert.equal(layout.storageIssue(JSON.stringify(v1)),"");
const noVersion=toPlain(v1);
delete noVersion.version;
assert.deepEqual(toPlain(layout.parse(JSON.stringify(noVersion))),
                 toPlain(original));
assert.equal(layout.storageIssue(JSON.stringify(noVersion)),"");
assert.deepEqual(toPlain(layout.normalize(original)),toPlain(original));
assert.deepEqual(toPlain(layout.parse(JSON.stringify(original))),
                 toPlain(original));
validateIds(fromV1);

// No writes over corrupted or future versions. The window honors this issue
// before attempting to persist a fallback layout.
assert.equal(layout.storageIssue(""),"");
assert.equal(layout.storageIssue("   "),"");
assert.equal(layout.storageIssue("{"),"INVALID_JSON");
assert.equal(layout.storageIssue("{}"),"INVALID_LAYOUT");
assert.equal(layout.storageIssue("null"),"INVALID_LAYOUT");
assert.equal(layout.storageIssue("[]"),"INVALID_LAYOUT");
assert.equal(layout.storageIssue(JSON.stringify({...v1,version:3})),
             "UNSUPPORTED_VERSION");
assert.equal(layout.storageIssue(JSON.stringify({...v1,version:99})),
             "UNSUPPORTED_VERSION");

// Removing the middle item affects only the selected submode's placement,
// not sibling groups, source module objects, data stores or source argument.
const beforeRemoval=JSON.stringify(fromV1);
const removed=layout.removeTile(fromV1,0,0,2);
assert.equal(removed.modes[0].subModes[0].tiles.length,5);
assert.equal(removed.modes[0].subModes[0].tiles[2].module,"weather");
assert.equal(removed.modes[1].subModes[0].tiles.length,3);
assert.equal(allTiles(removed).length,10);
assert.equal(JSON.stringify(fromV1),beforeRemoval);
assert.equal(removed.nextTileId,fromV1.nextTileId);
assert.equal(removed.modes[0].subModes[0].tiles.some(t=>t.module==="calendar"),false);
assert.equal(removed.version,2);
validateIds(removed);
const restored=layout.parse(beforeRemoval); // same bytes stored for Undo
assert.deepEqual(toPlain(restored),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,0,0,-1)),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,0,0,999)),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,0,0,0.5)),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,99,0,0)),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,0,99,0)),toPlain(fromV1));
assert.deepEqual(toPlain(layout.removeTile(fromV1,0,0,"1")),toPlain(fromV1));
const noTiles=layout.removeTile(removed,0,0,0);
assert.equal(noTiles.modes[0].subModes[0].tiles.length,4);
let emptied=toPlain(original);
while(emptied.modes[0].subModes[0].tiles.length)
    emptied=layout.removeTile(emptied,0,0,0);
assert.equal(emptied.modes[0].subModes[0].tiles.length,0);
assert.equal(emptied.modes.length,3); // empty group remains available
assert.equal(emptied.modes[0].subModes.length,1);

// Add after removal allocates a new stable tile ID, never reuses deleted ID.
const readded=layout.addTile(removed,0,0);
assert.equal(readded.version,2);
assert.equal(readded.nextTileId,13);
assert.equal(readded.modes[0].subModes[0].tiles.length,6);
assert.equal(readded.modes[0].subModes[0].tiles[5].id,"tile-12");
assert.equal(readded.modes[0].subModes[0].tiles[5].rowSpan,1);
validateIds(readded);
// Repeated normalization and swap/cycle do not discard dimensions or IDs.
const taller=layout.resizeTile(readded,0,0,0,"wide",3);
assert.equal(taller.modes[0].subModes[0].tiles[0].rowSpan,3);
assert.equal(taller.modes[0].subModes[0].tiles[0].size,"wide");
assert.equal(readded.modes[0].subModes[0].tiles[0].rowSpan,1);
assert.deepEqual(toPlain(layout.parse(JSON.stringify(taller))),toPlain(taller));
const swapped=layout.swapTiles(taller,0,0,0,1);
assert.equal(swapped.modes[0].subModes[0].tiles[1].id,
             taller.modes[0].subModes[0].tiles[0].id);
assert.equal(swapped.modes[0].subModes[0].tiles[1].rowSpan,3);
const cycled=layout.cycleTile(swapped,0,0,1);
assert.equal(cycled.modes[0].subModes[0].tiles[1].id,
             swapped.modes[0].subModes[0].tiles[1].id);
assert.equal(cycled.modes[0].subModes[0].tiles[1].rowSpan,3);
assert.deepEqual(toPlain(layout.resizeTile(taller,0,0,0,"wide",4)),
                 toPlain(taller));
assert.deepEqual(toPlain(layout.resizeTile(taller,0,0,0,"large",2)),
                 toPlain(taller));
assert.deepEqual(toPlain(layout.resizeTile(taller,0,0,33,"half",1)),
                 toPlain(taller));

// UI W:1/W:2 and H:1/H:2/H:3 cycle through the supported ranges.
// A resize is layout metadata only. It never changes the module or its ID.
const resizeBase = layout.defaultLayout();
const originalFirst = resizeBase.modes[0].subModes[0].tiles[0];
let stepped = resizeBase;
for (const expected of [
    ["wide",1], ["wide",2], ["wide",3], ["wide",1], ["half",1]
]) {
    stepped = layout.resizeTile(stepped,0,0,0,expected[0],expected[1]);
    const tile = stepped.modes[0].subModes[0].tiles[0];
    assert.equal(tile.size,expected[0]);
    assert.equal(tile.rowSpan,expected[1]);
    assert.equal(tile.id,originalFirst.id);
    assert.equal(tile.module,originalFirst.module);
    validateIds(stepped);
    assert.deepEqual(toPlain(layout.parse(JSON.stringify(stepped))),
                     toPlain(stepped));
}
assert.deepEqual(toPlain(stepped),toPlain(resizeBase));
const alreadyTall=layout.resizeTile(resizeBase,0,0,2,"wide",3);
const adjacent=alreadyTall.modes[0].subModes[0].tiles[3];
assert.equal(adjacent.rowSpan,1); // no resizing siblings
assert.equal(adjacent.size,"half");
const moved=layout.swapTiles(alreadyTall,0,0,2,3);
assert.equal(moved.modes[0].subModes[0].tiles[3].rowSpan,3);
assert.equal(moved.modes[0].subModes[0].tiles[2].rowSpan,1);
const reversed=layout.swapTiles(moved,0,0,3,2);
assert.deepEqual(toPlain(reversed),toPlain(alreadyTall));
assert.deepEqual(toPlain(resizeBase),toPlain(original));
assert.equal(layout.MAX_ROW_SPAN,3);
for(const badSpan of [-1,0,1.5,4,"2",null,Infinity,NaN]){
    assert.deepEqual(toPlain(layout.resizeTile(resizeBase,0,0,0,"half",badSpan)),
                     toPlain(resizeBase));
}


const duplicateIds=toPlain(taller);
duplicateIds.modes[0].subModes[0].tiles[1].id=
    duplicateIds.modes[0].subModes[0].tiles[0].id;
const repaired=layout.normalize(duplicateIds);
validateIds(repaired);
assert.equal(repaired.modes[0].subModes[0].tiles[0].id,
             duplicateIds.modes[0].subModes[0].tiles[0].id);
assert.equal(repaired.modes[0].subModes[0].tiles[1].id.startsWith("tile-"),true);
assert.equal(repaired.nextTileId>taller.nextTileId,true);

const badSpan=toPlain(taller);
badSpan.modes[0].subModes[0].tiles[0].rowSpan=Infinity;
assert.equal(layout.normalize(badSpan).modes[0].subModes[0].tiles[0].rowSpan,1);
const noSpan=toPlain(taller);
delete noSpan.modes[0].subModes[0].tiles[0].rowSpan;
assert.equal(layout.normalize(noSpan).modes[0].subModes[0].tiles[0].rowSpan,1);

// P1 Stage 3: explicit mode/group confirmation, stable identity, and
// minimum-one protections. Removing a layout branch must never rewrite the
// remaining tile IDs, content models or next-ID counter.
const hierarchy=layout.defaultLayout();
const hierarchyOriginal=JSON.stringify(hierarchy);
const modeToRemove=hierarchy.modes[1];
const groupToRemove=hierarchy.modes[0].subModes[0];
const rejectedMode=layout.removeMode(hierarchy,1,modeToRemove.id,false);
assert.deepEqual(toPlain(rejectedMode),toPlain(hierarchy));
assert.deepEqual(toPlain(layout.removeMode(hierarchy,1,"wrong-id",true)),
                 toPlain(hierarchy));
assert.deepEqual(toPlain(layout.removeMode(hierarchy,99,modeToRemove.id,true)),
                 toPlain(hierarchy));
assert.deepEqual(toPlain(layout.removeMode(hierarchy,-1,modeToRemove.id,true)),
                 toPlain(hierarchy));
assert.deepEqual(toPlain(layout.removeMode(hierarchy,0.5,modeToRemove.id,true)),
                 toPlain(hierarchy));
assert.deepEqual(toPlain(layout.removeMode(hierarchy,1,modeToRemove.id,1)),
                 toPlain(hierarchy));
const modeRemoved=layout.removeMode(hierarchy,1,modeToRemove.id,true);
assert.equal(modeRemoved.modes.length,2);
assert.equal(modeRemoved.modes.some(m=>m.id===modeToRemove.id),false);
assert.equal(modeRemoved.modes[0].id,hierarchy.modes[0].id);
assert.equal(modeRemoved.modes[1].id,hierarchy.modes[2].id);
assert.equal(modeRemoved.nextTileId,hierarchy.nextTileId);
validateIds(modeRemoved);
assert.equal(JSON.stringify(hierarchy),hierarchyOriginal);
assert.deepEqual(toPlain(layout.parse(hierarchyOriginal)),toPlain(hierarchy));
// Last remaining mode is protected, even with explicit confirmation.
const lastModeLayout=layout.removeMode(
    modeRemoved,1,modeRemoved.modes[1].id,true);
assert.equal(lastModeLayout.modes.length,1);
assert.deepEqual(toPlain(layout.removeMode(
    lastModeLayout,0,lastModeLayout.modes[0].id,true)),
    toPlain(lastModeLayout));
assert.equal(layout.parse(JSON.stringify(lastModeLayout)).modes.length,1);

// A default mode has only one group; it must be impossible to leave it
// with zero groups or silently recreate the entire default configuration.
assert.deepEqual(toPlain(layout.removeSubMode(
    hierarchy,0,0,groupToRemove.id,true)),toPlain(hierarchy));
const withGroup=layout.addSubMode(hierarchy,0);
assert.equal(withGroup.modes[0].subModes.length,2);
const secondGroup=withGroup.modes[0].subModes[1];
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,0,1,secondGroup.id,false)),toPlain(withGroup));
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,0,1,secondGroup.id,undefined)),toPlain(withGroup));
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,0,1,"wrong-group",true)),toPlain(withGroup));
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,0,99,secondGroup.id,true)),toPlain(withGroup));
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,9,1,secondGroup.id,true)),toPlain(withGroup));
assert.deepEqual(toPlain(layout.removeSubMode(
    withGroup,0,1,secondGroup.id,"true")),toPlain(withGroup));
const secondGone=layout.removeSubMode(withGroup,0,1,secondGroup.id,true);
assert.equal(secondGone.modes[0].subModes.length,1);
assert.equal(secondGone.modes[0].subModes[0].id,groupToRemove.id);
assert.equal(secondGone.nextTileId,withGroup.nextTileId);
validateIds(secondGone);
assert.deepEqual(toPlain(layout.removeSubMode(
    secondGone,0,0,groupToRemove.id,true)),toPlain(secondGone));

// Group removal can also remove a populated group and its placements,
// without mutating the sibling group or the persisted module's own data.
const filled=layout.addTile(withGroup,0,1);
const filledId=filled.modes[0].subModes[1].id;
const siblingBefore=toPlain(filled.modes[0].subModes[0]);
const savedBeforeGroupRemoval=JSON.stringify(filled);
const afterGroupRemoval=layout.removeSubMode(filled,0,1,filledId,true);
assert.deepEqual(toPlain(afterGroupRemoval.modes[0].subModes[0]),siblingBefore);
assert.equal(afterGroupRemoval.nextTileId,filled.nextTileId);
assert.equal(afterGroupRemoval.modes[0].subModes.length,1);
assert.equal(JSON.stringify(filled),savedBeforeGroupRemoval);
assert.deepEqual(toPlain(layout.parse(savedBeforeGroupRemoval)),toPlain(filled));

// Undo uses the existing captured previous JSON layout without allocating
// new identities or defaulting to another mode/group.
assert.deepEqual(toPlain(layout.parse(JSON.stringify(modeRemoved))),
                 toPlain(modeRemoved));
assert.deepEqual(toPlain(layout.parse(JSON.stringify(afterGroupRemoval))),
                 toPlain(afterGroupRemoval));

// P1 Stage 4: the full module list appears when search is empty.
// Choices preserve order, identify the current module, and exclude duplicates
// already placed elsewhere in the SAME group, not across other groups.
const chooserLayout=layout.defaultLayout();
const firstTile=chooserLayout.modes[0].subModes[0].tiles[0];
const chooser=layout.moduleChoices(chooserLayout,0,0,0,"");
assert.equal(chooser.state,"ready");
assert.equal(chooser.query,"");
assert.equal(chooser.total,10);
assert.equal(chooser.matchCount,10);
assert.equal(chooser.items.length,10);
// The policy runs in a separate VM realm, so convert its array to plain JS.
assert.deepEqual(toPlain(chooser.items.map(row=>row.id)),Array.from(layout.MODULE_IDS));
assert.equal(chooser.items.filter(row=>row.selected).length,1);
assert.equal(chooser.items.find(row=>row.selected).id,"time");
assert.equal(chooser.items.find(row=>row.id==="todo").inUse,true);
assert.equal(chooser.items.find(row=>row.id==="todo").available,false);
assert.equal(chooser.items.find(row=>row.id==="apps").available,true);
assert.equal(chooser.items.find(row=>row.id==="time").available,false);
assert.equal(chooser.availableCount,4);
assert.equal(chooser.items.find(row=>row.id==="cpu").title,"CPU++");

const queryCpu=layout.moduleChoices(chooserLayout,0,0,0," CpU ");
assert.equal(queryCpu.state,"ready");
assert.equal(queryCpu.query,"cpu");
assert.equal(queryCpu.matchCount,1);
assert.equal(queryCpu.availableCount,1);
assert.equal(queryCpu.items[0].id,"cpu");
assert.equal(queryCpu.items[0].available,true);
const queryDisplay=layout.moduleChoices(chooserLayout,0,0,0,"app launcher");
assert.equal(queryDisplay.matchCount,1);
assert.equal(queryDisplay.items[0].id,"apps");
assert.equal(layout.moduleChoices(chooserLayout,0,0,0,"").matchCount,10);
assert.equal(layout.moduleChoices(chooserLayout,0,0,0,"zzzzz").matchCount,0);
assert.equal(layout.moduleChoices(chooserLayout,0,0,0,42).matchCount,10);
assert.equal(layout.moduleChoices(chooserLayout,0,0,0,"x".repeat(120)).query.length,80);
assert.equal(layout.moduleChoices(chooserLayout,0,0,99,"").state,"unavailable");
assert.equal(layout.moduleChoices(chooserLayout,0,99,0,"").state,"unavailable");
assert.equal(layout.moduleChoices(chooserLayout,99,0,0,"").state,"unavailable");
assert.equal(layout.moduleChoices(null,0,0,0,"").state,"unavailable");
assert.equal(layout.moduleChoices({},0,0,0,"").state,"unavailable");

// Selecting an available module changes only one placement; undo restores.
const chooserBefore=JSON.stringify(chooserLayout);
const selected=layout.setTileModule(chooserLayout,0,0,0,firstTile.id,"apps");
assert.equal(selected.modes[0].subModes[0].tiles[0].module,"apps");
assert.equal(selected.modes[0].subModes[0].tiles[0].id,firstTile.id);
assert.equal(selected.modes[0].subModes[0].tiles[0].size,firstTile.size);
assert.equal(selected.modes[0].subModes[0].tiles[0].rowSpan,firstTile.rowSpan);
assert.equal(selected.nextTileId,chooserLayout.nextTileId);
assert.equal(JSON.stringify(chooserLayout),chooserBefore);
validateIds(selected);
assert.deepEqual(toPlain(layout.parse(JSON.stringify(selected))),toPlain(selected));
assert.deepEqual(toPlain(layout.parse(chooserBefore)),toPlain(chooserLayout));
assert.equal(layout.moduleChoices(selected,0,0,0,"apps").items[0].selected,true);

// Selecting used/unrecognized modules or stale targets does not mutate.
for(const [mode,group,tile,id,candidate] of [
    [0,0,0,firstTile.id,"todo"], // already in the same group
    [0,0,0,firstTile.id,"weather"],
    [0,0,0,firstTile.id,"not-a-module"],
    [0,0,0,"wrong-id","apps"],
    [0,0,0,"","apps"],
    [0,0,99,firstTile.id,"apps"],
    [0,99,0,firstTile.id,"apps"],
    [99,0,0,firstTile.id,"apps"],
    [0,0,0,firstTile.id,null],
]){
    assert.deepEqual(
        toPlain(layout.setTileModule(chooserLayout,mode,group,tile,id,candidate)),
        toPlain(chooserLayout));
}
// A module used in ANOTHER mode remains selectable here.
assert.equal(layout.moduleChoices(chooserLayout,0,0,0,"apps").availableCount,1);
// No-op current selection must not generate an undo change.
assert.deepEqual(toPlain(layout.setTileModule(
    chooserLayout,0,0,0,firstTile.id,"time")),toPlain(chooserLayout));
// ID plus width/height must survive changing the same tile a second time.
const resizedChoice=layout.resizeTile(chooserLayout,0,0,0,"wide",3);
const resultSized=layout.setTileModule(
    resizedChoice,0,0,0,firstTile.id,"network");
assert.equal(resultSized.modes[0].subModes[0].tiles[0].size,"wide");
assert.equal(resultSized.modes[0].subModes[0].tiles[0].rowSpan,3);
assert.equal(resultSized.modes[0].subModes[0].tiles[0].id,firstTile.id);

// Stage 5: MOVE transports a tile RECORD (never recreates it).
// Destination chooser is read-only; no target includes the source group.
const moveBase=layout.defaultLayout();
const moveSource=moveBase.modes[0].subModes[0].tiles[0];
const moveBaseJSON=JSON.stringify(moveBase);
const moveList=layout.moveTargets(moveBase,0,0,0);
assert.equal(moveList.state,"ready");
assert.equal(moveList.total,2);
assert.equal(moveList.availableCount,1);
assert.equal(moveList.items.some(row=>row.modeId==="dashboard"
        && row.groupId==="overview"),false);
const toConsole=moveList.items.find(row=>row.modeId==="console");
const toMedia=moveList.items.find(row=>row.modeId==="media");
assert.equal(toConsole.available,true);
assert.equal(toConsole.label,"Console / Quick");
assert.equal(toMedia.available,false);
assert.equal(toMedia.reason,"IN USE");
assert.equal(layout.moveTargets(moveBase,99,0,0).state,"unavailable");
assert.equal(layout.moveTargets(moveBase,0,99,0).state,"unavailable");
assert.equal(layout.moveTargets(moveBase,0,0,99).state,"unavailable");
assert.equal(layout.moveTargets(null,0,0,0).state,"unavailable");
const moveTo=(value,sm,sg,si,tileId,sourceModeId,sourceGroupId,
              dm,dg,destModeId,destGroupId)=>layout.transferTile(
    value,sm,sg,si,tileId,sourceModeId,sourceGroupId,
    dm,dg,destModeId,destGroupId);
const originalMode=moveBase.modes[0];
const sourceGroup=originalMode.subModes[0];
const destinationMode=moveBase.modes[1];
const destinationGroup=destinationMode.subModes[0];
const movedCrossMode=moveTo(moveBase,0,0,0,moveSource.id,
    originalMode.id,sourceGroup.id,1,0,destinationMode.id,destinationGroup.id);
assert.equal(movedCrossMode.modes[0].subModes[0].tiles.length,5);
assert.equal(movedCrossMode.modes[1].subModes[0].tiles.length,4);
assert.equal(JSON.stringify(moveBase),moveBaseJSON);
assert.equal(movedCrossMode.nextTileId,moveBase.nextTileId);
assert.deepEqual(toPlain(movedCrossMode.modes[1].subModes[0].tiles[3]),
                 toPlain(moveSource));
assert.equal(movedCrossMode.modes[0].subModes[0].tiles.some(t=>t.id===moveSource.id),false);
assert.deepEqual(toPlain(layout.parse(JSON.stringify(movedCrossMode))),
                 toPlain(movedCrossMode));
assert.deepEqual(toPlain(layout.parse(moveBaseJSON)),toPlain(moveBase));
validateIds(movedCrossMode);

// The same module cannot be duplicated within a destination group.
const duplicateRejected=moveTo(moveBase,0,0,0,moveSource.id,
    originalMode.id,sourceGroup.id,2,0,"media","player");
assert.deepEqual(toPlain(duplicateRejected),toPlain(moveBase));
// Invalid/stale references, same group, and fake confirmation remain no-ops.
for(const [sm,sg,si,id,mid,gid,dm,dg,dmid,dgid] of [
    [0,0,0,"old-tile","dashboard","overview",1,0,"console","quick"],
    [0,0,0,moveSource.id,"wrong","overview",1,0,"console","quick"],
    [0,0,0,moveSource.id,"dashboard","wrong",1,0,"console","quick"],
    [0,0,0,moveSource.id,"dashboard","overview",1,0,"wrong","quick"],
    [0,0,0,moveSource.id,"dashboard","overview",1,0,"console","wrong"],
    [0,0,0,moveSource.id,"dashboard","overview",0,0,"dashboard","overview"],
    [0,0,99,moveSource.id,"dashboard","overview",1,0,"console","quick"],
    [99,0,0,moveSource.id,"dashboard","overview",1,0,"console","quick"],
    [0,99,0,moveSource.id,"dashboard","overview",1,0,"console","quick"],
    [0,0,0,moveSource.id,"dashboard","overview",99,0,"console","quick"],
    [0,0,0,moveSource.id,"dashboard","overview",1,99,"console","quick"],
    [0,0,"0",moveSource.id,"dashboard","overview",1,0,"console","quick"],
]){
    assert.deepEqual(toPlain(moveTo(moveBase,sm,sg,si,id,mid,gid,dm,dg,dmid,dgid)),
                     toPlain(moveBase));
}

// Moving within the SAME main mode, to another submode, is supported.
const extraGroup=layout.addSubMode(moveBase,0);
const extraGroupId=extraGroup.modes[0].subModes[1].id;
const tallBefore=layout.resizeTile(extraGroup,0,0,0,"wide",3);
const beforeTall=tallBefore.modes[0].subModes[0].tiles[0];
const movedGroup=moveTo(tallBefore,0,0,0,beforeTall.id,
    "dashboard","overview",0,1,"dashboard",extraGroupId);
assert.deepEqual(toPlain(movedGroup.modes[0].subModes[1].tiles[0]),
                 toPlain(beforeTall));
assert.equal(movedGroup.modes[0].subModes[1].tiles[0].rowSpan,3);
assert.equal(movedGroup.modes[0].subModes[1].tiles[0].size,"wide");
assert.equal(movedGroup.nextTileId,tallBefore.nextTileId);
assert.equal(layout.moveTargets(tallBefore,0,0,0).total,3);

// A completely full destination refuses transfer, even with no duplicate.
// Use the existing policy to fill a dedicated empty group with eight tiles.
let fullCase=layout.addSubMode(moveBase,1);
const fullId=fullCase.modes[1].subModes[1].id;
for(let i=0;i<8;i++) fullCase=layout.addTile(fullCase,1,1);
assert.equal(fullCase.modes[1].subModes[1].tiles.length,8);
const fullChoices=layout.moveTargets(fullCase,0,0,0);
const blocked=fullChoices.items.find(t=>t.groupId===fullId);
assert.equal(blocked.available,false);
assert.equal(blocked.reason,"FULL");
const fullAttempt=moveTo(fullCase,0,0,0,
    fullCase.modes[0].subModes[0].tiles[0].id,
    "dashboard","overview",1,1,"console",fullId);
assert.deepEqual(toPlain(fullAttempt),toPlain(fullCase));
// Unchanged document means the UI must not add a new UNDO checkpoint.

// Stage 6: packed 2-column grid fills cells next to taller tiles without
// writing/reordering the persisted layout array or allocating identities.
const packBase=layout.defaultLayout();
const packJSON=JSON.stringify(packBase);
const packedNormal=layout.packTiles(packBase.modes[0].subModes[0].tiles);
assert.equal(packedNormal.state,"ready");
assert.equal(packedNormal.columns,2);
assert.equal(packedNormal.rows,3);
assert.equal(packedNormal.items.length,6);
assert.deepEqual(toPlain(packedNormal.items.map(p=>[p.column,p.row])),[
    [0,0],[1,0],[0,1],[1,1],[0,2],[1,2]
]);
const tallGrid=layout.resizeTile(packBase,0,0,0,"half",3);
const tallPack=layout.packTiles(tallGrid.modes[0].subModes[0].tiles);
assert.equal(tallPack.rows,4); // old Flow required five full 148px rows
assert.deepEqual(toPlain(tallPack.items.map(p=>[p.column,p.row])),[
    [0,0],[1,0],[1,1],[1,2],[0,3],[1,3]
]);
assert.equal(tallPack.items[0].columnSpan,1);
assert.equal(tallPack.items[0].rowSpan,3);
assert.equal(JSON.stringify(packBase),packJSON);
assert.deepEqual(toPlain(layout.parse(JSON.stringify(tallGrid))),
                 toPlain(tallGrid));
assert.deepEqual(toPlain(tallGrid.modes[0].subModes[0].tiles.map(t=>t.id)),
                 toPlain(packBase.modes[0].subModes[0].tiles.map(t=>t.id)));
const widePack=layout.packTiles(packBase.modes[1].subModes[0].tiles);
assert.deepEqual(toPlain(widePack.items.map(p=>[p.column,p.row,p.columnSpan])),[
    [0,0,2],[0,1,1],[1,1,1]
]);
assert.equal(widePack.rows,2);
const wideTall=layout.resizeTile(packBase,1,0,1,"half",3);
assert.equal(layout.packTiles(wideTall.modes[1].subModes[0].tiles).rows,4);

// The same first-fit algorithm also backfills holes left by a wide tile
// placed after a tall half-width tile. No tile overlaps another cell.
const sparse=[
    {id:"tile-1",module:"time",size:"half",rowSpan:3},
    {id:"tile-2",module:"apps",size:"wide",rowSpan:1},
    {id:"tile-3",module:"notes",size:"half",rowSpan:1},
    {id:"tile-4",module:"weather",size:"half",rowSpan:1}
];
const sparseGrid=layout.packTiles(sparse);
assert.deepEqual(toPlain(sparseGrid.items.map(p=>[p.column,p.row])),[
    [0,0],[0,3],[1,0],[1,1]
]);
assert.equal(sparseGrid.rows,4);
const ensureNoOverlap=(grid)=>{
    const cells=new Set();
    let maxRow=0;
    for(const p of grid.items){
        assert.ok(p.column>=0 && p.column+p.columnSpan<=2);
        assert.ok(p.row>=0 && p.rowSpan>=1 && p.rowSpan<=3);
        for(let y=p.row;y<p.row+p.rowSpan;y++){
            for(let x=p.column;x<p.column+p.columnSpan;x++){
                const cell=x+":"+y;
                assert.equal(cells.has(cell),false,cell);
                cells.add(cell);
                maxRow=Math.max(maxRow,y+1);
            }
        }
    }
    assert.equal(maxRow,grid.rows);
};
for(const check of [packedNormal,tallPack,widePack,sparseGrid])
    ensureNoOverlap(check);

// Exhaustively probe all 2-column-width and three-row-height variants for
// four tiles. The packing remains deterministic and has no overlap.
for(let bits=0;bits<16;bits++){
    for(let spans=0;spans<81;spans++){
        let code=spans;
        const records=[];
        for(let i=0;i<4;i++){
            records.push({
                id:"tile-"+(i+1),
                module:["time","apps","weather","notes"][i],
                size:(bits&(1<<i))?"wide":"half",
                rowSpan:code%3+1
            });
            code=Math.floor(code/3);
        }
        const before=JSON.stringify(records);
        const grid=layout.packTiles(records);
        assert.equal(grid.state,"ready");
        assert.equal(grid.items.length,records.length);
        ensureNoOverlap(grid);
        assert.equal(JSON.stringify(records),before);
        assert.deepEqual(toPlain(grid),toPlain(layout.packTiles(records)));
    }
}
assert.deepEqual(toPlain(layout.packTiles([])),
                 {state:"ready",columns:2,rows:0,items:[]});
const maximal=Array.from({length:8},(_,i)=>({
    id:"tile-"+(i+1),module:layout.MODULE_IDS[i],
    size:"wide",rowSpan:3
}));
assert.equal(layout.packTiles(maximal).rows,24);
for(const bad of [null,undefined,{},42,"",Array(9).fill(sparse[0]),
                   [{module:"time",size:"oversized",rowSpan:1}],
                   [{module:"time",size:"half",rowSpan:0}],
                   [{module:"time",size:"half",rowSpan:4}],
                   [{module:"unknown",size:"half",rowSpan:1}]]){
    assert.equal(layout.packTiles(bad).state,"unavailable");
    assert.equal(layout.packTiles(bad).items.length,0);
}

// P1 Stage 7: spatial navigation follows actual packed rectangles,
// not the saved array offsets. It must never alter the original document.
const navBase = layout.defaultLayout();
const navSaved = JSON.stringify(navBase);
const navPlain = layout.packTiles(navBase.modes[0].subModes[0].tiles);
assert.equal(layout.navigationTarget(navPlain,0,"right"),1);
assert.equal(layout.navigationTarget(navPlain,0,"down"),2);
assert.equal(layout.navigationTarget(navPlain,0,"left"),0);
assert.equal(layout.navigationTarget(navPlain,0,"up"),0);
assert.equal(layout.navigationTarget(navPlain,1,"left"),0);
assert.equal(layout.navigationTarget(navPlain,1,"down"),3);
assert.equal(layout.navigationTarget(navPlain,2,"right"),3);
assert.equal(layout.navigationTarget(navPlain,2,"up"),0);
assert.equal(layout.navigationTarget(navPlain,5,"down"),5);
const navTallGrid=layout.packTiles(
    layout.resizeTile(navBase,0,0,0,"half",3).modes[0].subModes[0].tiles);
assert.equal(layout.navigationTarget(navTallGrid,0,"right"),2);
assert.equal(layout.navigationTarget(navTallGrid,0,"down"),4);
assert.equal(layout.navigationTarget(navTallGrid,1,"left"),0);
assert.equal(layout.navigationTarget(navTallGrid,2,"left"),0);
assert.equal(layout.navigationTarget(navTallGrid,3,"left"),0);
assert.equal(layout.navigationTarget(navTallGrid,3,"down"),5);
assert.equal(layout.navigationTarget(navTallGrid,4,"up"),0);
assert.equal(layout.navigationTarget(navTallGrid,4,"right"),5);
const navWide=layout.packTiles(navBase.modes[1].subModes[0].tiles);
assert.equal(layout.navigationTarget(navWide,0,"right"),0);
assert.equal(layout.navigationTarget(navWide,0,"left"),0);
assert.equal(layout.navigationTarget(navWide,0,"down"),1);
assert.equal(layout.navigationTarget(navWide,1,"right"),2);
assert.equal(layout.navigationTarget(navWide,1,"up"),0);
assert.equal(JSON.stringify(navBase),navSaved);
assert.deepEqual(toPlain(layout.packTiles(navBase.modes[0].subModes[0].tiles)),
                 toPlain(navPlain));

// When a wide tile is below a tall half-width tile, arrows must only
// move into cards that really lie beyond the appropriate outer edge.
assert.equal(layout.navigationTarget(sparseGrid,0,"right"),2);
assert.equal(layout.navigationTarget(sparseGrid,0,"down"),1);
assert.equal(layout.navigationTarget(sparseGrid,1,"up"),0);
assert.equal(layout.navigationTarget(sparseGrid,2,"down"),3);
assert.equal(layout.navigationTarget(sparseGrid,2,"left"),0);
// Empty, invalid direction, and malformed grid inputs fail closed.
assert.equal(layout.navigationTarget({state:"ready",items:[]},0,"right"),0);
assert.equal(layout.navigationTarget(null,0,"right"),0);
assert.equal(layout.navigationTarget({state:"unavailable",items:[]},0,"down"),0);
assert.equal(layout.navigationTarget(navPlain,0,"diagonal"),0);
assert.equal(layout.navigationTarget(navPlain,-1,"up"),-1);
assert.equal(layout.navigationTarget(navPlain,0.4,"left"),0.4);

// Exercise every combination of four tile W/H sizes (1296 layouts). Every
// directional result is deterministic, is a real tile index, obeys its edge
// constraint, and does not mutate the grid or the source tile placements.
for(let flags=0; flags<16; flags++){
    for(let heightCode=0; heightCode<81; heightCode++){
        let code=heightCode;
        const tiles=[];
        for(let i=0;i<4;i++){
            tiles.push({
                id:"tile-"+(i+1),
                module:["time","apps","weather","notes"][i],
                size:(flags&(1<<i))?"wide":"half",
                rowSpan:code%3+1
            });
            code=Math.floor(code/3);
        }
        const tileBefore=JSON.stringify(tiles);
        const packed=layout.packTiles(tiles);
        const gridBefore=JSON.stringify(packed);
        for(let selected=0;selected<4;selected++){
            for(const direction of ["left","right","up","down"]){
                const chosen=layout.navigationTarget(packed,selected,direction);
                assert.ok(Number.isInteger(chosen) && chosen>=0 && chosen<4);
                assert.equal(chosen,layout.navigationTarget(packed,selected,direction));
                if(chosen!==selected){
                    const from=packed.items[selected], to=packed.items[chosen];
                    if(direction==="left")
                        assert.ok(to.column+to.columnSpan<=from.column);
                    if(direction==="right")
                        assert.ok(to.column>=from.column+from.columnSpan);
                    if(direction==="up")
                        assert.ok(to.row+to.rowSpan<=from.row);
                    if(direction==="down")
                        assert.ok(to.row>=from.row+from.rowSpan);
                }
            }
        }
        assert.equal(JSON.stringify(tiles),tileBefore);
        assert.equal(JSON.stringify(packed),gridBefore);
    }
}
console.log("ApolloHub Layout v2 migration, stable tile IDs, guarded remove and sizing tests passed");
