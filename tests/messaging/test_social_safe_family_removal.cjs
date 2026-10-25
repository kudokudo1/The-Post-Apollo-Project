#!/usr/bin/env node
"use strict";
// Execute actual Social identity policy. No live provider, account, desktop,
// file write or application launcher is invoked by this test.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const raw=fs.readFileSync(path.join(__dirname,
    "../../services/social/SocialIdentityPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(raw,p,{filename:"SocialIdentityPolicy.js"});

const base=p.initialDocument();
assert.equal(p.validate(base).ok,true);
assert.equal(p.removeFamily(base,"family-1","").reason,"REHOME_REQUIRED");
assert.equal(p.removeFamily(base,"family-1","family-1").reason,"SAME_FAMILY");
assert.equal(p.removeFamily(base,"family-1","family-404").reason,
             "INVALID_TARGET_FAMILY");
assert.equal(p.removeFamily(base,"bad","").reason,"INVALID_FAMILY");
assert.equal(p.removeFamily(base,7,"").reason,"INVALID_FAMILY");
assert.equal(p.removeFamily(base,"family-1",null).reason,"INVALID_TARGET_FAMILY");
assert.equal(base.identities[0].layout.families[0].appIds.length,32);

const withGaming=p.createFamily(base,"Gaming").document;
const withOther=p.createFamily(withGaming,"Other").document;
assert.equal(p.removeFamily(withOther,"family-2","family-3").reason,
             "TARGET_NOT_NEEDED");
const removeEmpty=p.removeFamily(withOther,"family-2","");
assert.equal(removeEmpty.ok,true);
assert.equal(removeEmpty.rehomedAppCount,0);
assert.equal(removeEmpty.document.identities[0].layout.families.map(f=>f.id).join(","),
             "family-1,family-3");
assert.equal(removeEmpty.document.identities[0].layout.nextFamilyId,4);
assert.equal(withOther.identities[0].layout.families.length,3);

// Prepare a nonempty, partially hidden source; destination already contains
// its own app and is collapsed. Rehoming appends ordered source members.
const source1=p.moveAppToFamily(withOther,"discord","family-2").document;
const source2=p.moveAppToFamily(source1,"telegram","family-2").document;
const dest1=p.moveAppToFamily(source2,"reddit","family-3").document;
const hidden=p.setAppHidden(dest1,"discord",true).document;
const collapsed=p.toggleFamily(hidden,"family-3").document;
assert.equal(collapsed.identities[0].layout.families[2].expanded,false);
assert.equal(p.removeFamily(collapsed,"family-2","").reason,"REHOME_REQUIRED");
assert.equal(p.removeFamily(collapsed,"family-2","family-2").reason,"SAME_FAMILY");
assert.equal(p.removeFamily(collapsed,"family-2","no-such-family").reason,
             "INVALID_TARGET_FAMILY");

const rehomed=p.removeFamily(collapsed,"family-2","family-3");
assert.equal(rehomed.ok,true);
assert.equal(rehomed.removedFamilyId,"family-2");
assert.equal(rehomed.rehomedAppCount,2);
const after=rehomed.document;
assert.equal(p.validate(after).ok,true);
assert.equal(collapsed.identities[0].layout.families.length,3); // immutable.
assert.equal(after.identities[0].layout.families.map(f=>f.id).join(","),
             "family-1,family-3");
assert.equal(after.identities[0].layout.families[1].appIds.join(","),
             "reddit,discord,telegram");
assert.equal(after.identities[0].layout.families[1].expanded,false);
assert.equal(after.identities[0].layout.hiddenAppIds.join(","),"discord");
assert.equal(after.identities[0].layout.nextFamilyId,4);
assert.equal(p.view("ready",after,"").appChoices[1].familyId,"family-3");
assert.equal(p.view("ready",after,"").appChoices[2].familyId,"family-3");
assert.equal(p.view("ready",after,"").appChoices[6].familyId,"family-3");
assert.equal(p.view("ready",after,"").appChoices[1].hidden,true);
assert.equal(p.view("ready",after,"").visibleAppIndices.includes(1),false);
assert.equal(p.view("ready",after,"").visibleAppIndices.includes(2),false);
const open=p.toggleFamily(after,"family-3").document;
assert.equal(p.view("ready",open,"").visibleAppIndices.slice(-2).join(","),
             "6,2"); // Hidden Discord remains hidden; Reddit and Telegram show.
assert.equal(new Set(after.identities[0].layout.families.flatMap(f=>f.appIds)).size,32);
assert.equal(after.identities[0].layout.families.reduce((n,f)=>n+f.appIds.length,0),32);

// If an occupied family becomes the sole remaining family, removal is refused.
// It can only be removed by first creating another destination.
const singleton=p.createFamily(base,"Destination").document;
const afterSolo=p.removeFamily(singleton,"family-2","").document;
assert.equal(p.removeFamily(afterSolo,"family-1","").reason,"REHOME_REQUIRED");
const movedAll=p.removeFamily(singleton,"family-1","family-2");
assert.equal(movedAll.ok,true);
assert.equal(movedAll.rehomedAppCount,32);
assert.equal(movedAll.document.identities[0].layout.families[0].appIds.length,32);
assert.equal(p.view("ready",movedAll.document,"").visibleAppIndices.length,32);

// Delete a final *empty* family, leaving the original start-empty state.
const empty=p.create(base,"Empty","empty","").document;
const created=p.createFamily(empty,"Disposable").document;
assert.equal(created.identities[1].layout.families.length,1);
const last=p.removeFamily(created,"family-1","");
assert.equal(last.ok,true);
assert.equal(last.document.identities[1].layout.families.length,0);
assert.equal(p.view("ready",last.document,"").railRows[0].kind,"empty");
assert.equal(p.view("ready",last.document,"").appChoices.length,32);
assert.equal(p.view("ready",last.document,"").visibleAppIndices.length,0);
assert.equal(last.document.identities[1].layout.nextFamilyId,2); // No reuse.
const afterNew=p.createFamily(last.document,"Later");
assert.equal(afterNew.familyId,"family-2");

// Per-identity safety: copied layouts share IDs but not arrays or mutation.
const copy=p.create(collapsed,"Work","copy","identity-1").document;
assert.equal(copy.activeId,"identity-2");
const workOnly=p.removeFamily(copy,"family-2","family-3").document;
assert.equal(workOnly.identities[0].layout.families.length,3);
assert.equal(workOnly.identities[0].layout.families[1].appIds.join(","),
             "discord,telegram");
assert.equal(workOnly.identities[1].layout.families.length,2);
assert.equal(workOnly.identities[1].layout.families[1].appIds.join(","),
             "reddit,discord,telegram");
const returnToDefault=p.select(workOnly,"identity-1").document;
assert.equal(p.view("ready",returnToDefault,"").familyOptions.length,3);
assert.equal(p.view("ready",workOnly,"").familyOptions.length,2);

// Validate still blocks unknown schema, and cloning drops injected fields.
const invalid={...collapsed,version:42};
assert.equal(p.removeFamily(invalid,"family-2","family-3").reason,
             "UNSUPPORTED_VERSION");
assert.equal(p.view("unsupported",invalid,"UNSUPPORTED_VERSION").writable,false);
const injected=p.clone(collapsed);
injected.identities[0].layout.families[1].password="NEVER_COPY";
injected.identities[0].linkedAccounts="NEVER_COPY";
const purified=p.removeFamily(injected,"family-2","family-3").document;
assert.equal(JSON.stringify(purified).includes("NEVER_COPY"),false);
assert.equal(purified.identities[0].layout.hiddenAppIds.includes("discord"),true);

console.log("Social safe family removal: rehome, confirmation preconditions, isolation PASS");
