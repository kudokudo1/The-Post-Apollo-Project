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

console.log("ApolloHub Layout v2 migration, stable tile IDs, guarded remove and sizing tests passed");
