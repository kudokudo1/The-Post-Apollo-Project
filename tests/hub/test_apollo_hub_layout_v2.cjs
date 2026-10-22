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

console.log("ApolloHub Layout v2 migration, stable tile IDs, guarded remove and sizing tests passed");
